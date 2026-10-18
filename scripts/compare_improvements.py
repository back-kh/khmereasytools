"""Paired accuracy comparisons; follow IMPROVEMENT_PROTOCOL.md before running."""
import argparse
import hashlib
import importlib
import importlib.metadata
import json
import math
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

from evaluation_metrics import aggregate_text, compact, fscore, sha256, text_score, nova_word_gold as word_gold

ROOT = Path(__file__).resolve().parents[1]
DEV = {"goc_3", "mef_1", "goc_4", "mef_3", "goc_2"}


def alt_gold(data, split):
    path = data / "alt"
    ids = {line.split("\t")[0].split(".")[1] for line in
           (path / ("URL-" + split + ".txt")).read_text(encoding="utf-8").splitlines()}
    tags = dict(line.split("\t", 1) for line in
                (path / "data_km.km-tag.nova").read_text(encoding="utf-8").splitlines())
    rows = []
    for line in (path / "data_km.km-tok.nova").read_text(encoding="utf-8").splitlines():
        key, text = line.split("\t", 1)
        if key.split(".")[1] in ids:
            rows.append((key, word_gold(text.split(), tags[key].split())))
    return rows


def spans(pairs):
    result, position = set(), 0
    for word, label in pairs:
        word = compact(word)
        if word:
            result.add((position, position + len(word), label))
            position += len(word)
    return result


def evaluate_text(ket, rows, with_pos=True):
    counts = {"segmentation": [0, 0, 0], "pos_boundaries": [0, 0, 0], "pos_joint": [0, 0, 0]}
    exact, changed = {key: 0 for key in counts}, {key: 0 for key in counts}
    started = time.perf_counter()
    for _, gold in rows:
        text = "".join(word for word, _ in gold)
        gold_tagged = spans(gold)
        gold_bounds = {item[:2] for item in gold_tagged}
        segmented = [(word, "") for word in ket.khseg(text)]
        predicted = {"segmentation": ({span[:2] for span in spans(segmented)}, gold_bounds,
                                       compact("".join(word for word, _ in segmented)) == text)}
        if with_pos:
            pairs = ket.khpos(text)
            tagged = spans(pairs)
            aligned = compact("".join(word for word, _ in pairs)) == text
            predicted.update(pos_boundaries=({span[:2] for span in tagged}, gold_bounds, aligned),
                             pos_joint=(tagged, gold_tagged, aligned))
        for name, (pred, target, aligned) in predicted.items():
            counts[name][0] += len(pred & target) if aligned else 0
            counts[name][1] += len(pred)
            counts[name][2] += len(target)
            exact[name] += aligned and pred == target
            changed[name] += not aligned
    return dict(sentences=len(rows), gold_tokens=sum(len(g) for _, g in rows),
                seconds=time.perf_counter() - started,
                metrics={name: dict(fscore(*values), exact_sentences=exact[name],
                                    alignment_failures=changed[name])
                         for name, values in counts.items() if values[2]})


def khpos_gold(data):
    result = []
    for i, line in enumerate((data / "OPEN-TEST.word").read_text(encoding="utf-8-sig").splitlines()):
        words = [compact(word.replace("\\~", "").replace("\\_", "")
                         .replace("~", "").replace("_", "")) for word in line.split()]
        result.append((i, [(word, "") for word in words if word]))
    return result


def evaluate_ocr(ket, data, partition, candidates=False):
    from PIL import Image, ImageOps
    from tempfile import TemporaryDirectory
    root = data / "khob/level1/khob-dataset/level-1"
    rows = []
    for path in sorted(root.rglob("*.json")):
        if (path.stem in DEV) != (partition == "dev"):
            continue
        annotation = json.loads(path.read_text(encoding="utf-8"))
        reference = "\n".join(s["label"].replace("\\t", "\t") for s in annotation["shapes"])
        rows.append((path, reference, path.parent / Path(annotation["imagePath"]).name))
    profiles = ("original", "enlarge2", "enlarge3", "enlarge2_gray") if candidates else ("public_default",)
    results = {}
    with TemporaryDirectory(prefix="ket-ocr-eval-") as directory:
        for profile in profiles:
            scores, started = [], time.perf_counter()
            for path, reference, image_path in rows:
                if candidates and profile != "original":
                    with Image.open(image_path) as image:
                        page = image.convert("RGB")
                        if profile.endswith("_gray"):
                            page = ImageOps.autocontrast(ImageOps.grayscale(page))
                        factor = 3 if profile == "enlarge3" else 2
                        page = page.resize((page.width * factor, page.height * factor),
                                           getattr(Image, "Resampling", Image).LANCZOS)
                        target = Path(directory) / "page.png"
                        page.save(target)
                        page.close()
                    report = ket.khocr_layout(target, segment=False)
                else:
                    report = ket.khocr_layout(image_path, segment=False)
                scores.append(dict(id=path.parent.name + "/" + path.stem,
                                   image_sha256=sha256(image_path),
                                   **text_score(reference, report.text)))
            results[profile] = dict(aggregate_text(scores), seconds=time.perf_counter() - started,
                                    per_page=scores)
            print("OCR", partition, profile, results[profile]["compact_codepoint_cer"], flush=True)
    return results


def source_metadata(ket):
    root = Path(ket.__file__).parent
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        digest.update(path.relative_to(root.parent).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    data = root / "data"
    def streamed_hash(path):
        value = hashlib.sha256()
        with Path(path).open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                value.update(block)
        return value.hexdigest()

    model_hashes = {name: streamed_hash(importlib.import_module(
        "khmernltk." + name).model_path) for name in ("pos_tag", "word_tokenize")}
    languages = subprocess.check_output(
        ["tesseract", "--list-langs"], stderr=subprocess.STDOUT).decode("utf-8", errors="replace")
    import re
    directory = re.search(r'"([^"]+)"', languages)
    model_location = os.environ.get("TESSDATA_PREFIX") or (directory.group(1) if directory else None)
    model_dir = Path(model_location) if model_location else None
    return dict(
        runtime_sources_sha256=digest.hexdigest(),
        dictionary_sha256=sha256(data / "khmer_words.txt"),
        frequencies_sha256=sha256(data / "word_frequencies.txt") if
        (data / "word_frequencies.txt").exists() else None,
        python=platform.python_version(), platform=platform.platform(),
        installed_package_path=str(root.resolve()),
        ci_source_revision=os.environ.get("GITHUB_SHA"),
        backend_model_sha256=model_hashes,
        tesseract_version=subprocess.check_output(["tesseract", "--version"]).decode(
            "utf-8", errors="replace").splitlines()[0],
        khm_model_sha256=streamed_hash(model_dir / "khm.traineddata") if model_dir else None,
        dependencies={name: importlib.metadata.version(name) for name in (
            "khmer-nltk", "sklearn-crfsuite", "python-crfsuite", "scikit-learn",
            "numpy", "Pillow", "pytesseract", "pypdfium2")},
        protocol_sha256=sha256(ROOT / "benchmarks/accuracy/IMPROVEMENT_PROTOCOL.md"),
        script_sha256=sha256(__file__))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path, default=ROOT)
    parser.add_argument("--installed", action="store_true", help="Require the current venv's installed wheel")
    parser.add_argument("--name", required=True)
    parser.add_argument("--partition", choices=("dev", "reserved"), default="dev")
    parser.add_argument("--checks", nargs="+", choices=("text", "ocr"), default=("text", "ocr"))
    parser.add_argument("--ocr-candidates", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "benchmarks/accuracy/improvements")
    args = parser.parse_args()
    if not args.installed:
        sys.path.insert(0, str(args.runtime_root.resolve()))
    import khmereasytools as ket
    if args.installed and Path(sys.prefix).resolve() not in Path(ket.__file__).resolve().parents:
        raise ValueError("Accuracy check must use the wheel inside this venv")
    data = ROOT / ".evaluation"
    result = dict(name=args.name, partition=args.partition, metadata=source_metadata(ket))
    if "text" in args.checks:
        result["alt_words"] = evaluate_text(ket, alt_gold(data, "dev" if args.partition == "dev" else "test"))
        if args.partition == "reserved":
            result["khpos_segmentation"] = evaluate_text(ket, khpos_gold(data), with_pos=False)
        for module_name, field in (("khmernltk.word_tokenize", "word_model_loaded"),
                                   ("khmernltk.pos_tag", "pos_model_loaded")):
            result[field] = getattr(sys.modules.get(module_name), "crf_model", None) is not None
        try:
            import resource
            peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            result["text_process_peak_rss_mib"] = peak / (1024 ** 2 if sys.platform == "darwin" else 1024)
        except ImportError:
            pass
    if "ocr" in args.checks:
        result["ocr"] = evaluate_ocr(ket, data, args.partition, args.ocr_candidates)
    args.output.mkdir(parents=True, exist_ok=True)
    target = args.output / (args.name + ".json")
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Saved", target, flush=True)
    if "alt_words" in result:
        print(json.dumps(result["alt_words"]), flush=True)


if __name__ == "__main__":
    main()

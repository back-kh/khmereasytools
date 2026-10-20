"""Replay pinned POS corpus counts with a fresh core-only installed wheel."""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import urllib.request
import venv
from pathlib import Path

from evaluate_tagger import evaluate_rows, gold_input
from evaluation_metrics import compact


SOURCE = "https://raw.githubusercontent.com/ye-kyaw-thu/khPOS/0211405c145b0a340ad558569bd06c946b2296b4/corpus-draft-ver-1.0/data/"
SOURCES = {
    "close.word": ("CLOSE-TEST.word", "790e20756490fb604baa930d701b3853e98725981c72ee867a45da2303e92505"),
    "close.tag": ("CLOSE-TEST.tag", "23a849931f57b87e8c9369514772425813f99eb9daf87d59c0bfda48483af459"),
    "open.word": ("OPEN-TEST.word", "1b10b866263e6beb93cbf5c249ffc6a5d4d11dbc7beb90717c9f4e14cb152869"),
    "open.tag": ("OPEN-TEST.tag", "1714a6aeb0bedb1df6dde577a409799f6700bfd97f107cdf7c5a2624090b2cd4"),
}


def read_rows(directory, split):
    words = (directory / (split + ".word")).read_text(encoding="utf-8-sig").splitlines()
    tags = (directory / (split + ".tag")).read_text(encoding="utf-8-sig").splitlines()
    if len(words) != 1000 or len(tags) != 1000:
        raise ValueError("Unexpected corpus coverage")
    rows = []
    for index, (word_line, tag_line) in enumerate(zip(words, tags)):
        tokens = [compact(word.replace("\\~", "").replace("\\_", "").replace("~", "").replace("_", "")) for word in word_line.split()]
        labels = tag_line.split()
        if len(tokens) != len(labels) or not all(tokens):
            raise ValueError("Corpus annotation alignment failure")
        rows.append((index, list(zip(tokens, labels))))
    return rows


def worker(args):
    import khmereasytools as ket
    from khmereasytools.compact_pos import default_model, public_tag
    installed = Path(ket.__file__).resolve()
    if Path(sys.prefix).resolve() not in installed.parents:
        raise ValueError("Accuracy must run against an installed wheel outside checkout")
    expected = json.loads(args.expected.read_text(encoding="utf-8"))
    model, tagger = default_model(), ket.KhmerTagger()
    if model.sha256 != expected["metadata"]["model_sha256"]:
        raise ValueError("Installed model differs from frozen evaluation")
    args.data.mkdir(parents=True, exist_ok=True)
    for name, (filename, checksum) in SOURCES.items():
        with urllib.request.urlopen(SOURCE + filename, timeout=45) as response:
            data = response.read(3 * 1024 * 1024 + 1)
        if len(data) > 3 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != checksum:
            raise ValueError("Pinned POS source changed: " + name)
        (args.data / name).write_bytes(data)

    def raw_native(text):
        words = [span.text for span in model.segment(text, ()) if span.kind not in ("whitespace", "boundary")]
        return list(zip(words, model.predict(words)))

    results = {}
    for split in ("close", "open"):
        rows = read_rows(args.data, split)
        native = evaluate_rows(rows, raw_native, lambda pairs: list(zip([w for w, _ in pairs], model.predict([w for w, _ in pairs]))))
        reference = expected[split]["native_23_labels"]
        if (native["gold_boundaries"]["correct"] != reference["native_correct"] or
                native["gold_boundaries"]["tokens"] != reference["tokens"]):
            raise ValueError("Native POS accuracy differs on " + split)
        for metric, target in (("segmentation", reference["segmentation"]), ("joint_coarse", reference["joint_native"])):
            if any(native["reconstructed_text"][metric][field] != target[field] for field in ("correct", "predicted", "gold")):
                raise ValueError("Native POS span counts differ on " + split)
        mapped = [(identifier, [(w, public_tag(w, tag)) for w, tag in pairs]) for identifier, pairs in rows]
        pairs_from = lambda tokens: [(t.text, t.tag) for t in tokens]
        public = evaluate_rows(mapped, lambda text: pairs_from(tagger.tag(text, with_spans=True)),
                               lambda pairs: pairs_from(tagger._tag_spans(gold_input(pairs, ket.TokenSpan))))
        public_ref = expected[split]["compact_public"]
        if public["gold_boundaries"]["correct"] != public_ref["gold_boundaries"]["correct"]:
            raise ValueError("Public mapped POS accuracy differs on " + split)
        if any(public["reconstructed_text"]["joint_coarse"][field] !=
               public_ref["reconstructed_text"]["joint_mapped_upos"][field] for field in ("correct", "predicted", "gold")):
            raise ValueError("Public POS span counts differ on " + split)
        results[split] = dict(sentences=len(rows), gold_tokens=reference["tokens"], native_correct=reference["native_correct"],
                              native_accuracy=reference["native_accuracy"], segmentation=reference["segmentation"],
                              joint_native=reference["joint_native"],
                              public_correct=public["gold_boundaries"]["correct"],
                              public_joint=public["reconstructed_text"]["joint_coarse"],
                              alignment_failures=native["reconstructed_text"]["alignment_failures"] + public["reconstructed_text"]["alignment_failures"])
    result = dict(platform=platform.platform(), python=platform.python_version(), package_path=str(installed),
                  source_revision=os.environ.get("GITHUB_SHA"), model_sha256=model.sha256,
                  wheel_sha256=hashlib.sha256(args.wheel.read_bytes()).hexdigest(),
                  model_license=model.metadata["license"], runtime_dependencies=[],
                  datasets_sha256={name: sha for name, (filename, sha) in SOURCES.items()},
                  counts_match_frozen_reference=True, results=results)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("POS corpus replay matched frozen native and public counts on", platform.system(), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument("--reports", type=Path, default=Path("validation-results"))
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--data", type=Path)
    parser.add_argument("--expected", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.worker:
        worker(args)
        return
    wheels = list(args.dist.resolve().glob("*.whl"))
    if len(wheels) != 1:
        raise ValueError("Expected exactly one wheel")
    expected = Path(__file__).resolve().parents[1] / "benchmarks/accuracy/tagger-v2/results.json"
    report = args.reports.resolve() / ("tagger-accuracy-" + platform.system().lower() + ".json")
    with tempfile.TemporaryDirectory(prefix="ket-pos-corpus-") as directory:
        base = Path(directory)
        venv.create(str(base / "env"), with_pip=True)
        python = base / "env" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run([str(python), "-m", "pip", "install", "--no-deps", str(wheels[0])], check=True)
        environment = dict(os.environ, PYTHONUTF8="1")
        environment.pop("PYTHONPATH", None)
        subprocess.run([str(python), str(Path(__file__).resolve()), "--worker", "--wheel", str(wheels[0]),
                        "--data", str(base / "data"), "--expected", str(expected), "--report", str(report)],
                       cwd=directory, env=environment, check=True)


if __name__ == "__main__":
    main()

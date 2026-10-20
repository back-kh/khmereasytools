"""Bounded OCR experiments defined in OCR_TARGET_PROTOCOL.md (no gold crops)."""
import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

from evaluation_metrics import aggregate_text, sha256, text_score

ROOT = Path(__file__).resolve().parents[1]
DEV = {"goc_3", "mef_1", "goc_4", "mef_3", "goc_2"}
BEST_SHA256 = "3d2d975e67a319bf1cd67626b12fdebc1e417a4ebef9c9afee01d9927b512815"
FAST_SHA256 = "47f110575341b322052f3becbefee61a3ecf1ef549352b5d4d33d28afe30d099"


def load_pages():
    root = ROOT / ".evaluation/khob/level1/khob-dataset/level-1"
    rows = []
    for path in sorted(root.rglob("*.json")):
        annotation = json.loads(path.read_text(encoding="utf-8"))
        reference = "\n".join(s["label"].replace("\\t", "\t") for s in annotation["shapes"])
        rows.append(dict(id=path.parent.name + "/" + path.stem, stem=path.stem,
                         annotation=path, reference=reference,
                         image=path.parent / Path(annotation["imagePath"]).name))
    if len(rows) != 60:
        raise ValueError("Expected exactly 60 pinned KHOB images")
    return rows


def pdf_transport(ket, rows, directory):
    """Reproduce the existing lossless 15-scan PDF at source pixel size, 200 DPI."""
    from PIL import Image
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.lib.utils import ImageReader
    scans = [row for row in rows if row["id"].startswith("task-3/")]
    if len(scans) != 15:
        raise ValueError("Expected 15 physical-scanner source pages")
    pdf_path = directory / "khob_scans.pdf"
    canvas = Canvas(str(pdf_path), pageCompression=1, invariant=1)
    for row in scans:
        with Image.open(row["image"]) as original:
            page = original.convert("RGB")
            width, height = page.width * 72 / 200, page.height * 72 / 200
            canvas.setPageSize((width, height))
            canvas.drawImage(ImageReader(page), 0, 0, width=width, height=height)
            page.close()
        canvas.showPage()
    canvas.save()
    started = time.perf_counter()
    document = ket.khanalyze(pdf_path, segment=False)
    if len(document.pages) != len(scans):
        raise ValueError("PDF transport lost pages")
    scores = [dict(id=row["id"], image_sha256=sha256(row["image"]),
                   **text_score(row["reference"], page.layout.text))
              for row, page in zip(scans, document.pages)]
    return dict(aggregate_text(scores), per_page=scores, pdf_sha256=sha256(pdf_path),
                seconds=time.perf_counter() - started,
                interpretation="Derived from the same images; not an independent document corpus")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True,
                        choices=("fast-auto", "best-auto", "best-large", "best-column"))
    parser.add_argument("--partition", choices=("dev", "reserved"), default="dev")
    parser.add_argument("--tessdata-dir", type=Path)
    parser.add_argument("--installed", action="store_true", help="Require the current venv's installed wheel")
    parser.add_argument("--pdf-transport", action="store_true", help="Also test the existing 15-scan PDF recipe")
    parser.add_argument("--output", type=Path, default=ROOT / ".evaluation/ocr-target")
    args = parser.parse_args()
    if args.profile.startswith("best") and args.tessdata_dir is None:
        parser.error("best profiles require the pinned best Khmer model directory")
    if args.pdf_transport and args.profile not in ("fast-auto", "best-auto"):
        parser.error("PDF transport only supports the selected auto profiles")
    if args.tessdata_dir is not None:
        # Only this standalone experiment process changes its environment.
        os.environ["TESSDATA_PREFIX"] = str(args.tessdata_dir.resolve())
    if not args.installed:
        sys.path.insert(0, str(ROOT))
    import khmereasytools as ket
    package = Path(ket.__file__).resolve().parent
    if args.installed and Path(sys.prefix).resolve() not in package.parents:
        raise ValueError("Accuracy check must use the wheel inside this venv")
    from PIL import Image, ImageOps
    import pytesseract

    languages = subprocess.check_output(["tesseract", "--list-langs"], stderr=subprocess.STDOUT).decode(
        "utf-8", errors="replace")
    directory = re.search(r'"([^"]+)"', languages)
    model_dir = os.environ.get("TESSDATA_PREFIX") or (directory.group(1) if directory else None)
    if model_dir is None:
        raise ValueError("Set --tessdata-dir to the pinned model directory")
    model_sha256 = sha256(Path(model_dir) / "khm.traineddata")
    if model_sha256 != (BEST_SHA256 if args.profile.startswith("best") else FAST_SHA256):
        raise ValueError("OCR model checksum differs from the fixed profile")
    source_hash = hashlib.sha256()
    for path in sorted(package.rglob("*.py")):
        source_hash.update(path.relative_to(package.parent).as_posix().encode("utf-8"))
        source_hash.update(path.read_bytes())
    rows = load_pages()
    scores, predictions = [], []
    started = time.perf_counter()
    with TemporaryDirectory(prefix="ket-ocr-target-") as directory:
        for source in rows:
            if (source["stem"] in DEV) != (args.partition == "dev"):
                continue
            reference, image_path = source["reference"], source["image"]
            page_started = time.perf_counter()
            if args.profile != "best-large":
                layout = ket.khocr_layout(image_path, segment=False,
                                          psm=4 if args.profile == "best-column" else 3)
            else:
                with Image.open(image_path) as original:
                    page = ImageOps.exif_transpose(original).convert("RGB")
                factor = 3 if max(page.size) < 1600 else 1
                if factor > 1:
                    page = ImageOps.autocontrast(ImageOps.grayscale(page))
                    page = page.resize((page.width * factor, page.height * factor),
                                       getattr(Image, "Resampling", Image).LANCZOS)
                target = Path(directory) / "page.png"
                page.save(target)
                page.close()
                layout = ket.khocr_layout(target, segment=False, preprocess="none")
            row = dict(id=source["id"], image_sha256=sha256(image_path),
                       annotation_sha256=sha256(source["annotation"]),
                       seconds=time.perf_counter() - page_started,
                       **text_score(reference, layout.text))
            scores.append(row)
            predictions.append(dict(id=row["id"], reference=reference, prediction=layout.text))
            print(row["id"], round(row["codepoint_edits"] / row["reference_codepoints"], 4), flush=True)
        pdf = pdf_transport(ket, rows, Path(directory)) if args.pdf_transport else None
    if len(scores) != (20 if args.partition == "dev" else 40):
        raise ValueError("Partition page count changed")
    page_cers = [row["codepoint_edits"] / row["reference_codepoints"] for row in scores]
    result = dict(profile=args.profile, partition=args.partition, python=platform.python_version(),
                  platform=platform.platform(),
                  tesseract=str(pytesseract.get_tesseract_version()).splitlines()[0],
                  model_sha256=model_sha256, model_bytes=(Path(model_dir) / "khm.traineddata").stat().st_size,
                  source_revision=os.environ.get("GITHUB_SHA") or subprocess.check_output(
                      ["git", "rev-parse", "HEAD"], cwd=str(ROOT)).decode().strip(),
                  runtime_sources_sha256=source_hash.hexdigest(), installed_package_path=str(package),
                  wheel_sha256=os.environ.get("KET_VALIDATION_WHEEL_SHA256"),
                  dependencies={name: importlib.metadata.version(name) for name in
                                ("Pillow", "pytesseract", "pypdfium2", "rapidfuzz", "reportlab")},
                  protocol_sha256=sha256(ROOT / "benchmarks/accuracy/OCR_TARGET_PROTOCOL.md"),
                  script_sha256=sha256(__file__), seconds=time.perf_counter() - started,
                  scores=aggregate_text(scores), per_page=scores,
                  per_task={task: aggregate_text([row for row in scores if row["id"].startswith(task + "/")])
                            for task in ("task-1", "task-2", "task-3", "task-4")},
                  pages_below_10_percent=sum(value < 0.1 for value in page_cers),
                  minimum_page_cer=min(page_cers), maximum_page_cer=max(page_cers),
                  target_met=aggregate_text(scores)["compact_codepoint_cer"] < 0.1)
    if pdf is not None:
        result["pdf_transport"] = pdf
    args.output.mkdir(parents=True, exist_ok=True)
    target = args.output / (args.profile + "-" + args.partition)
    target.with_suffix(".json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    # Predictions remain in ignored .evaluation, never committed or packaged.
    prediction_target = ROOT / ".evaluation/ocr-target/predictions" / target.name
    prediction_target.parent.mkdir(parents=True, exist_ok=True)
    prediction_target.with_suffix(".json").write_text(
        json.dumps(predictions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"profile": args.profile, "scores": result["scores"], "seconds": result["seconds"]}), flush=True)


if __name__ == "__main__":
    main()

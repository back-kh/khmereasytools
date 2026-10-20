"""One adaptive mixed-language follow-up; see OCR_MIXED_PROTOCOL.md."""
import argparse
import functools
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from urllib.request import urlopen

from evaluate_ocr_target import DEV, ROOT, load_pages, pdf_transport
from evaluation_metrics import aggregate_text, sha256, text_score
from prepare_ocr_ci import REVISION, SHA256

MODELS = {"khm": SHA256, "eng": "7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--partition", choices=("dev", "reserved"), default="dev")
    parser.add_argument("--tessdata-dir", type=Path, default=ROOT / ".evaluation/ocr-target/tessdata-mixed")
    parser.add_argument("--prepare-models", action="store_true", help="Explicitly fetch pinned evaluation models if needed")
    parser.add_argument("--installed", action="store_true")
    parser.add_argument("--pdf-transport", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / ".evaluation/ocr-target/mixed-final")
    args = parser.parse_args()
    directory = args.tessdata_dir.resolve()
    if args.prepare_models:
        directory.mkdir(parents=True, exist_ok=True)
    models = {}
    for language, expected in MODELS.items():
        path = directory / (language + ".traineddata")
        if args.prepare_models and (not path.is_file() or sha256(path) != expected):
            url = "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/{}/{}.traineddata".format(REVISION, language)
            with urlopen(url, timeout=60) as response:
                data = response.read(10000000)
            if hashlib.sha256(data).hexdigest() != expected:
                raise ValueError("Downloaded model checksum mismatch: " + language)
            path.write_bytes(data)
        if not path.is_file() or sha256(path) != expected:
            raise ValueError("Missing pinned model; use --prepare-models: " + language)
        models[language] = dict(sha256=expected, bytes=path.stat().st_size)
    # Only this standalone process selects these models. The library never
    # downloads data or mutates the caller's model-selection environment.
    os.environ["TESSDATA_PREFIX"] = str(directory)
    if not args.installed:
        sys.path.insert(0, str(ROOT))
    import khmereasytools as ket
    import pytesseract
    package = Path(ket.__file__).resolve().parent
    if args.installed and Path(sys.prefix).resolve() not in package.parents:
        raise ValueError("Expected the wheel installed in this venv")
    sources = load_pages()
    rows, predictions = [], []
    started = time.perf_counter()
    for source in sources:
        if (source["stem"] in DEV) != (args.partition == "dev"):
            continue
        page_started = time.perf_counter()
        page = ket.khocr_layout(source["image"], lang="khm+eng", segment=False)
        row = dict(id=source["id"], image_sha256=sha256(source["image"]),
                   annotation_sha256=sha256(source["annotation"]), seconds=time.perf_counter() - page_started,
                   **text_score(source["reference"], page.text))
        rows.append(row)
        predictions.append(dict(id=row["id"], reference=source["reference"], prediction=page.text))
        print(row["id"], round(row["codepoint_edits"] / row["reference_codepoints"], 4), flush=True)
    if len(rows) != (20 if args.partition == "dev" else 40):
        raise ValueError("Partition image count differs")
    result = dict(language="khm+eng", partition=args.partition, scores=aggregate_text(rows), per_page=rows,
                  models=models, model_revision=REVISION, image_seconds=time.perf_counter() - started,
                  python=platform.python_version(), platform=platform.platform(),
                  installed_package_path=str(package), source_revision=os.environ.get("GITHUB_SHA"),
                  wheel_sha256=os.environ.get("KET_VALIDATION_WHEEL_SHA256"),
                  tesseract=str(pytesseract.get_tesseract_version()).splitlines()[0],
                  dependencies={name: importlib.metadata.version(name) for name in
                                ("Pillow", "pytesseract", "pypdfium2", "rapidfuzz", "reportlab")},
                  script_sha256=sha256(__file__),
                  protocol_sha256=sha256(ROOT / "benchmarks/accuracy/OCR_MIXED_PROTOCOL.md"),
                  interpretation="Adaptive candidate motivated by benchmark inspection; needs independent validation")
    if args.pdf_transport:
        with tempfile.TemporaryDirectory(prefix="ket-mixed-pdf-") as temporary:
            # Bind an explicit language to the real public API, reusing the
            # same PDF recipe/scorer as the original comparison. No mock OCR.
            api = SimpleNamespace(khanalyze=functools.partial(ket.khanalyze, lang="khm+eng"))
            result["pdf_transport"] = pdf_transport(api, sources, Path(temporary))
    source_hash = hashlib.sha256()
    for path in sorted(package.rglob("*.py")):
        source_hash.update(path.relative_to(package.parent).as_posix().encode("utf-8"))
        source_hash.update(path.read_bytes())
    result["runtime_sources_sha256"] = source_hash.hexdigest()
    result["target_met"] = result["scores"]["compact_codepoint_cer"] < 0.1
    result["per_task"] = {task: aggregate_text([r for r in rows if r["id"].startswith(task + "/")])
                          for task in ("task-1", "task-2", "task-3", "task-4")}
    args.output.mkdir(parents=True, exist_ok=True)
    target = args.output / ("mixed-auto-" + args.partition + ".json")
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    prediction_path = ROOT / ".evaluation/ocr-target/predictions" / target.name
    prediction_path.parent.mkdir(parents=True, exist_ok=True)
    prediction_path.write_text(json.dumps(predictions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["scores"]), flush=True)


if __name__ == "__main__":
    main()

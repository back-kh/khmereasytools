"""Download only explicitly selected, checksum-pinned research baselines."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "benchmarks/accuracy/document-ocr/model-inventory.json"
DESTINATION = ROOT / ".evaluation/full_document_ocr/models"
FAST_REVISION = "87416418657359cb625c412a48b6e1d6d41c29bd"
FAST_HASHES = {
    "khm": "47f110575341b322052f3becbefee61a3ecf1ef549352b5d4d33d28afe30d099",
    "eng": "7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2",
}


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, choices=["all", "tesseract", "surya", "paddle", "deepseek"])
    args = parser.parse_args()
    if args.model in {"all", "tesseract"}:
        target = ROOT / ".evaluation/ocr-target/tessdata-mixed"
        target.mkdir(parents=True, exist_ok=True)
        for language, expected in FAST_HASHES.items():
            path = target / (language + ".traineddata")
            if not path.exists() or file_hash(path) != expected:
                url = "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/{}/{}.traineddata".format(
                    FAST_REVISION, language)
                with urlopen(url, timeout=60) as response:
                    content = response.read(10000000)
                if hashlib.sha256(content).hexdigest() != expected:
                    raise ValueError("Tesseract model identity mismatch: " + language)
                path.write_bytes(content)
        print("Verified original fast Khmer and English LSTM models", flush=True)
        if args.model == "tesseract":
            return
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    selectors = {"surya": "surya-ocr-2-gguf", "paddle": "PaddleOCR-VL-1.6-4bit",
                 "deepseek": "DeepSeek-OCR-4bit"}
    from huggingface_hub import snapshot_download
    for repository, model in inventory.items():
        if args.model != "all" and model["directory"] != selectors[args.model]:
            continue
        name = model["directory"]
        if Path(name).name != name or name in {".", ".."}:
            raise ValueError("Unsafe model directory")
        for row in model["files"]:
            path = PurePosixPath(row["path"])
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("Unsafe model file path")
        target = DESTINATION / name
        snapshot_download(repo_id=repository, revision=model["revision"],
                          allow_patterns=[row["path"] for row in model["files"]],
                          local_dir=str(target), max_workers=2)
        for row in model["files"]:
            path = target / row["path"]
            if path.stat().st_size != row["size"] or file_hash(path) != row["sha256"]:
                raise ValueError("Model identity mismatch: " + repository + "/" + row["path"])
        print("Verified", repository, model["revision"], flush=True)


if __name__ == "__main__":
    main()

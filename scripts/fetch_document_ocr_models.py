"""Download only explicitly selected, checksum-pinned research baselines."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "benchmarks/accuracy/document-ocr/model-inventory.json"
DESTINATION = ROOT / ".evaluation/full_document_ocr/models"


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, choices=["all", "surya", "paddle", "deepseek"])
    args = parser.parse_args()
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

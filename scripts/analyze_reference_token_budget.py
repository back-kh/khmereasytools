"""Post hoc text-only reference lengths; never changes inference settings."""
import hashlib
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / ".evaluation/full_document_ocr"
SMALL = ROOT / ".evaluation/small_vlm"
PUBLIC = ROOT / "benchmarks/accuracy/document-ocr"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    from transformers import AutoTokenizer
    pages = read(DATA / "prepared.json")["pages"]
    inventories = [(DATA, PUBLIC / "model-inventory.json", None),
                   (SMALL, SMALL / "model-inventory.json", "test")]
    result = {}
    for home, manifest, split in inventories:
        for repository, model in read(manifest).items():
            if "surya" in repository:
                continue  # Its GGUF tokenizer is not a Transformers tokenizer.
            selected = [p for p in pages if split is None or p["source_split"] == split]
            tokenizer = AutoTokenizer.from_pretrained(
                str(home / "models" / model["directory"]),
                local_files_only=True, trust_remote_code=False)
            counts = [len(tokenizer.encode(p["reference"], add_special_tokens=False))
                      for p in selected]
            result[repository] = dict(pages=len(selected), revision=model["revision"],
                source_partition=split or "test and source-train", minimum=min(counts),
                median=statistics.median(counts), maximum=max(counts),
                references_exceeding_4096=sum(n > 4096 for n in counts))
    report = dict(analysis="Post hoc tokenizer-only check; no inference or parameter selection",
        source_evaluation_token=read(DATA / "frozen.json")["token"],
        analyzer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        input="Released original_transcription; no special tokens or output-serialization overhead",
        models=result,
        limitations=["Surya GGUF tokenizer is not included in this check.",
                     "Text-only reference lengths do not prove full generated responses will fit the cap.",
                     "These counts do not establish recognition quality or justify removing capped outputs."])
    (PUBLIC / "reference-token-budget.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

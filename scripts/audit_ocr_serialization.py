"""Posthoc script/serialization counts for the unchanged historical outputs."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from document_ocr_metrics import visible_text
from evaluation_metrics import compact


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    totals = defaultdict(Counter)
    sources, rows = {}, []
    for relative, small in [("document-ocr", False), ("small-vlm", True)]:
        source = ROOT / "benchmarks/accuracy" / relative / "local-results.json"
        sources[relative] = digest(source)
        public = read(source)
        for row in public["records"]:
            directory = ROOT / (".evaluation/small_vlm/server-run" if small else ".evaluation/full_document_ocr")
            path = directory / "predictions" / row["evaluation_token"] / row["system"] / (hashlib.sha256(row["id"].encode()).hexdigest() + ".json")
            private = read(path)
            raw = private.get("raw") or ""
            prediction = visible_text(raw) if small else private["prediction"]
            if private.get("raw") is None:
                raw = prediction  # The Tesseract profiles already emit plain text.
            text = compact(prediction)
            counts = dict(samples=1, compact_prediction_codepoints=len(text),
                khmer_block_codepoints=sum("\u1780" <= c <= "\u17ff" for c in text),
                decimal_codepoints=sum(c.isdecimal() for c in text),
                raw_ref_det_marker_occurrences=sum(raw.count(marker) for marker in ("<|ref|>", "<|/ref|>", "<|det|>")),
                visible_bbox_assignments=prediction.count("bbox="),
                raw_bbox_assignments=raw.count("bbox="))
            totals[row["system"]].update(counts)
            rows.append(dict(id=row["id"], system=row["system"], raw_sha256=digest(path), **counts))
    if len(rows) != 810:
        raise ValueError("Expected all historical750 plus matched Qwen60 outputs")
    output = dict(schema_version=1, analysis_sha256=digest(Path(__file__)),
        source_results_sha256=sources, summary={key: dict(value) for key, value in sorted(totals.items())},
        raw_record_count=len(rows),
        private_count_record_inventory_sha256=hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest(),
        notes=["Posthoc descriptive counts; no predictions or CER scores are changed.",
               "Khmer-block membership is U+1780..U+17FF, not language identification or transcription correctness.",
               "Counts use compact NFC predictions; bbox assignments are literal serializer checks.",
               "Qwen summaries cover only30 historical test pages; other systems cover150.",
               "Absence of checked serialization markers does not certify every possible output format."])
    target = ROOT / "benchmarks/accuracy/ocr-word-errors/serialization-audit.json"
    target.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output["summary"], indent=2))


if __name__ == "__main__":
    main()

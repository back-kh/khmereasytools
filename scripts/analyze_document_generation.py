"""Post hoc output-length diagnostics; never change predictions or CER scoring.

Requires the completed, audited 150-page and 30-page studies. Public output
contains only counts, lengths and hashes, without recognized text or references.
An overlapping eight-code-point reuse fraction describes repetition but is not
an accuracy metric, and can also be high in legitimate repeated document text.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_document_ocr import projection
from document_ocr_metrics import visible_text

PRIMARY = ROOT / ".evaluation/full_document_ocr"
SMALL = ROOT / ".evaluation/small_vlm"
PUBLIC = ROOT / "benchmarks/accuracy/document-ocr"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reuse_fraction(text, width=8):
    count = max(0, len(text) - width + 1)
    return 0.0 if not count else 1 - len({text[i:i + width] for i in range(count)}) / count


def summarize(rows):
    denominator = sum(r["reference_codepoints"] for r in rows)
    predicted = sum(r["prediction_codepoints"] for r in rows)
    ratios = [r["prediction_codepoints"] / r["reference_codepoints"] for r in rows]
    return dict(samples=len(rows), reference_codepoints=denominator,
                prediction_codepoints=predicted,
                aggregate_length_ratio=predicted / denominator,
                median_page_length_ratio=statistics.median(ratios),
                maximum_page_length_ratio=max(ratios),
                outputs_longer_than_twice_reference=sum(value > 2 for value in ratios),
                cap_states=dict(Counter("unknown" if r["capped"] is None else
                                        "capped" if r["capped"] else "not_capped" for r in rows)),
                median_prediction_eightgram_reuse=statistics.median(r["prediction_eightgram_reuse"] for r in rows),
                median_reference_eightgram_reuse=statistics.median(r["reference_eightgram_reuse"] for r in rows))


def main():
    result_path = PUBLIC / "local-results.json"
    small_path = ROOT / "benchmarks/accuracy/small-vlm/local-results.json"
    audit_path = PUBLIC / "consistency-audit.json"
    result, small, audit = read(result_path), read(small_path), read(audit_path)
    if (not audit["passed"] or audit["results_sha256"] != digest(result_path) or
            audit["source_evaluation_token"] != result["source_environment"]["token"] or
            not small["independent_audit"]["passed"] or
            any(v["completed"] != 150 or v["missing"] for v in result["coverage"].values()) or
            any(v["completed"] != 30 or v["missing"] for v in small["coverage"].values())):
        raise ValueError("Both complete studies and their audits are required")
    pages = {p["id"]: p for p in read(PRIMARY / "prepared.json")["pages"]}
    rows = []
    for public, is_small in [(result, False), (small, True)]:
        for record in public["records"]:
            page = pages[record["id"]]
            token = record["evaluation_token"]
            filename = hashlib.sha256(record["id"].encode()).hexdigest() + ".json"
            path = ((SMALL / "server-run") if is_small else PRIMARY) / "predictions" / token / record["system"] / filename
            private = read(path)
            if is_small:
                if digest(path) != record["raw_record_sha256"]:
                    raise ValueError("Raw Qwen record differs")
                prediction = visible_text(private["raw"])
            else:
                if private["score"] != record["score"]:
                    raise ValueError("Scored primary record differs")
                prediction = private["prediction"]
            ref, pred = projection(page["reference"]), projection(prediction)
            if len(ref) != record["score"]["reference_codepoints"]:
                raise ValueError("Reference denominator differs")
            rows.append(dict(id=record["id"], system=record["system"], source_split=page["source_split"],
                             evaluation_token=token, reference_codepoints=len(ref),
                             prediction_codepoints=len(pred), capped=record.get("capped"),
                             prediction_eightgram_reuse=reuse_fraction(pred),
                             reference_eightgram_reuse=reuse_fraction(ref)))
    summaries = {}
    for collection, split in [("churro-sleuk", None), ("churro-sleuk-test", "test"),
                              ("churro-sleuk-train", "train")]:
        systems = sorted({r["system"] for r in rows if not split or r["source_split"] == split})
        for system in systems:
            selected = [r for r in rows if r["system"] == system and (not split or r["source_split"] == split)]
            # Qwen covers only the official test set; do not suggest it covers all 150.
            if split is None and system in small["coverage"]:
                continue
            summaries.setdefault(collection, {})[system] = summarize(selected)
    output = dict(schema_version=1, analysis_sha256=digest(Path(__file__)),
                  primary_results_sha256=digest(result_path), small_results_sha256=digest(small_path),
                  primary_audit_sha256=digest(audit_path), summary=summaries, records=rows,
                  notes=["Post hoc descriptive diagnostics; predictions and CER remain unchanged.",
                         "Lengths use the same compact NFC projection as CER.",
                         "Eightgram reuse is one minus distinct overlapping eightgrams divided by their count; texts under eight code points return zero.",
                         "Reuse is not an accuracy metric and can also reflect legitimate repetition.",
                         "No clipped, deduplicated or token-cap-selected alternative CER is reported."])
    (PUBLIC / "generation-diagnostics.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()

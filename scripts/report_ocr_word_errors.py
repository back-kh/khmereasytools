"""Add CER S/D/I and explicitly defined WERs to frozen OCR predictions.

No OCR inference, reference repair, repeat removal or metric clipping. Private
caches retain provenance; public output contains counts and hashes only.
"""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_document_ocr import edit_distance, self_check
from document_ocr_metrics import visible_text
from evaluation_metrics import compact, text_score
from ocr_word_metrics import aggregate, edit_counts, segmented_tokens, whitespace_tokens

DATA = ROOT / ".evaluation/ocr_word_errors"
PUBLIC = ROOT / "benchmarks/accuracy/ocr-word-errors"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def expanded_records():
    home = ROOT / ".evaluation/expanded_ocr"
    public = read(ROOT / "benchmarks/accuracy/expanded-ocr/local-paired.json")
    if digest(home / "prepared.json") != public["metadata"]["manifest_sha256"]:
        raise ValueError("Expanded source manifest differs")
    groups = read(home / "prepared.json")["groups"]
    references = {u["id"]: u["reference"] for g in groups for u in g["units"]}
    caches = sorted((home / "predictions").iterdir())
    if len(caches) != 1:
        raise ValueError("Choose the unique frozen expanded cache explicitly")
    public_rows = {(r["id"], r["variant"]): r for r in public["per_unit"]}
    seen = set()
    for path in sorted(caches[0].glob("*.json")):
        batch = read(path)
        if batch["token"] != caches[0].name:
            raise ValueError("Expanded cache token differs")
        predictions = {(r["id"], r["variant"]): r for r in batch["predictions"]}
        for row in batch["rows"]:
            key = (row["id"], row["variant"])
            if key in seen or key not in public_rows or public_rows[key] != row:
                raise ValueError("Expanded scored-row identity differs")
            seen.add(key)
            prediction = predictions[key]
            reference = references[row["id"]]
            if prediction["reference"] != reference:
                raise ValueError("Expanded raw reference differs")
            for old, system in [("baseline", "tesseract-fast"), ("toolkit", "ket-ocr")]:
                score = text_score(reference, prediction[old])
                if any(row[old][k] != value for k, value in score.items()):
                    raise ValueError("Original expanded score differs")
                yield dict(id=row["id"], collection=row["dataset"] + "_" + row["variant"],
                           group=row["group"], system=system, reference=reference,
                           prediction=prediction[old], source_score=score,
                           raw_sha256=digest(path), error=row[old]["failed"], capped=None)
    if seen != set(public_rows):
        raise ValueError("Expanded cache coverage differs")


def historical_records():
    home = ROOT / ".evaluation/full_document_ocr"
    pages = {p["id"]: p for p in read(home / "prepared.json")["pages"]}
    for relative, small in [("document-ocr", False), ("small-vlm", True)]:
        public = read(ROOT / "benchmarks/accuracy" / relative / "local-results.json")
        for row in public["records"]:
            filename = hashlib.sha256(row["id"].encode()).hexdigest() + ".json"
            directory = ROOT / ".evaluation/small_vlm/server-run" if small else home
            path = directory / "predictions" / row["evaluation_token"] / row["system"] / filename
            raw = read(path)
            if small and digest(path) != row["raw_record_sha256"]:
                raise ValueError("Qwen raw source differs")
            prediction = visible_text(raw["raw"]) if small else raw["prediction"]
            reference = pages[row["id"]]["reference"]
            if text_score(reference, prediction) != row["score"]:
                raise ValueError("Historical original score differs")
            yield dict(id=row["id"], collection="historical", source_split=pages[row["id"]]["source_split"],
                       group=pages[row["id"]]["group"], system="ket-ocr" if row["system"] == "khmereasytools-fast" else row["system"],
                       reference=reference, prediction=prediction, source_score=row["score"],
                       raw_sha256=digest(path), error=row["error"], capped=row.get("capped"))


def measured(item, metric_token):
    identity = {k: item[k] for k in ("id", "collection", "system", "raw_sha256")}
    identity["reference_sha256"] = hashlib.sha256(item["reference"].encode()).hexdigest()
    identity["metric_token"] = metric_token
    cache_key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    path = DATA / "measurements" / (cache_key + ".json")
    if path.exists():
        row = read(path)
        if any(row[k] != v for k, v in identity.items()):
            raise ValueError("Added metric cache differs")
        return row
    ref, pred = item["reference"], item["prediction"]
    projections = {"compact_cer": (compact(ref), compact(pred)),
                   "whitespace_unit_wer": (whitespace_tokens(ref), whitespace_tokens(pred)),
                   "segmentation_assisted_wer": (segmented_tokens(ref), segmented_tokens(pred))}
    scores = {}
    for name, (left, right) in projections.items():
        score = edit_counts(left, right)
        if score["edits"] != edit_distance(left, right):
            raise ValueError("Independent minimum-distance audit differs")
        scores[name] = score
    if (scores["compact_cer"]["edits"] != item["source_score"]["codepoint_edits"] or
            scores["compact_cer"]["reference_units"] != item["source_score"]["reference_codepoints"]):
        raise ValueError("Primary CER changed")
    row = dict(identity, scores=scores, group=item["group"], error=bool(item["error"]),
               empty=not pred.strip(), capped=item["capped"], source_split=item.get("source_split"),
               minimum_length_insertions=max(0, len(projections["compact_cer"][1]) - len(projections["compact_cer"][0])))
    write(path, row)
    return row


def main():
    checks = self_check()
    paths = ["scripts/ocr_word_metrics.py", "scripts/evaluation_metrics.py", "scripts/audit_document_ocr.py",
             "scripts/document_ocr_metrics.py", "khmereasytools/segmentation.py", "khmereasytools/lexicon.py",
             "khmereasytools/data/khmer_words.txt", "khmereasytools/data/word_frequencies.txt",
             "benchmarks/accuracy/BUSINESS_OCR_PROTOCOL.md"]
    sources = ["benchmarks/accuracy/expanded-ocr/local-paired.json", "benchmarks/accuracy/document-ocr/local-results.json",
               "benchmarks/accuracy/small-vlm/local-results.json"]
    profile = {name: digest(ROOT / name) for name in paths + sources}
    token = hashlib.sha256(json.dumps(profile, sort_keys=True).encode()).hexdigest()
    rows = []
    for iterator in (expanded_records(), historical_records()):
        for item in iterator:
            rows.append(measured(item, token))
            if len(rows) % 500 == 0:
                print("Audited", len(rows), "predictions", flush=True)
    if len(rows) != 8736:
        raise ValueError("Expected 7,926 scene/KHOB and 810 historical predictions")
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["collection"], row["system"])].append(row)
        if row["collection"] == "historical":
            grouped[("historical_" + row["source_split"], row["system"])].append(row)
    summary = {}
    for (collection, system), selected in sorted(grouped.items()):
        if collection == "historical" and system.startswith("qwen"):
            continue
        values = {metric: aggregate([r["scores"][metric] for r in selected]) for metric in
                  ("compact_cer", "whitespace_unit_wer", "segmentation_assisted_wer")}
        values.update(samples=len(selected), empty=sum(r["empty"] for r in selected),
                      errors=sum(r["error"] for r in selected), capped=sum(r["capped"] is True for r in selected),
                      minimum_length_insertions=sum(r["minimum_length_insertions"] for r in selected))
        summary.setdefault(collection, {})[system] = values
    output = dict(schema_version=1, analysis_sha256=digest(Path(__file__)), metric_token=token,
                  inputs_and_metrics=profile, summary=summary, records=rows,
                  independent_audit=dict(passed=True, bit_vector_dp_selfchecks=checks, predictions=len(rows),
                                         independently_checked_projections=3 * len(rows)),
                  notes=["Posthoc added metrics from unchanged frozen predictions and references.",
                         "All metrics are unbounded micro edit ratios; no clipping or repetition removal.",
                         "Whitespace WER uses NFC + U+200B as a space + str.split(). Khmer whitespace is not human word gold.",
                         "Segmentation-assisted WER uses the pinned identical KET frequency decoder on both strings, retaining punctuation, case and digits; not human word gold.",
                         "S/D/I are one minimum-cost alignment; equally optimal decompositions can differ.",
                         "Historical Qwen results cover only the official 30 test pages.",
                         "KET-OCR denotes the existing Tesseract-based toolkit pipeline, not an independent recognizer."])
    write(DATA / "results-with-count-records.json", output)
    # Keep the source repository small: all per-prediction count records stay
    # in the private analysis cache, alongside the existing raw predictions.
    # Public summaries retain their hash, audit coverage and source identities.
    output.pop("records")
    output["private_count_records_sha256"] = digest(DATA / "results-with-count-records.json")
    write(PUBLIC / "results.json", output)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()

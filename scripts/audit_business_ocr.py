"""Independent final distance and aggregation audit for the new KH-FUNSD study."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_document_ocr import edit_distance, self_check
from document_ocr_metrics import visible_text

DATA = ROOT / ".evaluation/business_ocr"
PUBLIC = ROOT / "benchmarks/accuracy/business-ocr"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def project(text):
    from khmereasytools import khseg_spans
    normalized = unicodedata.normalize("NFC", text)
    return {"compact_cer": "".join(c for c in normalized if not c.isspace() and c != "\u200b"),
            "whitespace_unit_wer": normalized.replace("\u200b", " ").split(),
            "segmentation_assisted_wer": [s.text for s in khseg_spans(normalized)
                                            if s.kind not in ("boundary", "whitespace")]}


def main():
    public = read(PUBLIC / "results.json")
    private_path = DATA / "scored-count-records.json"
    private = read(private_path)
    if (not public["complete"] or digest(private_path) != public["private_count_records_sha256"] or
            any(c["missing"] for c in public["coverage"].values())):
        raise ValueError("A complete public/private report pair is required")
    transfer_path = DATA / "server-run/transfer-inventory.json"
    transfer = read(transfer_path)
    if transfer["counts"] != {"paddleocr-vl-1.6-4bit": 146, "deepseek-ocr-4bit": 146,
                              "qwen25-vl-3b": 30, "qwen3-vl-2b": 30} or len(transfer["files"]) != 352:
        raise ValueError("Remote transfer coverage differs")
    for relative, sha in transfer["files"].items():
        if digest(DATA / "server-run" / relative) != sha:
            raise ValueError("Transferred GPU file differs from remote final inventory")
    refs = {r["id"]: r for r in [json.loads(line) for line in (DATA / "references.jsonl").read_text().splitlines()]}
    pages = {p["id"]: p for p in read(DATA / "inputs.json")["pages"]}
    if len(refs) != 146 or len({p["image_sha256"] for p in pages.values()}) != 146:
        raise ValueError("Reference or image uniqueness differs")
    backend_by_system = {"tesseract-fast": "cpu", "khmereasytools-fast": "cpu", "surya-2": "surya",
        "paddleocr-vl-1.6-4bit": "mlx", "deepseek-ocr-4bit": "mlx", "qwen25-vl-3b": "qwen", "qwen3-vl-2b": "qwen3"}
    accumulators, rows_by_system, raw_hashes = {}, defaultdict(dict), {}
    measurements = private["records"]
    for row in measurements:
        system, page_id = row["system"], row["id"]
        if page_id in rows_by_system[system]:
            raise ValueError("Duplicate scored identity")
        rows_by_system[system][page_id] = row
        backend = backend_by_system[system]
        home = DATA if backend in ("cpu", "surya") else DATA / "server-run" / backend
        filename = hashlib.sha256(page_id.encode()).hexdigest() + ".json"
        path = home / "predictions" / row["evaluation_token"] / system / filename
        if digest(path) != row["raw_sha256"]:
            raise ValueError("Raw output differs from reported hash")
        raw = read(path)
        raw_hashes[backend + "/" + system + "/" + filename] = digest(path)
        prediction = raw["prediction"] if "prediction" in raw else visible_text(raw["raw"])
        reference = refs[page_id]["transcript"]
        if hashlib.sha256(reference.encode()).hexdigest() != row["reference_sha256"]:
            raise ValueError("Reference hash differs")
        page = pages[page_id]
        if (digest(DATA / page["image"]) != page["image_sha256"] or
                raw["image_sha256"] != page["image_sha256"] or refs[page_id]["human_reviewed"]):
            raise ValueError("Image or review provenance differs")
        left, right = project(reference), project(prediction)
        for name in left:
            metric = row["scores"][name]
            expected = edit_distance(left[name], right[name])
            if (metric["edits"] != expected or metric["reference_units"] != len(left[name]) or
                    metric["prediction_units"] != len(right[name]) or
                    metric["substitutions"] + metric["deletions"] + metric["insertions"] != expected or
                    min(metric[k] for k in ("substitutions", "deletions", "insertions")) < 0):
                raise ValueError("Independent distance, length or alignment sum differs")
        if bool(raw["error"]) != row["error"] or (not prediction.strip()) != row["empty"]:
            raise ValueError("Error/empty accounting differs")
        collections = ["matched-30"] if page["qwen_subset"] else []
        if not system.startswith("qwen"):
            collections += ["all-146", "category-" + page["category"], "acquisition-" + page["acquisition_folder"]]
            if "[ILLEGIBLE]" not in reference:
                collections.append("marker-free-sensitivity")
        for collection in collections:
            key = (collection, system)
            if key not in accumulators:
                accumulators[key] = dict(samples=0, errors=0, empty=0, capped=0, capped_unknown=0, marker_pages=0,
                    **{name: dict(substitutions=0, deletions=0, insertions=0, reference_units=0, prediction_units=0, edits=0) for name in left})
            a = accumulators[key]
            a["samples"] += 1
            a["errors"] += bool(raw["error"])
            a["empty"] += not prediction.strip()
            a["capped"] += raw.get("capped") is True
            a["capped_unknown"] += raw.get("capped") is None
            a["marker_pages"] += "[ILLEGIBLE]" in reference
            for name in left:
                for field in a[name]:
                    a[name][field] += row["scores"][name][field]
    if len(measurements) != 790:
        raise ValueError("Expected 790 distinct scored records")
    for system, backend in backend_by_system.items():
        expected = {key for key, p in pages.items() if not backend.startswith("qwen") or p["qwen_subset"]}
        if set(rows_by_system[system]) != expected:
            raise ValueError("Paired coverage differs")
    for (collection, system), actual in accumulators.items():
        for name in ("compact_cer", "whitespace_unit_wer", "segmentation_assisted_wer"):
            a = actual[name]
            a["error_rate"] = a["edits"] / a["reference_units"] if a["reference_units"] else None
        if actual != public["summary"][collection][system]:
            raise ValueError("Independent aggregate differs: " + collection + "/" + system)
    expected_keys = {(collection, system) for collection, systems in public["summary"].items() for system in systems}
    if set(accumulators) != expected_keys:
        raise ValueError("Public aggregation coverage differs")
    output = dict(passed=True, audit_sha256=digest(Path(__file__)),
                  results_sha256=digest(PUBLIC / "results.json"),
                  private_count_records_sha256=digest(private_path),
                  reference_freeze_token=public["reference_freeze"]["token"],
                  image_hashes_verified=146, prediction_records_verified=790,
                  independent_projections_verified=2370, independent_aggregates_verified=len(accumulators),
                  gpu_transfer_files_verified=352, remote_transfer_inventory_sha256=digest(transfer_path),
                  bit_vector_dp_selfchecks=self_check(),
                  raw_record_inventory_sha256=hashlib.sha256(json.dumps(raw_hashes, sort_keys=True).encode()).hexdigest(),
                  notes=["Minimum distances and source lengths independently recomputed for every prediction.",
                         "S/D/I nonnegative sums checked; optimal alignment tie-breaking is not independently certified.",
                         "All failed/empty/capped predictions included; literal reference markers retained.",
                         "Machine-generated references remain unreviewed; passing audit does not certify reference quality."])
    (PUBLIC / "consistency-audit.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()

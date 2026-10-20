"""Join blinded CUDA outputs with the frozen public references and audit scores."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_document_ocr import score as independent_score
from document_ocr_metrics import scored_record, summarize, visible_text
from evaluation_metrics import sha256, text_score
from expanded_ocr_metrics import paired_interval

DATA = ROOT / ".evaluation/small_vlm"
PRIMARY = ROOT / ".evaluation/full_document_ocr"
PUBLIC = ROOT / "benchmarks/accuracy/small-vlm"
SYSTEMS = ["qwen25-vl-3b", "qwen3-vl-2b"]


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    frozen = read(DATA / "server-run/frozen.json")
    token_body = {k: v for k, v in frozen.items() if k != "token"}
    if hashlib.sha256(json.dumps(token_body, sort_keys=True).encode()).hexdigest() != frozen["token"]:
        raise ValueError("Frozen CUDA identity token differs")
    files = {"evaluate_small_vlm.py": ROOT / "scripts/evaluate_small_vlm.py",
             "inputs.json": DATA / "inputs.json",
             "model-inventory.json": DATA / "model-inventory.json",
             "protocol.md": DATA / "protocol.md"}
    if set(frozen["files"]) != set(files):
        raise ValueError("Unexpected frozen CUDA dependency inventory")
    for name, expected in frozen["files"].items():
        if sha256(files[name]) != expected:
            raise ValueError("Frozen CUDA input or evaluator differs: " + name)
    main_frozen = read(PRIMARY / "frozen.json")
    main_body = {k: v for k, v in main_frozen.items() if k != "token"}
    if hashlib.sha256(json.dumps(main_body, sort_keys=True).encode()).hexdigest() != main_frozen["token"]:
        raise ValueError("Primary frozen identity token differs")
    inputs = read(DATA / "inputs.json")
    if inputs["source_evaluation_token"] != main_frozen["token"]:
        raise ValueError("Primary source experiment differs")
    for relative, expected in main_frozen["files"].items():
        if sha256(ROOT / relative) != expected:
            raise ValueError("Primary frozen scoring/input dependency differs: " + relative)
    all_pages = read(PRIMARY / "prepared.json")["pages"]
    pages = {p["id"]: p for p in all_pages if p["source_split"] == "test"}
    if (len(pages) != 30 or len(inputs["pages"]) != 30 or
            {p["id"] for p in inputs["pages"]} != set(pages)):
        raise ValueError("Official test selection differs")
    for item in inputs["pages"]:
        page = pages[item["id"]]
        if (any(item[k] != page[k] for k in
                ["collection", "source_split", "group", "image_sha256", "width", "height"]) or
                sha256(DATA / item["image"]) != page["image_sha256"]):
            raise ValueError("Paired input image differs")
        if hashlib.sha256(page["reference"].encode()).hexdigest() != page["reference_sha256"]:
            raise ValueError("Released original reference differs")
    baseline = {}
    for key in pages:
        name = hashlib.sha256(key.encode()).hexdigest() + ".json"
        row = read(PRIMARY / "predictions" / main_frozen["token"] / "tesseract-fast" / name)
        page = pages[key]
        if (row["evaluation_token"] != main_frozen["token"] or
                any(row[k] != page[k] for k in ["id", "source_split", "group", "collection"]) or
                row["system"] != "tesseract-fast" or
                row["score"] != text_score(page["reference"], row["prediction"])):
            raise ValueError("Tesseract pairing provenance differs")
        baseline[key] = row
    records, coverage, paired = [], {}, {}
    for system in SYSTEMS:
        directory = DATA / "server-run/predictions" / frozen["token"] / system
        raw_paths = sorted(directory.glob("*.json"))
        raw_rows = [read(p) for p in raw_paths]
        if len(raw_rows) != 30 or len({r["id"] for r in raw_rows}) != 30 or {r["id"] for r in raw_rows} != set(pages):
            raise ValueError("Missing or duplicate CUDA predictions: " + system)
        by_id = {}
        for raw, path in zip(raw_rows, raw_paths):
            page = pages[raw["id"]]
            if (raw["evaluation_token"] != frozen["token"] or raw["system"] != system or
                    path.stem != hashlib.sha256(raw["id"].encode()).hexdigest() or
                    raw["image_sha256"] != page["image_sha256"] or
                    any(raw[k] != page[k] for k in ["source_split", "group"])):
                raise ValueError("CUDA prediction provenance differs")
            prediction = visible_text(raw["raw"])
            extra = {k: raw[k] for k in ["generation_tokens", "capped", "image_grid_thw", "peak_allocated_bytes"]}
            extra.update(evaluation_token=frozen["token"],
                         source_evaluation_token=main_frozen["token"],
                         raw_record_sha256=sha256(path))
            row = scored_record(page, system, prediction, raw["seconds"], error=raw["error"], **extra)
            if independent_score(page["reference"], prediction) != row["score"]:
                raise ValueError("Independent edit-distance audit differs")
            records.append(row)
            by_id[row["id"]] = row
        pairs = [dict(group=pages[key]["group"], baseline=baseline[key]["score"],
                      toolkit=by_id[key]["score"]) for key in sorted(pages)]
        pair = paired_interval(pairs, replicates=5000, seed=20261018)
        pair["interpretation"] = "Descriptive paired cluster interval; negative favors the named comparison model"
        paired[system] = pair
        coverage[system] = dict(expected=30, completed=30, missing=[])
    result = dict(environment=frozen, primary_evaluation_token=main_frozen["token"],
                  reporter_sha256=sha256(Path(__file__)),
                  coverage=coverage, summary=summarize(records),
                  paired={"churro-sleuk-test": paired},
                  independent_audit=dict(input_images=30, predictions=60,
                                         distance_projections=180, passed=True),
                  records=[{k: v for k, v in r.items() if k != "prediction"} for r in records],
                  notes=["Exploratory addition; both Qwen models cover only the 30 official source-test pages.",
                         "Original BF16 CUDA Qwen implementations differ from the Mac VLM profiles.",
                         "Shared GPU and different batching prevent a controlled speed ranking.",
                         "Private business-image model drafts are not gold and are not scored here."])
    (PUBLIC / "local-results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(coverage=coverage, summary=result["summary"]["churro-sleuk-test"]), indent=2))


if __name__ == "__main__":
    main()

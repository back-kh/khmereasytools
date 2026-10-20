"""Score new KH-FUNSD predictions against frozen author-designated references.

--preview is private and explicitly incomplete. Public results require all
five systems on 146 images and both Qwen systems on the frozen matched 30.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_document_ocr import self_check
from document_ocr_metrics import visible_text
from evaluation_metrics import text_score
from ocr_word_metrics import aggregate
import report_ocr_word_errors as word_report

DATA = ROOT / ".evaluation/business_ocr"
PUBLIC = ROOT / "benchmarks/accuracy/business-ocr"
BACKENDS = {"tesseract-fast": "cpu", "khmereasytools-fast": "cpu", "surya-2": "surya",
            "paddleocr-vl-1.6-4bit": "mlx", "deepseek-ocr-4bit": "mlx",
            "qwen25-vl-3b": "qwen", "qwen3-vl-2b": "qwen3"}
METRICS = ("compact_cer", "whitespace_unit_wer", "segmentation_assisted_wer")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def token_check(profile):
    body = {k: v for k, v in profile.items() if k != "token"}
    if hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() != profile["token"]:
        raise ValueError("Frozen token differs")


def inputs():
    frozen = read(DATA / "reference-freeze.json")
    token_check(frozen)
    if digest(DATA / "references.jsonl") != frozen["references_sha256"]:
        raise ValueError("Frozen references differ")
    for relative, sha in frozen["metric_files"].items():
        if digest(ROOT / relative) != sha:
            raise ValueError("Frozen scoring dependency differs: " + relative)
    if (digest(DATA / "protocol.md") != frozen["protocol_sha256"] or
            digest(ROOT / "benchmarks/accuracy/BUSINESS_OCR_PROTOCOL.md") != frozen["protocol_sha256"]):
        raise ValueError("Protocol differs")
    pages = read(DATA / "inputs.json")["pages"]
    refs = [json.loads(line) for line in (DATA / "references.jsonl").read_text().splitlines()]
    by_id = {p["id"]: p for p in pages}
    references = {r["id"]: r for r in refs}
    if len(refs) != len(pages) or len(by_id) != 146 or set(by_id) != set(references):
        raise ValueError("Frozen source coverage differs")
    if sum(p["qwen_subset"] for p in pages) != 30:
        raise ValueError("Frozen Qwen subset differs")
    for page in pages:
        row = references[page["id"]]
        if (row["human_reviewed"] or row["image_sha256"] != page["image_sha256"] or
                hashlib.sha256(row["transcript"].encode()).hexdigest() != frozen["reference_hashes"][page["id"]] or
                digest(DATA / page["image"]) != page["image_sha256"]):
            raise ValueError("Reference or image provenance differs")
    return frozen, by_id, references


def execution_profiles(reference_frozen):
    profiles = {}
    for backend in ("cpu", "surya", "mlx", "qwen", "qwen3"):
        kind = "qwen" if backend == "qwen3" else backend
        directory = DATA if backend in ("cpu", "surya") else DATA / "server-run" / backend
        value = read(directory / ("frozen-" + kind + ".json"))
        token_check(value)
        if value["reference_freeze_token"] != reference_frozen["token"]:
            raise ValueError("Execution uses different references/selection")
        paths = {"evaluate_business_ocr.py": ROOT / "scripts/evaluate_business_ocr.py",
                 "inputs.json": directory / "inputs.json", "protocol.md": directory / "protocol.md"}
        for name, sha in value["files"].items():
            if digest(paths[name]) != sha:
                raise ValueError("Execution input or runner differs: " + name)
        for name, sha in value["reused_adapter"]["files"].items():
            if backend in ("cpu", "surya"):
                path = ROOT / name
            elif name.startswith("evaluate_"):
                path = ROOT / "scripts" / name
            else:
                path = directory / name
            if digest(path) != sha:
                raise ValueError("Reused adapter or profile differs: " + name)
        if backend == "qwen3":
            amendment = read(directory / "execution-amendment.json")
            if (digest(directory / "execution-amendment.json") != value["execution_amendment_sha256"] or
                    amendment["previous_prediction_count"] != 0 or
                    amendment["reference_freeze_token"] != reference_frozen["token"] or
                    value["reused_adapter"]["cuda_visible_devices"] != amendment["new_cuda_visible_devices"]):
                raise ValueError("Qwen3 pre-inference device amendment differs")
        profiles[backend] = (value, directory)
    return profiles


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    frozen, pages, refs = inputs()
    profiles = execution_profiles(frozen)
    word_report.DATA = DATA / "word-measurements"
    coverage, rows = {}, []
    private_records = []
    for system, backend in BACKENDS.items():
        profile, directory = profiles[backend]
        selected = {key for key, p in pages.items() if not backend.startswith("qwen") or p["qwen_subset"]}
        paths = sorted((directory / "predictions" / profile["token"] / system).glob("*.json"))
        found = {}
        for path in paths:
            row = read(path)
            if row["id"] in found or row["id"] not in selected or path.stem != hashlib.sha256(row["id"].encode()).hexdigest():
                raise ValueError("Duplicate, unknown or incorrectly named prediction")
            page = pages[row["id"]]
            if (row["system"] != system or row["evaluation_token"] != profile["token"] or
                    row["reference_freeze_token"] != frozen["token"] or
                    any(row[k] != page[k] for k in ("image_sha256", "qwen_subset", "category", "acquisition_folder"))):
                raise ValueError("Prediction provenance differs")
            prediction = row["prediction"] if "prediction" in row else visible_text(row["raw"])
            reference = refs[row["id"]]["transcript"]
            item = dict(id=row["id"], collection="kh-funsd", group=row["id"], system=system,
                        reference=reference, prediction=prediction, source_score=text_score(reference, prediction),
                        raw_sha256=digest(path), error=row["error"], capped=row.get("capped"))
            measured = word_report.measured(item, frozen["token"])
            measured = dict(measured, category=page["category"], acquisition_folder=page["acquisition_folder"],
                            qwen_subset=page["qwen_subset"], has_illegible_marker="[ILLEGIBLE]" in reference,
                            image_sha256=page["image_sha256"], evaluation_token=profile["token"])
            rows.append(measured)
            found[row["id"]] = measured
            private_records.append(dict(id=row["id"], system=system, prediction=prediction,
                                        raw_record_sha256=digest(path)))
        coverage[system] = dict(expected=len(selected), completed=len(found), missing=len(selected - set(found)))
    complete = not any(v["missing"] for v in coverage.values())
    if not args.preview and not complete:
        raise ValueError("Public report requires complete coverage: " + json.dumps(coverage))
    grouped = defaultdict(list)
    for row in rows:
        for collection in ["all-146"] + (["matched-30"] if row["qwen_subset"] else []):
            if collection == "all-146" and row["system"].startswith("qwen"):
                continue
            grouped[(collection, row["system"])].append(row)
        if not row["system"].startswith("qwen"):
            grouped[("category-" + row["category"], row["system"])].append(row)
            grouped[("acquisition-" + row["acquisition_folder"], row["system"])].append(row)
            if not row["has_illegible_marker"]:
                grouped[("marker-free-sensitivity", row["system"])].append(row)
    summary = {}
    for (collection, system), selected in sorted(grouped.items()):
        value = {name: aggregate([r["scores"][name] for r in selected]) for name in METRICS}
        value.update(samples=len(selected), errors=sum(r["error"] for r in selected),
                     empty=sum(r["empty"] for r in selected), capped=sum(r["capped"] is True for r in selected),
                     capped_unknown=sum(r["capped"] is None for r in selected),
                     marker_pages=sum(r["has_illegible_marker"] for r in selected))
        summary.setdefault(collection, {})[system] = value
    output = dict(schema_version=1, complete=complete, analysis_sha256=digest(Path(__file__)),
                  analysis_environment=word_report.analysis_environment(),
                  reference_freeze=frozen, execution_profiles={k: v[0] for k, v in profiles.items()},
                  coverage=coverage, summary=summary,
                  reference_summary=dict(pages=146, human_reviewed=0,
                      uncertain_pages=sum(bool(r["uncertain_spans"]) for r in refs.values()),
                      illegible_pages=sum("[ILLEGIBLE]" in r["transcript"] for r in refs.values()),
                      literal_illegible_markers=sum(r["transcript"].count("[ILLEGIBLE]") for r in refs.values()),
                      categories=dict(Counter(p["category"] for p in pages.values()))),
                  records=rows, independent_audit=dict(passed=True, predictions=len(rows),
                      independently_checked_projections=3 * len(rows), bit_vector_dp_selfchecks=self_check()),
                  interpretation="Agreement with author-designated Codex-generated unreviewed operational ground truth; not verified human OCR accuracy.",
                  notes=["KET-OCR is the existing Tesseract-based KhmerEasyTools pipeline, system ID khmereasytools-fast.",
                         "All pages retain literal [ILLEGIBLE] markers; marker-free sensitivity is separate and predefined.",
                         "Qwen covers the identical frozen matched30 subset; compare with matched30 primary results only.",
                         "Distinct image hashes do not certify independent documents, complete references or original158-unit dataset mapping.",
                         "Whitespace-unit and segmentation-assisted WER are not human-gold Khmer word WER.",
                         "No clipping, repeated-output repair, selective exclusion or failed-call retry.",
                         "Shared GPUs and different hosts preclude a controlled speed ranking; Qwen3 moved to GPU3 before its first prediction, with a separately hashed execution amendment."])
    if args.preview:
        output.pop("records")
        write(DATA / "provisional-summary.json", output)
    else:
        if len(rows) != 790:
            raise ValueError("Expected 730 primary and 60 Qwen records")
        write(DATA / "scored-count-records.json", output)
        write(DATA / "private-predictions.json", private_records)
        output.pop("records")
        output["private_count_records_sha256"] = digest(DATA / "scored-count-records.json")
        write(PUBLIC / "results.json", output)
    print(json.dumps(coverage, indent=2), flush=True)


if __name__ == "__main__":
    main()

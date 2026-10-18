"""Freeze private KH-FUNSD operational references before fresh inference."""
import hashlib
import json
from collections import defaultdict
from pathlib import Path
import shutil
import time

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ".evaluation/kh_funsd_local"
DATA = ROOT / ".evaluation/business_ocr"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    if DATA.exists():
        raise ValueError("Preserve existing experiment; preparation is one-time")
    selection = json.loads((SOURCE / "page-selection.json").read_text())
    refs = [json.loads(line) for line in (SOURCE / "reference-drafts.jsonl").read_text().splitlines()]
    by_id = {r["id"]: r for r in refs}
    if len(by_id) != len(refs) or len(refs) != len(selection["pages"]) or len(refs) != 146:
        raise ValueError("Expected 146 unique references and images")
    strata = defaultdict(list)
    for page in selection["pages"]:
        row = by_id[page["id"]]
        if row["human_reviewed"] or row["image_sha256"] != page["image_sha256"]:
            raise ValueError("Reference provenance differs")
        if hashlib.sha256(row["transcript"].encode()).hexdigest() != row["draft_sha256"]:
            raise ValueError("Transcript hash differs")
        if digest(SOURCE / page["image"]) != page["image_sha256"]:
            raise ValueError("Input image differs")
        strata[(page["category"], page["acquisition_folder"])].append(page)
    allocations = {key: len(pages) * 30 // 146 for key, pages in strata.items()}
    remainder = 30 - sum(allocations.values())
    order = sorted(strata, key=lambda key: (-(len(strata[key]) * 30 % 146), key))
    for key in order[:remainder]:
        allocations[key] += 1
    selected = set()
    for key, pages in strata.items():
        pages.sort(key=lambda p: hashlib.sha256(("khmereasytools-business-ocr-20261018/" + p["id"]).encode()).hexdigest())
        selected.update(p["id"] for p in pages[:allocations[key]])
    if len(selected) != 30:
        raise ValueError("Subset allocation failed")
    DATA.mkdir()
    (DATA / "images").symlink_to((SOURCE / "images").resolve(), target_is_directory=True)
    shutil.copy2(SOURCE / "reference-drafts.jsonl", DATA / "references.jsonl")
    shutil.copy2(ROOT / "benchmarks/accuracy/BUSINESS_OCR_PROTOCOL.md", DATA / "protocol.md")
    pages = [dict(id=p["id"], image=p["image"], image_sha256=p["image_sha256"],
                  source_sha256=p["source_sha256"], category=p["category"],
                  acquisition_folder=p["acquisition_folder"], collection="kh-funsd",
                  group=p["id"], source_split="author-supplied evaluation", qwen_subset=p["id"] in selected)
             for p in selection["pages"]]
    manifest = dict(created_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        source_selection_sha256=digest(SOURCE / "page-selection.json"),
        references_sha256=digest(DATA / "references.jsonl"),
        protocol_sha256=digest(DATA / "protocol.md"),
        prepared_by_sha256=digest(Path(__file__)),
        reference_policy="Author-designated machine-generated operational ground truth; zero independently human-reviewed pages; literal markers retained",
        pages=146, qwen_pages=30,
        strata=[dict(category=k[0], acquisition_folder=k[1], pages=len(strata[k]), qwen_pages=allocations[k]) for k in sorted(strata)],
        reference_hashes={r["id"]: r["draft_sha256"] for r in refs},
        metric_files={name: digest(ROOT / name) for name in [
            "scripts/evaluation_metrics.py", "scripts/document_ocr_metrics.py",
            "scripts/ocr_word_metrics.py", "khmereasytools/segmentation.py", "khmereasytools/lexicon.py",
            "khmereasytools/data/khmer_words.txt", "khmereasytools/data/word_frequencies.txt"]})
    manifest["token"] = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    write(DATA / "reference-freeze.json", manifest)
    write(DATA / "inputs.json", dict(source_evaluation_token=manifest["token"], pages=pages))
    print("Frozen references", manifest["token"], "146 pages; Qwen 30", flush=True)


if __name__ == "__main__":
    main()

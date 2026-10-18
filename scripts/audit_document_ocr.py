"""Independently audit frozen document OCR inputs, coverage and edit counts.

Uses only the standard library and a separate bit-vector Levenshtein
implementation, rather than the scorer used by the inference harness.
Never writes source transcripts or recognized text to the public report.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / ".evaluation/full_document_ocr"
PUBLIC = ROOT / "benchmarks/accuracy/document-ocr"
SYSTEMS = ["tesseract-fast", "khmereasytools-fast", "surya-2",
           "paddleocr-vl-1.6-4bit", "deepseek-ocr-4bit"]


def digest_bytes(value):
    return hashlib.sha256(value).hexdigest()


def projection(text):
    return "".join(c for c in unicodedata.normalize("NFC", text)
                   if not c.isspace() and c != "\u200b")


def edit_distance(left, right):
    """Exact unit-cost Levenshtein distance using Python integer bit vectors."""
    if len(left) > len(right):
        left, right = right, left
    size = len(left)
    if not size:
        return len(right)
    positions = {}
    for i, symbol in enumerate(left):
        positions[symbol] = positions.get(symbol, 0) | (1 << i)
    positive, negative = (1 << size) - 1, 0
    distance, top = size, 1 << (size - 1)
    for symbol in right:
        equal = positions.get(symbol, 0)
        horizontal = (((equal & positive) + positive) ^ positive) | equal | negative
        up = negative | ~(horizontal | positive)
        down = positive & horizontal
        distance += bool(up & top) - bool(down & top)
        up = (up << 1) | 1
        negative = up & horizontal
        positive = (down << 1) | ~(horizontal | up)
    return distance


def slow_distance(left, right):
    previous = list(range(len(right) + 1))
    for i, symbol in enumerate(left, 1):
        row = [i]
        for j, other in enumerate(right, 1):
            row.append(min(row[-1] + 1, previous[j] + 1,
                           previous[j - 1] + (symbol != other)))
        previous = row
    return previous[-1]


def self_check():
    rng = random.Random(20261018)
    alphabet = "abកខ្\u17b6\u0301\u200b "
    pairs = [("", ""), ("", "ក"), ("abc", "abc"), ("abc", "xyz"),
             ("ab", "ba"), ("កខ", "ខកខ"), (["ក", "abc"], ["abc"])]
    pairs.extend(("".join(rng.choices(alphabet, k=rng.randrange(32))),
                  "".join(rng.choices(alphabet, k=rng.randrange(32))))
                 for _ in range(1000))
    pairs.extend(("".join(rng.choices(alphabet, k=rng.randrange(64, 360))),
                  "".join(rng.choices(alphabet, k=rng.randrange(64, 360))))
                 for _ in range(32))
    for left, right in pairs:
        assert edit_distance(left, right) == slow_distance(left, right)
    return len(pairs)


def score(reference, prediction):
    compact_ref, compact_pred = projection(reference), projection(prediction)
    space_ref = " ".join(unicodedata.normalize("NFC", reference).split())
    space_pred = " ".join(unicodedata.normalize("NFC", prediction).split())
    return dict(reference_codepoints=len(compact_ref),
                codepoint_edits=edit_distance(compact_ref, compact_pred),
                exact_compact=compact_ref == compact_pred,
                spacefold_reference_codepoints=len(space_ref),
                spacefold_codepoint_edits=edit_distance(space_ref, space_pred),
                reference_whitespace_units=len(space_ref.split()),
                whitespace_unit_edits=edit_distance(space_ref.split(), space_pred.split()))


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    self_checks = self_check()
    frozen = read(DATA / "frozen.json")
    token_body = {k: v for k, v in frozen.items() if k != "token"}
    assert digest_bytes(json.dumps(token_body, sort_keys=True).encode()) == frozen["token"]
    for relative, expected in frozen["files"].items():
        assert digest_bytes((ROOT / relative).read_bytes()) == expected, relative
    pages = read(DATA / "prepared.json")["pages"]
    public_pages = read(PUBLIC / "source-inventory.json")["pages"]
    assert len(pages) == 150 and len(public_pages) == 150
    assert [{k: v for k, v in page.items() if k != "reference"} for page in pages] == public_pages
    assert Counter(p["source_split"] for p in pages) == {"test": 30, "train": 120}
    candidates = read(DATA / "churro-khmer-candidates.json")
    assert Counter(p["split"] for p in candidates) == {"test": 30, "dev": 30, "train": 562}
    seed = read(PUBLIC / "source-inventory.json")["seed"]
    train = sorted((p for p in candidates if p["split"] == "train"),
                   key=lambda p: digest_bytes((seed + p["row"]["example_id"]).encode()))[:120]
    selected = {p["row"]["example_id"] for p in train}
    selected.update(p["row"]["example_id"] for p in candidates if p["split"] == "test")
    assert selected == {p["id"] for p in pages}
    candidates = {p["row"]["example_id"]: p for p in candidates}
    for page in pages:
        assert page["reference"] == candidates[page["id"]]["row"]["original_transcription"]
        assert digest_bytes(page["reference"].encode()) == page["reference_sha256"]
        assert digest_bytes((DATA / page["image"]).read_bytes()) == page["image_sha256"]
        stem = page["id"].split("/", 1)[1]
        assert digest_bytes((DATA / "sources/churro" / (stem + ".jpg")).read_bytes()) == page["source_sha256"]
    assert len({p["image_sha256"] for p in pages}) == 150
    assert len({p["reference_sha256"] for p in pages}) == 150
    by_page = {p["id"]: p for p in pages}
    all_records, totals = {}, {}
    public = read(PUBLIC / "local-results.json")
    assert public["environment"] == frozen
    assert set(public["coverage"]) == set(SYSTEMS)
    for system in SYSTEMS:
        records = {}
        for path in (DATA / "predictions" / frozen["token"] / system).glob("*.json"):
            record = read(path)
            assert path.stem == digest_bytes(record["id"].encode())
            assert record["id"] not in records
            assert record["evaluation_token"] == frozen["token"]
            assert record["system"] == system
            page = by_page[record["id"]]
            assert all(record[k] == page[k] for k in ["id", "collection", "source_split", "group"])
            assert score(page["reference"], record["prediction"]) == record["score"]
            records[record["id"]] = record
        assert set(records) == set(by_page), system + " is incomplete"
        all_records[system] = records
        for split in [None, "test", "train"]:
            collection = "churro-sleuk" + ("-" + split if split else "")
            values = [r for r in records.values() if split is None or r["source_split"] == split]
            denominator = sum(r["score"]["reference_codepoints"] for r in values)
            edits = sum(r["score"]["codepoint_edits"] for r in values)
            checks = dict(samples=len(values), reference_codepoints=denominator,
                          codepoint_edits=edits, compact_codepoint_cer=edits / denominator,
                          exact_compact=sum(r["score"]["exact_compact"] for r in values),
                          empty=sum(not r["prediction"].strip() for r in values),
                          failures=sum(bool(r["error"]) for r in values),
                          capped=sum(bool(r.get("capped")) for r in values))
            for key, value in checks.items():
                assert public["summary"][collection][system][key] == value, (system, collection, key)
            totals.setdefault(collection, {})[system] = checks
    public_records = {(r["system"], r["id"]): r for r in public["records"]}
    assert len(public_records) == len(public["records"]) == 750
    for system, records in all_records.items():
        for identity, row in records.items():
            assert public_records[(system, identity)] == {k: v for k, v in row.items()
                                                         if k not in {"prediction", "raw", "prompt"}}
    assert all(v == dict(expected=150, completed=150, missing=[]) for v in public["coverage"].values())
    identical = sum(projection(all_records[SYSTEMS[0]][key]["prediction"]) ==
                    projection(all_records[SYSTEMS[1]][key]["prediction"]) for key in by_page)
    repeated = {}
    previous = read(PUBLIC / "protocol-amendment.json")["initial_evaluation_token"]
    for system in SYSTEMS[:2]:
        original = [read(p) for p in (DATA / "predictions" / previous / system).glob("*.json")]
        assert len(original) == 150
        matched = sum(projection(row["prediction"]) ==
                      projection(all_records[system][row["id"]]["prediction"]) for row in original)
        repeated[system] = dict(repeated_pages=150, identical_compact_predictions=matched)
    native = read(PUBLIC / "native-validation.json")
    assert len(native["records"]) == 6
    assert len({r["wheel_sha256"] for r in native["records"]}) == 1
    assert all(r["source_revision"] == native["source_revision"] for r in native["records"])
    native_test_count = native["records"][0]["tests"]
    assert native_test_count >= 157
    assert all(r["tests"] == native_test_count and not r["failures"] and not r["errors"] for r in native["records"])
    assert sum(r["real_ocr"] and r["real_pos"] and r["skipped"] == 1 for r in native["records"]) == 3
    result = dict(evaluation_token=frozen["token"], source_revision=frozen["source_revision"],
                  auditor_sha256=digest_bytes(Path(__file__).read_bytes()),
                  independent_distance="Exact integer bit-vector Levenshtein; standard-library implementation",
                  distance_self_checks=self_checks, input_hashes_verified=150,
                  unique_page_image_hashes=150, unique_raw_reference_hashes=150,
                  source_split_counts={"test": 30, "train": 120},
                  selected_from_source_inventory=622,
                  prediction_records_verified=750,
                  independent_score_projections_verified=2250,
                  tesseract_toolkit_identical_compact_pages=identical,
                  repeated_cpu_attempts=repeated,
                  native_installation_records_verified=6, tests_per_native_run=native_test_count, summary=totals,
                  notes=["Repeated CPU runs are repeatability evidence, not additional independent pages.",
                         "Source filename groups are not verified independent books.",
                         "This audit validates bookkeeping and exact edit counts, not transcript correctness."])
    path = PUBLIC / "consistency-audit.json"
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("Independent audit passed: 150 inputs, 750 predictions, 2250 distance projections")


if __name__ == "__main__":
    main()

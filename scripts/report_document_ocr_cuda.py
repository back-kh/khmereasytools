"""Join three frozen Mac profiles and two blinded CUDA profiles locally."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from document_ocr_metrics import scored_record, summarize, visible_text
from evaluation_metrics import sha256, text_score
from expanded_ocr_metrics import paired_interval

PRIMARY = ROOT / ".evaluation/full_document_ocr"
CUDA = ROOT / ".evaluation/document_mlx_cuda"
PUBLIC = ROOT / "benchmarks/accuracy/document-ocr"
MAC_SYSTEMS = ["tesseract-fast", "khmereasytools-fast", "surya-2"]
CUDA_SYSTEMS = ["paddleocr-vl-1.6-4bit", "deepseek-ocr-4bit"]
SYSTEMS = MAC_SYSTEMS + CUDA_SYSTEMS


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def verify_token(profile):
    body = {k: v for k, v in profile.items() if k != "token"}
    if hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() != profile["token"]:
        raise ValueError("Frozen identity token differs")


def complete_records(directory, expected):
    result = {}
    for path in sorted(directory.glob("*.json")):
        row = read(path)
        identity = row["id"]
        if path.stem != hashlib.sha256(identity.encode()).hexdigest() or identity in result:
            raise ValueError("Duplicate or incorrectly named prediction record")
        result[identity] = (row, path)
    if set(result) != set(expected):
        raise ValueError("Incomplete profile: " + directory.name + " (" + str(len(result)) +
                         "/" + str(len(expected)) + ")")
    return result


def verify_inputs():
    source = read(PRIMARY / "frozen.json")
    cuda = read(CUDA / "server-run/frozen.json")
    verify_token(source)
    verify_token(cuda)
    for relative, expected in source["files"].items():
        if sha256(ROOT / relative) != expected:
            raise ValueError("Original frozen dependency differs: " + relative)
    paths = {"evaluate_mlx_cuda.py": ROOT / "scripts/evaluate_mlx_cuda.py",
             "inputs.json": CUDA / "inputs.json",
             "model-inventory.json": CUDA / "model-inventory.json",
             "protocol.md": CUDA / "protocol.md",
             "framework-inventory.json": CUDA / "framework-inventory.json"}
    if set(cuda["files"]) != set(paths):
        raise ValueError("Unexpected CUDA dependency inventory")
    for name, expected in cuda["files"].items():
        if sha256(paths[name]) != expected:
            raise ValueError("Frozen CUDA dependency differs: " + name)
    amendment = read(PUBLIC / "execution-amendment.json")
    if (amendment["source_evaluation_token"] != source["token"] or
            amendment["cuda_evaluation_token"] != cuda["token"] or
            amendment["moved_systems"] != CUDA_SYSTEMS or
            amendment["retained_mac_systems"] != MAC_SYSTEMS):
        raise ValueError("Declared execution amendment differs")
    inputs = read(CUDA / "inputs.json")
    pages = read(PRIMARY / "prepared.json")["pages"]
    if (len(pages) != 150 or len({p["id"] for p in pages}) != 150 or
            sum(p["source_split"] == "test" for p in pages) != 30 or
            sum(p["source_split"] == "train" for p in pages) != 120):
        raise ValueError("Original page selection differs")
    if (inputs["reference_text_supplied"] is not False or
            inputs["source_evaluation_token"] != source["token"] or
            cuda["source_evaluation_token"] != source["token"] or
            inputs["pages"] != [{k: v for k, v in p.items() if k != "reference"} for p in pages]):
        raise ValueError("Blinded CUDA selection differs")
    original_models = read(PUBLIC / "model-inventory.json")
    expected_models = {name: original_models[name] for name in
                       ["mlx-community/DeepSeek-OCR-4bit", "mlx-community/PaddleOCR-VL-1.6-4bit"]}
    if read(CUDA / "model-inventory.json") != expected_models:
        raise ValueError("Moved checkpoint inventory differs")
    for key, expected in dict(max_tokens=4096, timeout_seconds=240, temperature=0.0,
                              seed=20261018, batch_size=1).items():
        if cuda[key] != expected:
            raise ValueError("Recognition option changed: " + key)
    for page in pages:
        if (sha256(PRIMARY / page["image"]) != page["image_sha256"] or
                hashlib.sha256(page["reference"].encode()).hexdigest() != page["reference_sha256"]):
            raise ValueError("Original source image or transcript differs")
    for system in CUDA_SYSTEMS:
        if list((PRIMARY / "predictions" / source["token"] / system).glob("*.json")):
            raise ValueError("Superseded Mac profile has test predictions; do not select between devices")
    return source, cuda, amendment, {p["id"]: p for p in pages}


def main():
    source, cuda, amendment, pages = verify_inputs()
    controls = read(PUBLIC / "cuda-execution/setup-controls.json")["controls"]
    inputs = {}
    # Require all five complete profiles before writing any composite scores.
    for system in SYSTEMS:
        home = PRIMARY if system in MAC_SYSTEMS else CUDA / "server-run"
        profile = source if system in MAC_SYSTEMS else cuda
        inputs[system] = complete_records(home / "predictions" / profile["token"] / system, pages)
    rows, environments = [], {}
    for system in SYSTEMS:
        profile = source if system in MAC_SYSTEMS else cuda
        environments[system] = profile
        for identity in sorted(pages):
            page = pages[identity]
            raw, path = inputs[system][identity]
            if (raw["evaluation_token"] != profile["token"] or raw["system"] != system or
                    any(raw[k] != page[k] for k in ["collection", "group", "source_split"])):
                raise ValueError("Prediction provenance differs")
            if system in MAC_SYSTEMS:
                if raw["score"] != text_score(page["reference"], raw["prediction"]):
                    raise ValueError("Original score differs")
                row = raw
            else:
                if (raw["source_evaluation_token"] != source["token"] or
                        raw["image_sha256"] != page["image_sha256"] or
                        raw["started_utc"] < cuda["created_utc"] or
                        raw["started_utc"] < amendment["created_utc"]):
                    raise ValueError("CUDA source identity or execution order differs")
                expected_prompt = cuda["prompts"][system]
                expected_format = controls[system + "-english-control"]["formatted_prompt_sha256"]
                if (raw["prompt"] != expected_prompt or
                        raw["formatted_prompt_sha256"] != expected_format):
                    raise ValueError("Recognition prompt differs")
                extra = {k: raw[k] for k in ["raw", "generation_tokens", "capped", "started_utc",
                    "peak_allocated_bytes", "formatted_prompt_sha256", "image_sha256", "prompt"]}
                row = scored_record(page, system, visible_text(raw["raw"]), raw["seconds"],
                                    error=raw["error"], **extra)
                row.update(evaluation_token=cuda["token"], source_evaluation_token=source["token"],
                           raw_record_sha256=sha256(path))
                filename = hashlib.sha256(identity.encode()).hexdigest() + ".json"
                write(PRIMARY / "predictions" / cuda["token"] / system / filename, row)
            rows.append(row)
    paired = {}
    for collection in ["churro-sleuk", "churro-sleuk-test", "churro-sleuk-train"]:
        selected = {key for key, page in pages.items()
                    if collection == "churro-sleuk" or collection.endswith("-" + page["source_split"])}
        by_system = {s: {r["id"]: r for r in rows if r["system"] == s and r["id"] in selected}
                     for s in SYSTEMS}
        baseline = by_system["tesseract-fast"]
        for system in SYSTEMS[1:]:
            pairs = [dict(group=pages[key]["group"], baseline=baseline[key]["score"],
                          toolkit=by_system[system][key]["score"]) for key in sorted(selected)]
            paired.setdefault(collection, {})[system] = paired_interval(pairs, replicates=5000, seed=20261018)
    result = dict(schema_version=2, source_environment=source, backend_environments=environments,
        execution_amendment=amendment, reporter_sha256=sha256(Path(__file__)),
        coverage={s: dict(expected=150, completed=150, missing=[]) for s in SYSTEMS},
        summary=summarize(rows), paired=paired,
        records=[{k: v for k, v in row.items() if k not in {"prediction", "raw", "prompt"}} for row in rows],
        notes=["Three Mac profiles and two CUDA profiles retain distinct environment tokens.",
               "CUDA inference receives no references; scoring joins released transcripts locally.",
               "All 150 pages remain in every system denominator, including failures.",
               "Source training pages are a stress test, not the official held-out partition."])
    write(PUBLIC / "local-results.json", result)
    print(json.dumps(dict(coverage=result["coverage"], summary=result["summary"]), indent=2))


if __name__ == "__main__":
    main()

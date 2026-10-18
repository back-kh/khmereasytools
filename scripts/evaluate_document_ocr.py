"""Run frozen full-page OCR baselines from installed research environments.

Use --freeze after acquisition and smoke checks, then one --system per process.
Never imports a heavyweight OCR package into the distributed toolkit.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from evaluation_metrics import compact, sha256, text_score, provenance
from document_ocr_metrics import scored_record, summarize, visible_text
from expanded_ocr_metrics import paired_interval

DATA = ROOT / ".evaluation/full_document_ocr"
PUBLIC = ROOT / "benchmarks/accuracy/document-ocr"
PROTOCOL = ROOT / "benchmarks/accuracy/DOCUMENT_OCR_PROTOCOL.md"
SYSTEMS = ["tesseract-fast", "khmereasytools-fast", "surya-2", "paddleocr-vl-1.6-4bit", "deepseek-ocr-4bit"]
MODELS = {"surya-2": "surya-ocr-2-gguf", "paddleocr-vl-1.6-4bit": "PaddleOCR-VL-1.6-4bit",
          "deepseek-ocr-4bit": "DeepSeek-OCR-4bit"}
MAX_TOKENS = 4096
TIMEOUT = 240


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def identity():
    paths = [PROTOCOL, Path(__file__), ROOT / "scripts/document_ocr_metrics.py",
             ROOT / "scripts/evaluation_metrics.py", ROOT / "scripts/fetch_document_ocr.py",
             DATA / "prepared.json", PUBLIC / "source-inventory.json", PUBLIC / "model-inventory.json"]
    result = {p.relative_to(ROOT).as_posix(): sha256(p) for p in paths}
    versions = {}
    for name in ["khmereasytools", "pillow", "pytesseract", "surya-ocr", "mlx-vlm", "mlx", "torch",
                 "transformers", "pypdfium2", "rapidfuzz", "numpy", "beautifulsoup4"]:
        versions[name] = importlib.metadata.version(name)
    import khmereasytools as ket
    if ROOT / "khmereasytools" in Path(ket.__file__).parents:
        raise ValueError("Use an installed wheel with python -I")
    package = Path(ket.__file__).parent
    expected_files = {p for p in subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", "b062be0", "khmereasytools"], cwd=str(ROOT)).decode().splitlines()
        if p.endswith(".py")}
    if {"khmereasytools/" + p.relative_to(package).as_posix() for p in package.rglob("*.py")} != expected_files:
        raise ValueError("Installed toolkit source file set changed")
    digest = hashlib.sha256()
    for p in sorted(package.rglob("*.py")):
        relative = "khmereasytools/" + p.relative_to(package).as_posix()
        expected = subprocess.check_output(["git", "show", "b062be0:" + relative], cwd=str(ROOT))
        if p.read_bytes() != expected:
            raise ValueError("Installed toolkit runtime changed: " + relative)
        digest.update(relative.encode("utf-8")); digest.update(expected)
    model_dir = ROOT / ".evaluation/ocr-target/tessdata-mixed"
    tess_models = {name: sha256(model_dir / (name + ".traineddata")) for name in ["khm", "eng"]}
    if tess_models != {"khm": "47f110575341b322052f3becbefee61a3ecf1ef549352b5d4d33d28afe30d099",
                       "eng": "7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2"}:
        raise ValueError("Tesseract model identity changed")
    return dict(files=result, versions=versions, python=platform.python_version(), platform=platform.platform(),
                tesseract=subprocess.check_output(["tesseract", "--version"]).decode().splitlines()[0],
                llama_cpp=subprocess.check_output(["llama-server", "--version"], stderr=subprocess.STDOUT).decode(),
                runtime_sha256=digest.hexdigest(), tessdata=tess_models, max_tokens=MAX_TOKENS,
                timeout_seconds=TIMEOUT, surya_batch_size=4)


def freeze():
    prepared = json.loads((DATA / "prepared.json").read_text())["pages"]
    if len(prepared) != 150 or any(p["collection"] != "churro-sleuk" for p in prepared):
        raise ValueError("Expected exactly 150 historical page images")
    for page in prepared:
        if sha256(DATA / page["image"]) != page["image_sha256"]:
            raise ValueError("Input changed before freeze")
        if hashlib.sha256(page["reference"].encode("utf-8")).hexdigest() != page["reference_sha256"]:
            raise ValueError("Reference changed before freeze")
    state = identity()
    state["source_revision"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(ROOT)).decode().strip()
    state["created_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    state["token"] = hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()
    path = DATA / "frozen.json"
    if path.exists():
        raise ValueError("Evaluation is already frozen; preserve prior measurements")
    write_json(path, state)
    write_json(PUBLIC / "environment.json", state)
    print("Frozen", state["token"], flush=True)


def verify(system):
    frozen = json.loads((DATA / "frozen.json").read_text())
    actual = identity()
    for name, value in actual.items():
        if value != frozen[name]:
            raise ValueError("Frozen evaluation differs: " + name)
    if system in MODELS:
        inventory = json.loads((PUBLIC / "model-inventory.json").read_text())
        found = next(x for x in inventory.values() if x["directory"] == MODELS[system])
        for row in found["files"]:
            if sha256(DATA / "models" / found["directory"] / row["path"]) != row["sha256"]:
                raise ValueError("OCR baseline file differs: " + row["path"])
    return frozen


def deadline(signum, frame):
    raise TimeoutError("Per-call wall-clock limit exceeded")


def tess_page(payload):
    page, system = payload
    os.environ["OMP_THREAD_LIMIT"] = "1"
    os.environ["TESSDATA_PREFIX"] = str(ROOT / ".evaluation/ocr-target/tessdata-mixed")
    from PIL import Image
    import pytesseract
    path = DATA / page["image"]
    if sha256(path) != page["image_sha256"]:
        raise ValueError("Page input changed")
    start = time.monotonic(); error = None; prediction = ""
    try:
        if system == "tesseract-fast":
            with Image.open(path) as im:
                prediction = pytesseract.image_to_string(im, lang="khm+eng", config="--oem 1 --psm 3", timeout=TIMEOUT)
        else:
            import khmereasytools as ket
            prediction = ket.khocr_layout(str(path), lang="khm+eng", psm=3, preprocess="auto",
                reading_order="engine", segment=False, min_confidence=0, timeout=TIMEOUT).text
    except Exception as exc:
        error = type(exc).__name__ + ": " + str(exc)[:500]
    return scored_record(page, system, prediction, time.monotonic() - start, error=error)


def surya_start():
    directory = DATA / "models/surya-ocr-2-gguf"
    os.environ.update(SURYA_INFERENCE_BACKEND="llamacpp", SURYA_GGUF_LOCAL_MODEL_PATH=str(directory / "surya-2.gguf"),
        SURYA_GGUF_LOCAL_MMPROJ_PATH=str(directory / "surya-2-mmproj.gguf"), SURYA_INFERENCE_PARALLEL="4",
        SURYA_MAX_TOKENS_FULL_PAGE=str(MAX_TOKENS), SURYA_INFERENCE_TIMEOUT_SECONDS=str(TIMEOUT),
        SURYA_FULLPAGE_REGEN="false", DISABLE_TQDM="true")
    from surya.inference import SuryaInferenceManager
    from surya.recognition import RecognitionPredictor
    manager = SuryaInferenceManager(lazy=False)
    return manager, RecognitionPredictor(manager)


def run_surya(pages, save):
    from PIL import Image
    manager, predictor = surya_start()
    try:
        for start in range(0, len(pages), 4):
            group = pages[start:start + 4]
            images = []
            for page in group:
                if sha256(DATA / page["image"]) != page["image_sha256"]:
                    raise ValueError("Page input changed")
                with Image.open(DATA / page["image"]) as im:
                    images.append(im.convert("RGB"))
            begun = time.monotonic(); outputs = None; error = None
            try:
                # The library batches independent pages through four inference slots.
                signal.alarm(TIMEOUT + 20)
                outputs = predictor(images, full_page=True)
            except Exception as exc:
                error = type(exc).__name__ + ": " + str(exc)[:500]
            finally:
                signal.alarm(0)
                for im in images:
                    im.close()
            elapsed = time.monotonic() - begun
            for i, page in enumerate(group):
                raw = outputs[i].model_dump() if outputs is not None else None
                block_errors = sum(x.error for x in outputs[i].blocks) if outputs is not None else 0
                text = "\n".join(visible_text(block.html) for block in sorted(outputs[i].blocks,
                    key=lambda x: x.reading_order) if not block.skipped) if outputs is not None else ""
                record = scored_record(page, "surya-2", text, elapsed / len(group),
                    error=error or ("block_errors=" + str(block_errors) if block_errors else None), raw=raw,
                    batch_size=len(group), batch_seconds=elapsed, capped=None)
                save(record)
            if error:
                manager.stop()
                manager, predictor = surya_start()
    finally:
        manager.stop()


def run_mlx(pages, system, save):
    import mlx.core as mx
    from mlx_vlm import load, generate
    from mlx_vlm.prompt_utils import apply_chat_template
    directory = DATA / "models" / MODELS[system]
    model, processor = load(str(directory))
    config = json.loads((directory / "config.json").read_text())
    # apply_chat_template inserts the image marker; passing it again produces
    # a 2-image-token/1-image mismatch in the native DeepSeek processor.
    prompt = "OCR:" if system.startswith("paddleocr") else "Free OCR."
    formatted = apply_chat_template(processor, config, prompt, num_images=1)
    if system == "deepseek-ocr-4bit" and formatted.count("<image>") != 1:
        raise ValueError("DeepSeek template must contain exactly one image marker")
    for page in pages:
        path = DATA / page["image"]
        if sha256(path) != page["image_sha256"]:
            raise ValueError("Page input changed")
        start = time.monotonic(); error = None; prediction = ""; raw = None; tokens = 0; capped = False
        try:
            mx.random.seed(20261018)
            signal.alarm(TIMEOUT)
            output = generate(model, processor, formatted, image=[str(path)],
                              max_tokens=MAX_TOKENS, temperature=0.0, verbose=False)
            raw = output.text
            prediction = visible_text(raw)
            tokens = output.generation_tokens
            capped = tokens >= MAX_TOKENS or output.finish_reason == "length"
        except Exception as exc:
            error = type(exc).__name__ + ": " + str(exc)[:500]
        finally:
            signal.alarm(0)
        save(scored_record(page, system, prediction, time.monotonic() - start, error=error,
                           raw=raw, generation_tokens=tokens, capped=capped, prompt=prompt))
        mx.clear_cache()


def run(system, workers):
    frozen = verify(system)
    pages = json.loads((DATA / "prepared.json").read_text())["pages"]
    token = frozen["token"]
    destination = DATA / "predictions" / token / system
    destination.mkdir(parents=True, exist_ok=True)
    todo = []
    def filename(identity):
        return destination / (hashlib.sha256(identity.encode()).hexdigest() + ".json")
    for page in pages:
        if not filename(page["id"]).exists():
            todo.append(page)
    print(system, "remaining", len(todo), "of", len(pages), flush=True)
    completed = len(pages) - len(todo)
    def save(record):
        nonlocal completed
        record["evaluation_token"] = token
        write_json(filename(record["id"]), record)
        completed += 1
        print(system, completed, "/", len(pages), record["id"], "seconds", round(record["seconds"], 2),
              "error", record["error"], flush=True)
    signal.signal(signal.SIGALRM, deadline)
    if system in SYSTEMS[:2]:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(tess_page, (page, system)) for page in todo]
            for future in as_completed(futures):
                save(future.result())
    elif system == "surya-2":
        run_surya(todo, save)
    else:
        run_mlx(todo, system, save)
    print(system, "complete", flush=True)


def report():
    frozen = json.loads((DATA / "frozen.json").read_text())
    pages = json.loads((DATA / "prepared.json").read_text())["pages"]
    rows = []
    coverage = {}
    for system in SYSTEMS:
        paths = list((DATA / "predictions" / frozen["token"] / system).glob("*.json"))
        values = [json.loads(path.read_text()) for path in paths]
        if len({r["id"] for r in values}) != len(values):
            raise ValueError("Duplicate prediction identities")
        expected = {p["id"]: p for p in pages}
        for record in values:
            page = expected[record["id"]]
            if record["evaluation_token"] != frozen["token"] or record["score"] != text_score(page["reference"], record["prediction"]):
                raise ValueError("Prediction/scoring provenance mismatch")
        coverage[system] = dict(expected=len(pages), completed=len(values),
            missing=sorted(set(expected) - {r["id"] for r in values}))
        rows.extend(values)
    public_rows = [{k: v for k, v in row.items() if k not in {"prediction", "raw", "prompt"}} for row in rows]
    paired = {}
    for collection in ["churro-sleuk", "churro-sleuk-test", "churro-sleuk-train"]:
        selected = [p for p in pages if p["collection"] == "churro-sleuk" and
                    (collection == "churro-sleuk" or collection.endswith("-" + p["source_split"]))]
        expected_ids = {p["id"] for p in selected}
        by_system = {name: {r["id"]: r for r in rows if r["system"] == name and r["id"] in expected_ids}
                     for name in SYSTEMS}
        base = by_system["tesseract-fast"]
        for name in SYSTEMS[1:]:
            other = by_system[name]
            if set(base) != expected_ids or set(other) != expected_ids:
                continue
            pairs = [dict(group=base[key]["group"], baseline=base[key]["score"],
                          toolkit=other[key]["score"]) for key in sorted(expected_ids)]
            paired.setdefault(collection, {})[name] = paired_interval(pairs, replicates=5000, seed=20261018)
    write_json(PUBLIC / "local-results.json", dict(environment=frozen, coverage=coverage,
                summary=summarize(rows), paired=paired, records=public_rows))
    print(json.dumps({"coverage": coverage, "summary": summarize(rows)}, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--freeze", action="store_true")
    group.add_argument("--system", choices=SYSTEMS)
    group.add_argument("--report", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.freeze:
        freeze()
    elif args.report:
        report()
    else:
        run(args.system, args.workers)


if __name__ == "__main__":
    main()

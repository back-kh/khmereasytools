"""Blinded KH-FUNSD execution with new freezes and reused pinned adapters."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import importlib
import json
import os
from pathlib import Path
import signal
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
SYSTEMS = {"cpu": ("tesseract-fast", "khmereasytools-fast"), "surya": ("surya-2",),
           "mlx": ("paddleocr-vl-1.6-4bit", "deepseek-ocr-4bit"),
           "qwen": ("qwen25-vl-3b", "qwen3-vl-2b")}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def adapter(backend):
    name = {"cpu": "evaluate_document_ocr", "surya": "evaluate_document_ocr",
            "mlx": "evaluate_mlx_cuda", "qwen": "evaluate_small_vlm"}[backend]
    return importlib.import_module(name)


def configure(backend, base):
    return base.configure() if backend == "mlx" else base.configure_torch() if backend == "qwen" else None


def identity(data, backend, base, runtime):
    existing = base.identity(data, runtime) if backend in ("mlx", "qwen") else base.identity()
    return dict(backend=backend, reused_adapter=existing,
                files={"evaluate_business_ocr.py": digest(Path(__file__)),
                       "inputs.json": digest(data / "inputs.json"),
                       "protocol.md": digest(data / "protocol.md")},
                reference_freeze_token=read(data / "inputs.json")["source_evaluation_token"],
                expected_pages=30 if backend == "qwen" else 146)


def pages_for(data, backend):
    pages = read(data / "inputs.json")["pages"]
    if len(pages) != 146 or len({p["id"] for p in pages}) != 146:
        raise ValueError("Expected 146 unique page identities")
    if sum(p["qwen_subset"] for p in pages) != 30:
        raise ValueError("Expected frozen matched Qwen subset")
    for page in pages:
        if set(page) != {"id", "image", "image_sha256", "source_sha256", "category",
                         "acquisition_folder", "collection", "group", "source_split", "qwen_subset"}:
            raise ValueError("Unexpected input fields; references must not reach inference")
        if digest(data / page["image"]) != page["image_sha256"]:
            raise ValueError("Input image hash differs")
    return [p for p in pages if p["qwen_subset"]] if backend == "qwen" else pages


def verify_models(data, backend, base):
    if backend in ("mlx", "qwen"):
        base.verify_checkpoints(data)
    elif backend == "surya":
        inventory = read(data / "model-inventory.json")
        item = next(v for v in inventory.values() if v["directory"] == "surya-ocr-2-gguf")
        for row in item["files"]:
            if digest(data / "models" / item["directory"] / row["path"]) != row["sha256"]:
                raise ValueError("Surya checkpoint differs")


def freeze(data, backend, base, runtime):
    path = data / ("frozen-" + backend + ".json")
    if path.exists():
        raise ValueError("Preserve previous frozen execution profile")
    pages_for(data, backend)
    verify_models(data, backend, base)
    value = identity(data, backend, base, runtime)
    value["created_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    value["token"] = hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
    write(path, value)
    print("Frozen", backend, value["token"], flush=True)


def cpu_page(payload):
    data, page, system = payload
    base = adapter("cpu")
    base.DATA = Path(data)
    # The reused transport's scoring helper expects a reference. An empty
    # placeholder keeps actual reference text outside inference; discard score.
    row = base.tess_page((dict(page, reference=""), system))
    row.pop("score")
    return row


def run(data, backend, base, runtime, system):
    frozen = read(data / ("frozen-" + backend + ".json"))
    for key, value in identity(data, backend, base, runtime).items():
        if frozen[key] != value:
            raise ValueError("Frozen execution differs: " + key)
    pages = pages_for(data, backend)
    verify_models(data, backend, base)
    directory = data / "predictions" / frozen["token"] / system
    todo = []
    metadata = {p["id"]: p for p in pages}

    def filename(page_id):
        return directory / (hashlib.sha256(page_id.encode()).hexdigest() + ".json")

    for page in pages:
        path = filename(page["id"])
        if path.exists():
            old = read(path)
            if old["evaluation_token"] != frozen["token"] or old["image_sha256"] != page["image_sha256"]:
                raise ValueError("Cached output provenance differs")
        else:
            todo.append(page)
    complete = len(pages) - len(todo)
    print(system, "remaining", len(todo), "of", len(pages), flush=True)

    def save(row):
        nonlocal complete
        page = metadata[row["id"]]
        row.pop("score", None)
        row.update({key: page[key] for key in ("category", "acquisition_folder", "qwen_subset", "image_sha256")})
        row.update(system=system, evaluation_token=frozen["token"],
                   reference_freeze_token=frozen["reference_freeze_token"])
        if filename(page["id"]).exists():
            raise ValueError("Refusing to overwrite a completed prediction")
        write(filename(page["id"]), row)
        complete += 1
        write(data / ("progress-" + system + ".json"), dict(completed=complete, expected=len(pages),
              token=frozen["token"], updated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))
        print(system, complete, "/", len(pages), page["id"], "seconds", round(row["seconds"], 2),
              "error", row.get("error"), flush=True)

    if backend == "cpu":
        with ProcessPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(cpu_page, (str(data), p, system)) for p in todo]
            for future in as_completed(futures):
                save(future.result())
    elif backend == "surya":
        base.DATA = data
        signal.signal(signal.SIGALRM, base.deadline)
        if todo:
            base.run_surya([dict(p, reference="") for p in todo], save)
    else:
        if not todo:
            return
        if backend == "mlx":
            model, processor, prompt, formatted = base.load(data, system)
            signal.signal(signal.SIGALRM, base.deadline)
        else:
            model, processor = base.load(data, system, runtime)
            signal.signal(signal.SIGALRM, base.timeout)
        for page in todo:
            if backend == "mlx":
                row = base.infer(data / page["image"], model, processor, formatted, runtime)
                row["prompt"] = prompt
            else:
                row = base.infer(data / page["image"], model, processor, runtime)
            row.update(id=page["id"])
            save(row)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--backend", choices=SYSTEMS, required=True)
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--system")
    args = parser.parse_args()
    if not args.freeze and args.system not in SYSTEMS[args.backend]:
        parser.error("Choose a system belonging to this backend")
    if args.freeze and args.system:
        parser.error("Freeze before inference")
    data = args.data_root.resolve()
    base = adapter(args.backend)
    runtime = configure(args.backend, base)
    if args.freeze:
        freeze(data, args.backend, base, runtime)
    else:
        run(data, args.backend, base, runtime, args.system)


if __name__ == "__main__":
    main()

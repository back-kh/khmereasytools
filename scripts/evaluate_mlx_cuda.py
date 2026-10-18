"""Blinded CUDA execution of the pinned MLX OCR recognition profiles.

Uses the same native MLX-VLM load, prompt rendering and generation calls as
the original Mac adapter. No reference text is sent to this inference host.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import time

MODELS = {"paddleocr-vl-1.6-4bit": "mlx-community/PaddleOCR-VL-1.6-4bit",
          "deepseek-ocr-4bit": "mlx-community/DeepSeek-OCR-4bit"}
MAX_TOKENS = 4096
TIMEOUT = 240
SEED = 20261018
MEMORY_LIMIT = 16 * 1024 ** 3


def digest(path):
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def configure():
    visible = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    if not visible.isdigit():
        raise ValueError("Expose exactly one physical CUDA device")
    os.environ["OMP_NUM_THREADS"] = "4"
    os.environ["MLX_ENABLE_TF32"] = "0"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    import torch
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    import mlx.core as mx
    mx.set_default_device(mx.Device(mx.gpu, 0))
    mx.set_memory_limit(MEMORY_LIMIT)
    value = mx.ones((64, 64))
    control = mx.sum(value @ value)
    mx.eval(control)
    if control.item() != 262144.0 or "gpu" not in str(mx.default_device()).lower():
        raise ValueError("CUDA matrix control failed")
    mx.clear_cache()
    return mx


def identity(data, mx):
    names = ["mlx", "mlx-cuda-12", "mlx-vlm", "mlx-audio", "torch",
             "torchvision", "transformers", "Pillow", "numpy",
             "nvidia-cublas-cu12", "nvidia-cufft-cu12", "nvidia-cusolver-cu12",
             "nvidia-cusparse-cu12", "nvidia-cuda-runtime-cu12", "nvidia-cuda-nvrtc-cu12",
             "nvidia-cudnn-cu12", "nvidia-nccl-cu12", "nvidia-nvjitlink-cu12"]
    versions = {name: importlib.metadata.version(name) for name in names}
    gpu = subprocess.check_output(["nvidia-smi", "-i", os.environ["CUDA_VISIBLE_DEVICES"],
        "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"],
        text=True).strip()
    return dict(files={"evaluate_mlx_cuda.py": digest(Path(__file__)),
                       "inputs.json": digest(data / "inputs.json"),
                       "model-inventory.json": digest(data / "model-inventory.json"),
                       "protocol.md": digest(data / "protocol.md"),
                       "framework-inventory.json": digest(data / "framework-inventory.json")},
                source_evaluation_token=read(data / "inputs.json")["source_evaluation_token"],
                python=platform.python_version(), platform=platform.platform(), versions=versions,
                gpu_query=gpu, cuda_visible_devices=os.environ["CUDA_VISIBLE_DEVICES"],
                mlx_default_device=str(mx.default_device()), mlx_memory_limit_bytes=MEMORY_LIMIT,
                mlx_enable_tf32=False, max_tokens=MAX_TOKENS, timeout_seconds=TIMEOUT,
                temperature=0.0, seed=SEED, batch_size=1, cpu_threads=4,
                prompts={"paddleocr-vl-1.6-4bit": "OCR:", "deepseek-ocr-4bit": "Free OCR."})


def verify_checkpoints(data):
    for repository in MODELS.values():
        model = read(data / "model-inventory.json")[repository]
        for item in model["files"]:
            path = data / "models" / model["directory"] / item["path"]
            if path.stat().st_size != item["size"] or digest(path) != item["sha256"]:
                raise ValueError("Pinned checkpoint differs: " + item["path"])


def freeze(data, mx):
    if (data / "frozen.json").exists():
        raise ValueError("Already frozen; retain earlier profiles")
    inputs = read(data / "inputs.json")
    pages = inputs["pages"]
    if len(pages) != 150 or len({p["id"] for p in pages}) != 150:
        raise ValueError("Expected all 150 distinct primary input identities")
    if (sum(p["source_split"] == "test" for p in pages) != 30 or
            sum(p["source_split"] == "train" for p in pages) != 120):
        raise ValueError("Expected 30 official test pages")
    for page in pages:
        if "reference" in page or digest(data / page["image"]) != page["image_sha256"]:
            raise ValueError("Blinded input provenance differs")
    verify_checkpoints(data)
    value = identity(data, mx)
    value["created_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    value["token"] = hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
    write(data / "frozen.json", value)
    print("Frozen CUDA MLX profile", value["token"], flush=True)


def load(data, system):
    from mlx_vlm import load as load_model
    from mlx_vlm.prompt_utils import apply_chat_template
    item = read(data / "model-inventory.json")[MODELS[system]]
    directory = data / "models" / item["directory"]
    model, processor = load_model(str(directory))
    config = read(directory / "config.json")
    prompt = "OCR:" if system.startswith("paddleocr") else "Free OCR."
    formatted = apply_chat_template(processor, config, prompt, num_images=1)
    if system == "deepseek-ocr-4bit" and formatted.count("<image>") != 1:
        raise ValueError("DeepSeek template must contain exactly one image marker")
    return model, processor, prompt, formatted


def deadline(signum, frame):
    raise TimeoutError("Per-page deadline exceeded")


def infer(path, model, processor, formatted, mx):
    from mlx_vlm import generate
    start = time.monotonic()
    started_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    raw, tokens, error, capped = "", 0, None, False
    mx.reset_peak_memory()
    try:
        mx.random.seed(SEED)
        signal.alarm(TIMEOUT)
        output = generate(model, processor, formatted, image=[str(path)],
                          max_tokens=MAX_TOKENS, temperature=0.0, verbose=False)
        raw = output.text
        tokens = output.generation_tokens
        capped = tokens >= MAX_TOKENS or output.finish_reason == "length"
    except Exception as exc:
        error = type(exc).__name__ + ": " + str(exc)[:500]
    finally:
        signal.alarm(0)
    result = dict(raw=raw, generation_tokens=tokens, capped=capped, error=error,
                  started_utc=started_utc,
                  seconds=time.monotonic() - start, peak_allocated_bytes=mx.get_peak_memory(),
                  formatted_prompt_sha256=hashlib.sha256(formatted.encode()).hexdigest())
    mx.clear_cache()
    return result


def run(data, system, mx, smoke=False):
    if not smoke:
        frozen = read(data / "frozen.json")
        for key, value in identity(data, mx).items():
            if frozen[key] != value:
                raise ValueError("Frozen CUDA profile differs: " + key)
    verify_checkpoints(data)
    model, processor, prompt, formatted = load(data, system)
    signal.signal(signal.SIGALRM, deadline)
    if smoke:
        for name in ["english-control", "khob-development"]:
            row = infer(data / "controls" / (name + ".png"), model, processor, formatted, mx)
            row["prompt"] = prompt
            write(data / "setup" / (system + "-" + name + ".json"), row)
            print(system, name, "characters", len(row["raw"]), "error", row["error"], flush=True)
        return
    directory = data / "predictions" / frozen["token"] / system
    for i, page in enumerate(read(data / "inputs.json")["pages"], 1):
        path = directory / (hashlib.sha256(page["id"].encode()).hexdigest() + ".json")
        if path.exists():
            row = read(path)
            if row["evaluation_token"] != frozen["token"] or row["image_sha256"] != page["image_sha256"]:
                raise ValueError("Cached CUDA prediction provenance differs")
            print(system, i, "/ 150 cached", flush=True)
            continue
        if digest(data / page["image"]) != page["image_sha256"]:
            raise ValueError("Input image changed")
        row = infer(data / page["image"], model, processor, formatted, mx)
        row.update(id=page["id"], system=system, collection=page["collection"], group=page["group"],
                   source_split=page["source_split"], image_sha256=page["image_sha256"],
                   source_evaluation_token=frozen["source_evaluation_token"],
                   evaluation_token=frozen["token"], prompt=prompt)
        write(path, row)
        print(system, i, "/ 150", page["id"], "seconds", round(row["seconds"], 2),
              "error", row["error"], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--system", choices=MODELS)
    mode.add_argument("--device-control", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    if args.smoke and not args.system:
        parser.error("Setup images require --system")
    mx = configure()
    if args.device_control:
        print("CUDA MLX matrix control passed", str(mx.default_device()), flush=True)
    elif args.freeze:
        freeze(args.data_root.resolve(), mx)
    elif args.system:
        run(args.data_root.resolve(), args.system, mx, smoke=args.smoke)
    else:
        parser.error("Choose a control, freeze, or system")


if __name__ == "__main__":
    main()

"""Isolated CUDA comparison of two small Qwen VLMs on 30 public test pages.

The inference host receives images and identities, without reference text.
References are joined and scored separately on the original evaluation host.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import signal
import time

MODELS = {"qwen25-vl-3b": "Qwen/Qwen2.5-VL-3B-Instruct",
          "qwen3-vl-2b": "Qwen/Qwen3-VL-2B-Instruct"}
PROMPT = ("Transcribe all visible text in this image exactly as written. Preserve Khmer and Latin "
          "characters, digits and punctuation. Read blocks from top to bottom and tables row by row, "
          "left to right. Do not translate, explain, summarize, correct spelling or invent missing text. "
          "Return only the transcription, without Markdown or formatting labels.")
MAX_TOKENS = 4096
MAX_PIXELS = 1003520
MIN_PIXELS = 112896
TIMEOUT = 240
MEMORY_FRACTION = 0.2
SEED = 20261018


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


def configure_torch():
    os.environ["OMP_NUM_THREADS"] = "4"
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    import torch
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise ValueError("Expose exactly one CUDA device for this isolated research run")
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    torch.cuda.set_per_process_memory_fraction(MEMORY_FRACTION, 0)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.manual_seed(SEED)
    torch.cuda.manual_seed_all(SEED)
    return torch


def identity(data, torch):
    versions = {name: importlib.metadata.version(name) for name in
                ["torch", "torchvision", "transformers", "accelerate", "Pillow", "huggingface-hub", "numpy"]}
    device = torch.cuda.get_device_properties(0)
    return dict(files={"evaluate_small_vlm.py": digest(Path(__file__)),
                       "inputs.json": digest(data / "inputs.json"),
                       "model-inventory.json": digest(data / "model-inventory.json"),
                       "protocol.md": digest(data / "protocol.md")},
                python=platform.python_version(), platform=platform.platform(),
                versions=versions, cuda_runtime=torch.version.cuda,
                gpu=dict(name=device.name, total_memory_bytes=device.total_memory,
                         compute_capability=[device.major, device.minor]),
                cuda_visible_devices=os.environ.get("CUDA_VISIBLE_DEVICES"),
                prompt=PROMPT, max_new_tokens=MAX_TOKENS, max_pixels=MAX_PIXELS,
                min_pixels=MIN_PIXELS, timeout_seconds=TIMEOUT,
                torch_allocator_memory_fraction=MEMORY_FRACTION,
                dtype="bfloat16", attention="sdpa", do_sample=False,
                seed=SEED, batch_size=1)


def verify_checkpoints(data):
    inventory = read(data / "model-inventory.json")
    for repository in MODELS.values():
        model = inventory[repository]
        for item in model["files"]:
            path = data / "models" / model["directory"] / item["path"]
            if path.stat().st_size != item["size"] or digest(path) != item["sha256"]:
                raise ValueError("Pinned checkpoint differs: " + item["path"])


def freeze(data, torch):
    target = data / "frozen.json"
    if target.exists():
        raise ValueError("Already frozen; retain previous runs")
    pages = read(data / "inputs.json")["pages"]
    if len(pages) != 30 or any(p["source_split"] != "test" for p in pages):
        raise ValueError("Expected all 30 official test pages")
    if len({p["id"] for p in pages}) != 30:
        raise ValueError("Duplicate input identity")
    for page in pages:
        if digest(data / page["image"]) != page["image_sha256"]:
            raise ValueError("Input image differs")
        if "reference" in page:
            raise ValueError("Do not transfer references to the inference host")
    verify_checkpoints(data)
    value = identity(data, torch)
    value["created_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    value["token"] = hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
    write(target, value)
    print("Frozen exploratory small-model profile", value["token"], flush=True)


def load(data, system, torch):
    from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration, Qwen3VLForConditionalGeneration
    repository = MODELS[system]
    item = read(data / "model-inventory.json")[repository]
    directory = data / "models" / item["directory"]
    processor = AutoProcessor.from_pretrained(str(directory), local_files_only=True,
                                              trust_remote_code=False)
    image_processor = processor.image_processor
    if hasattr(image_processor, "min_pixels"):
        image_processor.min_pixels = MIN_PIXELS
    if hasattr(image_processor, "max_pixels"):
        image_processor.max_pixels = MAX_PIXELS
    if isinstance(getattr(image_processor, "size", None), dict):
        image_processor.size = {"shortest_edge": MIN_PIXELS, "longest_edge": MAX_PIXELS}
    model_class = Qwen2_5_VLForConditionalGeneration if system == "qwen25-vl-3b" else Qwen3VLForConditionalGeneration
    model = model_class.from_pretrained(str(directory), dtype=torch.bfloat16,
        device_map={"": 0}, attn_implementation="sdpa", local_files_only=True,
        trust_remote_code=False)
    model.eval()
    return model, processor


def timeout(signum, frame):
    raise TimeoutError("Per-page deadline exceeded")


def infer(image_path, model, processor, torch):
    from PIL import Image
    torch.manual_seed(SEED)
    torch.cuda.manual_seed_all(SEED)
    torch.cuda.reset_peak_memory_stats(0)
    begun = time.monotonic()
    raw, error, tokens, grid = "", None, 0, None
    try:
        signal.alarm(TIMEOUT)
        with Image.open(image_path) as source:
            image = source.convert("RGB")
        messages = [{"role": "user", "content": [{"type": "image", "image": image},
                    {"type": "text", "text": PROMPT}]}]
        inputs = processor.apply_chat_template(messages, tokenize=True,
            add_generation_prompt=True, return_dict=True, return_tensors="pt")
        grid = inputs["image_grid_thw"].tolist()
        patch = processor.image_processor.patch_size
        if any(row[1] * row[2] * patch * patch > MAX_PIXELS * 1.1 for row in grid):
            raise ValueError("Native processor exceeded fixed image pixel budget")
        inputs = inputs.to("cuda:0")
        with torch.inference_mode():
            output = model.generate(**inputs, max_new_tokens=MAX_TOKENS,
                do_sample=False, num_beams=1, repetition_penalty=1.0,
                no_repeat_ngram_size=0, use_cache=True)
        generated = output[:, inputs["input_ids"].shape[-1]:]
        tokens = generated.shape[-1]
        raw = processor.batch_decode(generated, skip_special_tokens=True,
                                     clean_up_tokenization_spaces=False)[0]
        torch.cuda.synchronize()
    except Exception as exc:
        error = type(exc).__name__ + ": " + str(exc)[:500]
    finally:
        signal.alarm(0)
    result = dict(raw=raw, generation_tokens=tokens, capped=tokens >= MAX_TOKENS,
                  seconds=time.monotonic() - begun, error=error,
                  image_grid_thw=grid, peak_allocated_bytes=torch.cuda.max_memory_allocated(0))
    torch.cuda.empty_cache()
    return result


def run(data, system, torch, smoke=False):
    if not smoke:
        frozen = read(data / "frozen.json")
        for key, value in identity(data, torch).items():
            if frozen[key] != value:
                raise ValueError("Frozen profile differs: " + key)
    verify_checkpoints(data)
    model, processor = load(data, system, torch)
    signal.signal(signal.SIGALRM, timeout)
    if smoke:
        for name in ["english-control", "khob-development"]:
            record = infer(data / "controls" / (name + ".png"), model, processor, torch)
            write(data / "setup" / (system + "-" + name + ".json"), record)
            print(system, name, "characters", len(record["raw"]), "error", record["error"], flush=True)
        return
    directory = data / "predictions" / frozen["token"] / system
    for i, page in enumerate(read(data / "inputs.json")["pages"], 1):
        path = directory / (hashlib.sha256(page["id"].encode()).hexdigest() + ".json")
        if path.exists():
            old = read(path)
            if old["evaluation_token"] != frozen["token"] or old["image_sha256"] != page["image_sha256"]:
                raise ValueError("Cached output provenance differs")
            print(system, i, "/ 30", "cached", flush=True)
            continue
        if digest(data / page["image"]) != page["image_sha256"]:
            raise ValueError("Input changed")
        record = infer(data / page["image"], model, processor, torch)
        record.update(id=page["id"], system=system, source_split=page["source_split"],
                      group=page["group"], image_sha256=page["image_sha256"],
                      evaluation_token=frozen["token"])
        write(path, record)
        print(system, i, "/ 30", page["id"], "seconds", round(record["seconds"], 2),
              "error", record["error"], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--system", choices=MODELS)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    data = args.data_root.resolve()
    torch = configure_torch()
    if args.freeze:
        if args.system or args.smoke:
            parser.error("Freeze must be separate from inference")
        freeze(data, torch)
    elif args.system:
        run(data, args.system, torch, smoke=args.smoke)
    else:
        parser.error("Choose --freeze or --system")


if __name__ == "__main__":
    main()

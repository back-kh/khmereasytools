"""Execute EXPANDED_OCR_PROTOCOL.md with original KHOB and KhmerST data."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from evaluation_metrics import compact, sha256, text_score
from expanded_ocr_metrics import polygon_bounds, stable_subset, summarize

DATA = ROOT / ".evaluation/expanded_ocr"
PROTOCOL = ROOT / "benchmarks/accuracy/EXPANDED_OCR_PROTOCOL.md"
EXCLUDED_KHOB = {"goc_3", "mef_1", "goc_4", "mef_3", "goc_2"}
MODEL_HASHES = {
    "khm": "47f110575341b322052f3becbefee61a3ecf1ef549352b5d4d33d28afe30d099",
    "eng": "7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2",
}


def load_groups():
    from PIL import Image
    inventory_path = DATA / "khmerst_inventory.json"
    inventory = json.loads(inventory_path.read_text())
    if inventory["revision"] != "ff64017769af17dee93384756019a975489a7fe0" or not inventory["contains_images"]:
        raise ValueError("Fetch the complete pinned KhmerST corpus first")
    files = {row["path"]: row for row in inventory["files"]}
    if len(files) != 1575 or len(inventory["files"]) != 1575:
        raise ValueError("Expected complete, unique KhmerST file inventory")
    annotations, seen, groups, exclusions = {}, set(), [], []
    for name, record in sorted(files.items()):
        if not name.endswith(".json"):
            continue
        path = DATA / "khmerst" / name
        if sha256(path) != record["sha256"]:
            raise ValueError("Annotation hash changed: " + name)
        items = json.loads(path.read_text(encoding="utf-8-sig"))
        for item in items.values():
            filename = item["filename"]
            if Path(filename).name != filename or filename in seen:
                raise ValueError("Unsafe or duplicate scene filename")
            seen.add(filename)
            annotations[filename] = (item, record["sha256"])
    if len(annotations) != 1544:
        raise ValueError("Expected 1544 scene source annotations")
    for filename, (item, annotation_hash) in sorted(annotations.items()):
        name = "scene_img_data/" + filename
        record = files[name]
        path = DATA / "khmerst" / name
        if sha256(path) != record["sha256"]:
            raise ValueError("Scene image changed: " + filename)
        with Image.open(path) as image:
            width, height = image.size
            orientation = image.getexif().get(274, 1)
        if width * height > 40000000 or orientation != 1:
            exclusions.append(dict(source=filename, reason="image_dimensions_or_orientation"))
            continue
        regions = item.get("regions", [])
        regions = list(regions.values()) if isinstance(regions, dict) else regions
        units = []
        for index, region in enumerate(regions):
            identity = filename + "/region-{:04d}".format(index)
            label = region.get("region_attributes", {}).get("Name")
            if not isinstance(label, str) or not compact(label) or label.strip() == "###":
                exclusions.append(dict(source=filename, unit=identity, reason="missing_or_illegible_label"))
                continue
            shape = region.get("shape_attributes", {})
            try:
                points, bounds = polygon_bounds(shape.get("all_points_x"),
                                                shape.get("all_points_y"), width, height)
            except ValueError as exc:
                exclusions.append(dict(source=filename, unit=identity, reason=str(exc)))
                continue
            units.append(dict(id=identity, reference=label, points=points, bounds=bounds,
                              label_sha256=hashlib.sha256(label.encode("utf-8")).hexdigest()))
        if units:
            groups.append(dict(dataset="khmerst", source_id=filename, group=record["sha256"],
                               image="expanded_ocr/khmerst/" + name,
                               image_sha256=record["sha256"], annotation_sha256=annotation_hash,
                               width=width, height=height, psm=7, units=units))
    root = ROOT / ".evaluation/khob/level1/khob-dataset/level-1"
    count = 0
    for path in sorted(root.rglob("*.json")):
        if path.stem in EXCLUDED_KHOB:
            continue
        item = json.loads(path.read_text(encoding="utf-8"))
        image = path.parent / Path(item["imagePath"]).name
        reference = "\n".join(shape["label"].replace("\\t", "\t") for shape in item["shapes"])
        source = path.parent.name + "/" + path.stem
        groups.append(dict(dataset="khob", source_id=source, group=path.stem,
                           image=image.relative_to(ROOT / ".evaluation").as_posix(),
                           image_sha256=sha256(image), annotation_sha256=sha256(path), psm=3,
                           units=[dict(id=source, reference=reference,
                                       label_sha256=hashlib.sha256(reference.encode("utf-8")).hexdigest())]))
        count += 1
    if count != 40:
        raise ValueError("Expected 40 original KHOB comparison images")
    subset = stable_subset([g["source_id"] for g in groups if g["dataset"] == "khmerst"], 128)
    for group in groups:
        group["degrade"] = group["dataset"] == "khob" or group["source_id"] in subset
    return groups, exclusions, inventory


def source_fingerprint(package):
    digest = hashlib.sha256()
    installed = sorted(package.rglob("*.py"))
    actual_names = {"khmereasytools/" + path.relative_to(package).as_posix() for path in installed}
    expected_names = {name for name in subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", "b062be0", "khmereasytools"],
        cwd=str(ROOT)).decode().splitlines() if name.endswith(".py")}
    if actual_names != expected_names:
        raise ValueError("Installed runtime source file set differs from b062be0")
    for path in installed:
        relative = "khmereasytools/" + path.relative_to(package).as_posix()
        expected = subprocess.check_output(["git", "show", "b062be0:" + relative], cwd=str(ROOT))
        actual = path.read_bytes()
        if actual != expected:
            raise ValueError("Installed runtime differs from b062be0: " + relative)
        digest.update(relative.encode("utf-8")); digest.update(actual)
    return digest.hexdigest()


def degrade(image):
    from PIL import Image
    width, height = max(2, image.width // 2), max(2, image.height // 2)
    reduced = image.resize((width, height), getattr(Image, "Resampling", Image).LANCZOS)
    data = io.BytesIO()
    reduced.save(data, format="JPEG", quality=40, subsampling=2)
    reduced.close()
    data.seek(0)
    with Image.open(data) as decoded:
        return decoded.convert("RGB")


def crop_region(image, unit):
    from PIL import Image, ImageDraw, ImageOps
    x0, y0, x1, y1 = unit["bounds"]
    crop = image.crop((x0, y0, x1, y1))
    mask = Image.new("L", crop.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.polygon([(x - x0, y - y0) for x, y in unit["points"]], fill=255)
    white = Image.new("RGB", crop.size, "white")
    white.paste(crop, mask=mask)
    padded = ImageOps.expand(white, border=2, fill="white")
    crop.close(); mask.close(); white.close()
    return padded


def run_group(payload):
    group, token, model_dir = payload
    os.environ["OMP_THREAD_LIMIT"] = "1"
    os.environ["TESSDATA_PREFIX"] = model_dir
    from PIL import Image, ImageOps
    import pytesseract
    import khmereasytools as ket
    image_path = ROOT / ".evaluation" / group["image"]
    if sha256(image_path) != group["image_sha256"]:
        raise ValueError("Image changed after preparation")
    with Image.open(image_path) as original:
        source = (ImageOps.exif_transpose(original) if group["dataset"] == "khob" else original).convert("RGB")
    rows, predictions = [], []
    with tempfile.TemporaryDirectory(prefix="ket-expanded-ocr-") as temporary:
        target = Path(temporary) / "input.png"
        for unit in group["units"]:
            prepared = source.copy() if group["dataset"] == "khob" else crop_region(source, unit)
            variants = [("clean", prepared)]
            if group["degrade"]:
                variants.append(("half_jpeg40", degrade(prepared)))
            for variant, page in variants:
                page.info.clear()
                page.save(target, format="PNG")
                row = dict(id=unit["id"], dataset=group["dataset"], variant=variant,
                           source_id=group["source_id"], group=group["group"],
                           image_sha256=group["image_sha256"],
                           annotation_sha256=group["annotation_sha256"],
                           label_sha256=unit["label_sha256"], input_sha256=sha256(target),
                           input_width=page.width, input_height=page.height, psm=group["psm"])
                text_outputs = {}
                order = ["baseline", "toolkit"]
                if hashlib.sha256((unit["id"] + variant).encode()).digest()[0] % 2:
                    order.reverse()
                for system in order:
                    started, failed, failure_kind = time.perf_counter(), False, None
                    try:
                        if system == "baseline":
                            text = pytesseract.image_to_string(
                                str(target), lang="khm+eng", config="--psm {}".format(group["psm"]), timeout=60)
                        else:
                            text = ket.khocr_layout(str(target), lang="khm+eng", psm=group["psm"],
                                                    segment=False, preprocess="auto", min_confidence=0,
                                                    reading_order="engine", timeout=60).text
                    except Exception as exc:
                        text, failed, failure_kind = "", True, type(exc).__name__
                    row[system] = dict(text_score(unit["reference"], text),
                                       seconds=time.perf_counter() - started,
                                       failed=failed, failure_kind=failure_kind)
                    text_outputs[system] = text
                rows.append(row)
                predictions.append(dict(id=unit["id"], variant=variant,
                                        reference=unit["reference"], **text_outputs))
                if variant != "clean":
                    page.close()
            prepared.close()
    source.close()
    return dict(token=token, rows=rows, predictions=predictions)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--tessdata-dir", type=Path,
                        default=ROOT / ".evaluation/ocr-target/tessdata-mixed")
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "benchmarks/accuracy/expanded-ocr")
    args = parser.parse_args()
    if args.workers != 4:
        parser.error("The frozen experiment uses exactly four workers")
    groups, exclusions, inventory = load_groups()
    manifest = dict(groups=groups, exclusions=exclusions, protocol_sha256=sha256(PROTOCOL))
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "prepared.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print("Prepared", len(groups), "source images;", sum(len(g["units"]) for g in groups),
          "clean units;", len(exclusions), "exclusions", flush=True)
    if args.prepare_only:
        print(Counter(row["reason"] for row in exclusions), flush=True)
        return
    if not sys.flags.isolated or args.wheel is None:
        parser.error("Run the installed-wheel evaluation with python -I and --wheel")
    for language, expected in MODEL_HASHES.items():
        if sha256(args.tessdata_dir / (language + ".traineddata")) != expected:
            raise ValueError("Fixed model hash changed: " + language)
    os.environ["OMP_THREAD_LIMIT"] = "1"
    os.environ["TESSDATA_PREFIX"] = str(args.tessdata_dir.resolve())
    import khmereasytools as ket
    import pytesseract
    package = Path(ket.__file__).resolve().parent
    if Path(sys.prefix).resolve() not in package.parents:
        raise ValueError("Expected toolkit installed in the active venv")
    languages = set(pytesseract.get_languages())
    if not {"khm", "eng"} <= languages:
        raise ValueError("Both pinned OCR languages must be available")
    metadata = dict(runtime_revision="b062be07447f7b9f1bf57f97aab7098d04db165b",
                    runtime_sources_sha256=source_fingerprint(package),
                    installed_package_path=str(package), wheel_sha256=sha256(args.wheel),
                    protocol_sha256=sha256(PROTOCOL), script_sha256=sha256(__file__),
                    metrics_sha256=sha256(ROOT / "scripts/expanded_ocr_metrics.py"),
                    common_metrics_sha256=sha256(ROOT / "scripts/evaluation_metrics.py"),
                    manifest_sha256=sha256(DATA / "prepared.json"), model_sha256=MODEL_HASHES,
                    language="khm+eng", python=platform.python_version(), platform=platform.platform(),
                    tesseract=str(pytesseract.get_tesseract_version()).splitlines()[0], workers=args.workers,
                    omp_thread_limit=1,
                    dependencies={n: importlib.metadata.version(n) for n in ["Pillow", "pytesseract", "rapidfuzz"]})
    token = hashlib.sha256(json.dumps(metadata, sort_keys=True).encode()).hexdigest()
    cache = DATA / "predictions" / token
    cache.mkdir(parents=True, exist_ok=True)
    completed, rows, tasks = 0, [], []
    for group in groups:
        key = hashlib.sha256((group["dataset"] + "/" + group["source_id"]).encode()).hexdigest()
        path = cache / (key + ".json")
        if path.is_file():
            stored = json.loads(path.read_text())
            if stored.get("token") != token:
                raise ValueError("Stale experiment cache")
            rows.extend(stored["rows"]); completed += 1
        else:
            tasks.append((group, path))
    started = time.monotonic()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run_group, (group, token, str(args.tessdata_dir.resolve()))): path
                   for group, path in tasks}
        for future in as_completed(futures):
            result = future.result()
            path = futures[future]
            temporary = path.with_suffix(".partial")
            temporary.write_text(json.dumps(result, ensure_ascii=False) + "\n")
            temporary.replace(path)
            rows.extend(result["rows"]); completed += 1
            if completed % 20 == 0 or completed == len(groups):
                print("Scored {}/{} images; {} units; {:.1f}s".format(
                    completed, len(groups), len(rows), time.monotonic() - started), flush=True)
    rows.sort(key=lambda row: (row["dataset"], row["variant"], row["id"]))
    tracks = {dataset + "_" + variant: summarize(
        [r for r in rows if r["dataset"] == dataset and r["variant"] == variant])
        for dataset in ["khob", "khmerst"] for variant in ["clean", "half_jpeg40"]}
    by_acquisition = {task: summarize([r for r in rows if r["dataset"] == "khob" and
                                     r["variant"] == "clean" and r["source_id"].startswith(task + "/")])
                      for task in ["task-1", "task-2", "task-3", "task-4"]}
    public = dict(metadata=metadata, tracks=tracks, khob_acquisitions=by_acquisition,
                  exclusions=exclusions, exclusion_counts=dict(Counter(r["reason"] for r in exclusions)),
                  per_unit=rows, wall_seconds=time.monotonic() - started,
                  scope="KhmerST gold-polygon recognition; KHOB full-page OCR; synthetic variants are dependent")
    args.output.mkdir(parents=True, exist_ok=True)
    target = args.output / "local-paired.json"
    target.write_text(json.dumps(public, indent=2) + "\n")
    for name, value in tracks.items():
        print(name, json.dumps({"units": value["units"], "images": value["source_images"],
                               "baseline_cer": value["baseline"]["compact_codepoint_cer"],
                               "toolkit_cer": value["toolkit"]["compact_codepoint_cer"],
                               "paired": value["paired"]}), flush=True)
    print("Saved", target, flush=True)


if __name__ == "__main__":
    main()

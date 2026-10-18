"""Fetch original, pinned KhmerST research data into ignored .evaluation only."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.utils import parsedate_to_datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import threading
import time
from urllib.parse import quote, urlencode
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PROJECT = 62344518
REVISION = "ff64017769af17dee93384756019a975489a7fe0"
API = "https://gitlab.com/api/v4/projects/{}/repository/".format(PROJECT)
DATA = ROOT / ".evaluation/expanded_ocr"
COOLDOWN_LOCK = threading.Lock()
COOLDOWN_UNTIL = 0.0


def read_url(url, limit=16000000):
    global COOLDOWN_UNTIL
    for attempt in range(4):
        while True:
            with COOLDOWN_LOCK:
                delay = COOLDOWN_UNTIL - time.time()
            if delay <= 0:
                break
            time.sleep(min(delay, 30))
        try:
            with urlopen(Request(url, headers={"User-Agent": "KhmerEasyTools-research-evaluation"}),
                         timeout=60) as response:
                data = response.read(limit + 1)
            if len(data) > limit:
                raise ValueError("Download exceeds byte bound")
            return data
        except Exception as exc:
            delay = 2 ** attempt
            if isinstance(exc, HTTPError):
                if exc.code not in {408, 429, 500, 502, 503, 504}:
                    raise
                retry_after = exc.headers.get("Retry-After")
                if retry_after:
                    try:
                        delay = max(delay, float(retry_after))
                    except ValueError:
                        delay = max(delay, parsedate_to_datetime(retry_after).timestamp() - time.time())
                if exc.code == 429:
                    with COOLDOWN_LOCK:
                        COOLDOWN_UNTIL = max(COOLDOWN_UNTIL, time.time() + delay)
                    print("Rate limited; pausing all new requests for {:.0f}s".format(delay), flush=True)
            if attempt == 3:
                raise
            time.sleep(delay)


def tree(path):
    result, page = [], 1
    while True:
        params = urlencode(dict(path=path, ref=REVISION, per_page=100, page=page))
        rows = json.loads(read_url(API + "tree?" + params))
        if not isinstance(rows, list):
            raise ValueError("Unexpected repository tree")
        result.extend(rows)
        if len(rows) < 100:
            return result
        page += 1


def blob_hash(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def fetch(row):
    parts = PurePosixPath(row["path"]).parts
    if (len(parts) != 2 or parts[0] not in {"scene_img_data", "scene_json_data"}
            or any(c in row["path"] for c in ("\\", ":", "\0"))
            or parts[1] in {".", ".."}
            or len(row["id"]) != 40
            or any(c not in "0123456789abcdef" for c in row["id"])):
        raise ValueError("Unsafe dataset member")
    path = DATA / "khmerst" / row["path"]
    if path.is_file():
        data = path.read_bytes()
        if blob_hash(data) == row["id"]:
            return dict(path=row["path"], bytes=len(data), git_blob=row["id"],
                        sha256=hashlib.sha256(data).hexdigest())
    url = API + "files/" + quote(row["path"], safe="") + "/raw?ref=" + REVISION
    data = read_url(url)
    if blob_hash(data) != row["id"]:
        raise ValueError("Git blob mismatch for " + row["path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".partial")
    temp.write_bytes(data)
    temp.replace(path)
    return dict(path=row["path"], bytes=len(data), git_blob=row["id"],
                sha256=hashlib.sha256(data).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", action="store_true", help="Also fetch all 1544 original images")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.workers <= 12:
        parser.error("workers must be 1..12")
    DATA.mkdir(parents=True, exist_ok=True)
    catalog_path = DATA / "khmerst_catalog.json"
    if catalog_path.is_file():
        catalog = json.loads(catalog_path.read_text())
        if catalog.get("revision") != REVISION:
            raise ValueError("Catalog revision changed")
    else:
        image_rows, json_rows = tree("scene_img_data"), tree("scene_json_data")
        image_rows = [row for row in image_rows if row["type"] == "blob"]
        json_rows = [row for row in json_rows if row["path"].endswith(".json")]
        if len(image_rows) != 1544 or len(json_rows) != 31:
            raise ValueError("Pinned dataset member counts differ")
        catalog = dict(project=PROJECT, revision=REVISION,
                       images=sorted(image_rows, key=lambda r: r["path"]),
                       annotations=sorted(json_rows, key=lambda r: r["path"]))
        catalog_path.write_text(json.dumps(catalog, indent=2) + "\n")
    rows = catalog["annotations"] + (catalog["images"] if args.images else [])
    records, failures, byte_count, started = [], [], 0, time.monotonic()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(fetch, row): row["path"] for row in rows}
        for completed, future in enumerate(as_completed(futures), 1):
            try:
                record = future.result()
                records.append(record)
                byte_count += record["bytes"]
            except Exception as exc:
                failures.append(dict(path=futures[future], error=type(exc).__name__, detail=str(exc)[:200]))
                print("Download failed:", futures[future], type(exc).__name__, str(exc)[:150], flush=True)
            if completed % 50 == 0 or completed == len(rows):
                print("Verified {}/{} files, {:.1f} MiB, {:.1f}s".format(
                    completed, len(rows), byte_count / 2 ** 20, time.monotonic() - started), flush=True)
    if failures:
        (DATA / "download_failures.json").write_text(json.dumps(failures, indent=2) + "\n")
        raise RuntimeError("{} downloads failed; rerun to reuse verified files".format(len(failures)))
    inventory = dict(project=PROJECT, revision=REVISION, contains_images=args.images,
                     files=sorted(records, key=lambda r: r["path"]))
    target = DATA / ("khmerst_inventory.json" if args.images else "khmerst_annotations_inventory.json")
    target.write_text(json.dumps(inventory, indent=2) + "\n")
    print("Saved", target, flush=True)


if __name__ == "__main__":
    main()

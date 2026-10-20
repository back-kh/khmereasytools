"""Fetch a fixed research-only Khmer page evaluation; never a runtime dependency.

Images and transcripts remain in ignored .evaluation. Public manifests contain
identities, hashes, acquisition details and counts, without redistributing data.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import unicodedata
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / ".evaluation/full_document_ocr"
REVISION = "cbeaba69179d5de122fbbc9e97b2a7d97942f688"
DATASET = "stanford-oval/churro-dataset"
SEED = "khmereasytools-document-ocr-20261018/"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def compact(text):
    return "".join(c for c in unicodedata.normalize("NFC", text)
                   if not c.isspace() and c != "\u200b")


def session():
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    client = requests.Session()
    client.headers["User-Agent"] = (
        "KhmerEasyTools-Research/0.5 (https://github.com/back-kh/khmereasytools)")
    client.mount("https://", HTTPAdapter(max_retries=Retry(
        total=4, backoff_factor=1, status_forcelist=[429, 500, 502, 503])))
    return client


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def get_json(client, url, params=None):
    response = client.get(url, params=params, timeout=40)
    response.raise_for_status()
    return response.json()


def cache_rows(split, offset):
    path = DATA / ("churro-{}-rows-{}.json".format(split, offset))
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    value = get_json(session(), "https://datasets-server.huggingface.co/rows", {
        "dataset": DATASET, "config": "default", "split": split,
        "offset": offset, "length": 100})
    write_json(path, value)
    return value


def manuscript_group(example_id):
    """Conservative filename groups, not verified independent book identities."""
    stem = example_id.split("/", 1)[1]
    parts = re.sub(r"^\d+_", "", stem).split("_")
    if parts[:2] in [["pp", "ttp"], ["kandal", "tekvil"]]:
        return "sleuk/" + "_".join(parts[:3])
    return "sleuk/" + "_".join(parts[:2])


def source_candidates():
    client = session()
    metadata = get_json(client, "https://huggingface.co/api/datasets/" + DATASET)
    if metadata["sha"] != REVISION:
        raise ValueError("Dataset main changed; recover the pinned revision before fetching")
    jobs = [("train", n) for n in range(96400, 97100, 100)] + [("dev", 1100), ("test", 1100)]
    all_rows = []
    for split, offset in jobs:
        for entry in cache_rows(split, offset)["rows"]:
            row = entry["row"]
            if row["main_language"] != "Khmer":
                continue
            if row["dataset_id"] != "sleuk" or not row["example_id"].startswith("sleuk/"):
                raise ValueError("Unexpected Khmer source")
            if entry.get("truncated_cells"):
                raise ValueError("Viewer truncated a source record")
            if not compact(row["original_transcription"]):
                raise ValueError("Empty source reference")
            src = row["image"]["src"]
            if "/--/" + REVISION + "/--/" not in src:
                raise ValueError("Viewer image revision differs from pinned dataset")
            all_rows.append(dict(split=split, row_idx=entry["row_idx"], row=row))
    counts = {split: sum(x["split"] == split for x in all_rows) for split in ["train", "dev", "test"]}
    if counts != {"train": 562, "dev": 30, "test": 30}:
        raise ValueError("Incomplete Khmer inventory: " + str(counts))
    if len({x["row"]["example_id"] for x in all_rows}) != 622:
        raise ValueError("Duplicate Khmer source identities")
    write_json(DATA / "churro-khmer-candidates.json", all_rows)
    selected = [x for x in all_rows if x["split"] == "test"]
    train = [x for x in all_rows if x["split"] == "train"]
    train.sort(key=lambda x: digest((SEED + x["row"]["example_id"]).encode("utf-8")))
    return sorted(selected + train[:120], key=lambda x: x["row"]["example_id"])


def fetch_churro(entry):
    from PIL import Image, ImageOps
    row = entry["row"]
    key = row["example_id"].split("/", 1)[1]
    raw_path = DATA / "sources/churro" / (key + ".jpg")
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    if not raw_path.exists():
        response = session().get(row["image"]["src"], timeout=60)
        response.raise_for_status()
        if len(response.content) > 40000000:
            raise ValueError("Oversized source image")
        raw_path.write_bytes(response.content)
    with Image.open(raw_path) as original:
        image = ImageOps.exif_transpose(original).convert("RGB")
    if image.size != (row["image"]["width"], row["image"]["height"]):
        raise ValueError("Image dimensions differ from metadata")
    if image.width * image.height > 80000000:
        raise ValueError("Source image pixel bound exceeded")
    target = DATA / "images" / ("churro-" + key + ".png")
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, format="PNG")
    reference = row["original_transcription"]
    return dict(id=row["example_id"], collection="churro-sleuk", source_split=entry["split"],
                group=manuscript_group(row["example_id"]), row_idx=entry["row_idx"],
                reference=reference, reference_sha256=digest(reference.encode("utf-8")),
                source_sha256=digest(raw_path.read_bytes()), source_revision=REVISION,
                image=target.relative_to(DATA).as_posix(), image_sha256=digest(target.read_bytes()),
                width=image.width, height=image.height,
                source_url="https://huggingface.co/datasets/" + DATASET + "/tree/" + REVISION,
                acquisition="HF viewer JPEG from pinned embedded page; RGB PNG conversion",
                reference_provenance="Released original_transcription; no generated XML metadata")


def fetch_wikisource():
    """Use only community-proofread pages; pin revisions and original PDF hashes."""
    from bs4 import BeautifulSoup
    import pypdfium2 as pdfium
    client = session()
    api = "https://wikisource.org/w/api.php"
    params = dict(action="query", format="json", list="allpages", apnamespace=104,
                  aplimit=500, apfrom="ក")
    pages = []
    while True:
        response = get_json(client, api, params)
        batch = response["query"]["allpages"]
        pages.extend(x for x in batch if any("\u1780" <= c <= "\u17ff" for c in x["title"]))
        if "continue" not in response or not any("\u1780" <= c <= "\u17ff" for c in batch[-1]["title"]):
            break
        params.update(response["continue"])
    candidates = []
    for start in range(0, len(pages), 20):
        response = get_json(client, api, dict(action="query", format="json",
            pageids="|".join(str(p["pageid"]) for p in pages[start:start + 20]),
            prop="revisions", rvprop="ids|content", rvslots="main"))
        for item in response["query"]["pages"].values():
            rev = item["revisions"][0]
            text = rev["slots"]["main"]["*"]
            level = re.search(r'<pagequality level="([34])"', text)
            if level:
                candidates.append(dict(title=item["title"], pageid=item["pageid"],
                                       revid=rev["revid"], quality=int(level.group(1))))
    write_json(DATA / "wiki-proofread-candidates.json", candidates)
    result = []
    files = {}
    for item in sorted(candidates, key=lambda x: x["pageid"]):
        title = item["title"]
        filename, page_number = title[5:].rsplit("/", 1)
        response = get_json(client, api, dict(action="parse", format="json", oldid=item["revid"],
                                            prop="text|revid|parsewarnings"))
        if response["parse"]["revid"] != item["revid"]:
            raise ValueError("Wikisource reference revision mismatch")
        write_json(DATA / "sources/wiki" / (str(item["pageid"]) + ".json"), response)
        soup = BeautifulSoup(response["parse"]["text"]["*"], "html.parser")
        for el in soup.select("style,script,link,.prp-page-qualityheader,.mw-editsection"):
            el.decompose()
        # Root output includes printed header/footer as well as the page body.
        reference = soup.get_text("\n", strip=True)
        if not compact(reference):
            raise ValueError("Empty proofread page")
        if filename not in files:
            response = get_json(client, api, dict(action="query", format="json", titles="File:" + filename,
                                                prop="imageinfo", iiprop="url|size|sha1|extmetadata"))
            info = next(iter(response["query"]["pages"].values()))["imageinfo"][0]
            raw = client.get(info["url"], timeout=60)
            raw.raise_for_status()
            if hashlib.sha1(raw.content).hexdigest() != info["sha1"]:
                raise ValueError("Original PDF SHA-1 differs from Wikimedia metadata")
            source = DATA / "sources/wiki" / (digest(filename.encode("utf-8"))[:16] + ".pdf")
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(raw.content)
            files[filename] = (info, source)
        info, source = files[filename]
        pdf = pdfium.PdfDocument(source)
        page = pdf[int(page_number) - 1]
        bitmap = page.render(scale=300 / 72)
        image = bitmap.to_pil().convert("RGB")
        target = DATA / "images" / ("wiki-" + str(item["pageid"]) + ".png")
        target.parent.mkdir(parents=True, exist_ok=True)
        image.save(target, format="PNG")
        result.append(dict(item, id="wikisource/" + str(item["pageid"]), collection="wikisource-printed",
            group="wikisource/" + filename, source_split="community-proofread",
            reference=reference, reference_sha256=digest(reference.encode("utf-8")),
            image=target.relative_to(DATA).as_posix(), image_sha256=digest(target.read_bytes()),
            width=image.width, height=image.height, source_sha256=digest(source.read_bytes()),
            source_sha1=info["sha1"], source_url="https://wikisource.org/w/index.php?oldid=" + str(item["revid"]),
            file_description_url=info["descriptionurl"], source_pdf=source.relative_to(DATA).as_posix(),
            source_pdf_page=int(page_number), acquisition="Original PDF rendered at 300 dpi with PDFium",
            reference_provenance="Community proofread level {}; rendered revision text".format(item["quality"])))
        bitmap.close(); page.close(); pdf.close()
    write_json(DATA / "wiki-file-metadata.json", {name: info for name, (info, _) in files.items()})
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--with-wikisource", action="store_true")
    args = parser.parse_args()
    DATA.mkdir(parents=True, exist_ok=True)
    candidates = source_candidates()
    print("Selected 150 pages: 30 official test and 120 source train pages", flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        rows = list(executor.map(fetch_churro, candidates))
    excluded = []
    if args.with_wikisource:
        # Proofread status alone does not certify that every printed header,
        # footer and stamp was transcribed. A pre-inference visual audit found
        # omitted page-header text and literal markup in page 107688. Exclude
        # this entire small collection from CER rather than selecting pages
        # according to any engine's predictions.
        excluded = fetch_wikisource()
        for item in excluded:
            item["exclusion_reason"] = "Collection lacks consistently complete full-page OCR references"
    if len({row["image_sha256"] for row in rows}) != len(rows):
        raise ValueError("Byte-identical page images; resolve duplicates before inference")
    if get_json(session(), "https://huggingface.co/api/datasets/" + DATASET)["sha"] != REVISION:
        raise ValueError("Dataset revision changed during acquisition")
    write_json(DATA / "prepared.json", dict(dataset_revision=REVISION, seed=SEED, pages=rows,
                                            excluded_pages=excluded))
    public = {"dataset_revision": REVISION, "seed": SEED,
              "pages": [{k: v for k, v in row.items() if k != "reference"} for row in rows],
              "excluded_pages": [{k: v for k, v in row.items() if k != "reference"} for row in excluded]}
    write_json(ROOT / "benchmarks/accuracy/document-ocr/source-inventory.json", public)
    print("Prepared", len(rows), "unique images; groups", len({x["group"] for x in rows}), flush=True)


if __name__ == "__main__":
    main()

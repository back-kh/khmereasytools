"""Reproducible optional accuracy checks; see benchmarks/accuracy/PROTOCOL.md."""
import argparse
import collections
import importlib.metadata
import json
import math
import platform
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation_metrics import (aggregate_text, compact, fscore, matched_boxes,
                                provenance, sha256, text_score)
import khmereasytools as ket

NOVA = re.compile(r"([^\s\[\]]+)(\[)?|\]([^\s\[\]]+)")


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def metadata():
    return dict(provenance(), python=platform.python_version(), platform=platform.platform(),
                package_version=ket.__version__, protocol_sha256=sha256(
                    ROOT / "benchmarks/accuracy/PROTOCOL.md"))


def alt_rows(data):
    directory = data / "alt"
    test_ids = {line.split("\t")[0].split(".")[1] for line in
                (directory / "URL-test.txt").read_text(encoding="utf-8").splitlines()}
    tags = dict(line.split("\t", 1) for line in
                (directory / "data_km.km-tag.nova").read_text(encoding="utf-8").splitlines())
    rows = []
    for line in (directory / "data_km.km-tok.nova").read_text(encoding="utf-8").splitlines():
        identifier, content = line.split("\t", 1)
        if identifier.split(".")[1] not in test_ids:
            continue
        words = content.split()
        leaves = [m.group(1).rstrip("-") for m in NOVA.finditer(tags[identifier])
                  if m.group(1) and not m.group(2)]
        if len(words) != len(leaves):
            raise ValueError("NOVA leaf/token mismatch: " + identifier)
        pairs = [(compact(word), tag) for word, tag in zip(words, leaves) if compact(word)]
        rows.append((identifier, pairs))
    if len(rows) != 1018 or len({row[0].split(".")[1] for row in rows}) != 97:
        raise ValueError("ALT split membership differs from frozen protocol")
    return rows


def pair_spans(pairs):
    position, spans = 0, set()
    for word, label in pairs:
        word = compact(word)
        if word:
            spans.add((position, position + len(word), label))
            position += len(word)
    return spans


def evaluate_pos(data, output):
    import khmernltk
    from khmernltk.pos_tag.features import create_word_features
    from khmernltk.pos_tag import model_path
    # Load the actual installed CRF once; no substitute/model training.
    khmernltk.pos_tag("ខ្ញុំទៅសាលា។")
    from khmernltk.pos_tag import crf_model
    rows = alt_rows(data)
    inventory = set(crf_model.classes_)
    totals, predictions, by_tag = {}, [], collections.defaultdict(collections.Counter)
    oracle_correct = majority_correct = gold_count = 0
    started = time.perf_counter()
    methods = {"public_khpos": ket.khpos, "backend_raw": khmernltk.pos_tag}
    for identifier, gold in rows:
        text = "".join(word for word, _ in gold)
        gold_spans = pair_spans(gold)
        words, labels = zip(*gold)
        if not set(labels) <= inventory:
            raise ValueError("Gold labels outside backend inventory")
        oracle = crf_model.predict([create_word_features(list(words))])[0]
        oracle_correct += sum(a == b for a, b in zip(labels, oracle))
        majority_correct += sum(label == "n" for label in labels)
        gold_count += len(gold)
        for label, predicted in zip(labels, oracle):
            by_tag[label]["gold"] += 1
            by_tag[label]["correct"] += label == predicted
        item = {"id": identifier, "gold": gold, "predictions": {}}
        for name, method in methods.items():
            stats = totals.setdefault(name, collections.Counter())
            pairs = method(text)
            item["predictions"][name] = pairs
            span_set = pair_spans(pairs)
            aligned = compact("".join(word for word, _ in pairs)) == text
            stats["alignment_failures"] += not aligned
            stats["discarded_whitespace_pairs"] += sum(not compact(word) for word, _ in pairs)
            stats["predicted"] += len(span_set)
            stats["gold"] += len(gold_spans)
            if aligned:
                stats["tagged_correct"] += len(span_set & gold_spans)
                stats["token_correct"] += len({s[:2] for s in span_set} &
                                               {s[:2] for s in gold_spans})
                stats["exact_tagged_sentences"] += span_set == gold_spans
        predictions.append(item)
    result = dict(metadata(), dataset="NICT Khmer ALT 2018-11-01, standard article test",
                  corpus_sha256=sha256(data / "alt/km-nova-181101.zip"),
                  split_sha256=sha256(data / "alt/URL-test.txt"), sentences=len(rows),
                  gold_tokens=gold_count, backend_version=importlib.metadata.version("khmer-nltk"),
                  model_sha256=sha256(model_path), labels=sorted(inventory),
                  training_overlap="Possible: upstream trained on ALT; membership unavailable.",
                  oracle_gold_token_accuracy=oracle_correct / gold_count,
                  oracle_correct=oracle_correct,
                  majority_noun_oracle_accuracy=majority_correct / gold_count,
                  oracle_by_tag={key: dict(value) for key, value in sorted(by_tag.items())},
                  seconds=time.perf_counter() - started, methods={})
    for name, stats in totals.items():
        result["methods"][name] = dict(
            stats, token_spans=fscore(stats["token_correct"], stats["predicted"], stats["gold"]),
            tagged_spans=fscore(stats["tagged_correct"], stats["predicted"], stats["gold"]))
    write(data / "accuracy_predictions/pos.json", predictions)
    write(output / "pos.json", result)
    print("POS", json.dumps(result["methods"]), flush=True)


def span_totals(text, expected):
    gold, position = set(), 0
    for piece in expected:
        start = text.index(piece, position)
        gold.add((start, start + len(piece)))
        position = start + len(piece)
    predicted = {(span.start, span.end) for span in ket.khsentences(text, with_spans=True)}
    # Ignore the article-end boundary: every system gets it for free.
    end = len(text.rstrip())
    gold_ends = {b for _, b in gold if b != end}
    pred_ends = {b for _, b in predicted if b != end}
    return dict(
        exact=gold == predicted,
        spans=(len(gold & predicted), len(predicted), len(gold)),
        boundaries=(len(gold_ends & pred_ends), len(pred_ends), len(gold_ends)))


def combine_spans(items):
    result = dict(cases=len(items), exact_cases=sum(item["exact"] for item in items))
    for name in ("spans", "boundaries"):
        result[name] = fscore(*(sum(item[name][i] for item in items) for i in range(3)))
    return result


def evaluate_sentences(data, output):
    articles = collections.OrderedDict()
    for identifier, pairs in alt_rows(data):
        articles.setdefault(identifier.split(".")[1], []).append(
            "".join(word for word, _ in pairs))
    details = []
    for identifier, pieces in articles.items():
        text = " ".join(pieces)
        details.append(dict(id=identifier, **span_totals(text, pieces)))
    result = dict(metadata(), dataset="ALT standard test article reconstruction",
                  corpus_sha256=sha256(data / "alt/km-nova-181101.zip"),
                  split_sha256=sha256(data / "alt/URL-test.txt"), sentences=1018,
                  **combine_spans(details))
    result["imperfect_article_ids"] = [item["id"] for item in details if not item["exact"]]
    write(output / "sentences_alt.json", result)
    print("Sentences ALT", json.dumps(result), flush=True)


def evaluate_pos_proxy(data, output):
    import khmernltk
    from khmernltk.pos_tag.features import create_word_features
    from khmernltk.pos_tag import model_path
    khmernltk.pos_tag("ខ្ញុំទៅសាលា។")
    from khmernltk.pos_tag import crf_model
    mapping = {"NN": "n", "PN": "n", "VB": "v", "KAN": "."}
    word_lines = (data / "OPEN-TEST.word").read_text(encoding="utf-8-sig").splitlines()
    tag_lines = (data / "OPEN-TEST.tag").read_text(encoding="utf-8-sig").splitlines()
    if len(word_lines) != 1000 or len(tag_lines) != 1000:
        raise ValueError("khPOS sentence count changed")
    totals, per_tag, predictions = collections.Counter(), {}, []
    for index, (word_line, tag_line) in enumerate(zip(word_lines, tag_lines)):
        words = [compact(word.replace("\\~", "").replace("\\_", "")
                         .replace("_", "").replace("~", "")) for word in word_line.split()]
        tags = tag_line.split()
        if len(words) != len(tags) or not all(words):
            raise ValueError("khPOS word/tag mismatch at " + str(index))
        oracle = [str(tag) for tag in crf_model.predict([create_word_features(words)])[0]]
        text = "".join(words)
        predicted = ket.khpos(text)
        aligned = compact("".join(word for word, _ in predicted)) == text
        spans = pair_spans(predicted)
        boundaries = {span[:2] for span in spans}
        totals["alignment_failures"] += not aligned
        totals["all_gold_tokens"] += len(words)
        position = 0
        for word, tag, oracle_tag in zip(words, tags, oracle):
            end = position + len(word)
            if tag in mapping:
                stats = per_tag.setdefault(tag, collections.Counter())
                stats["gold"] += 1
                stats["oracle_correct"] += oracle_tag == mapping[tag]
                stats["noun_baseline_correct"] += mapping[tag] == "n"
                stats["public_boundary_correct"] += aligned and (position, end) in boundaries
                stats["public_joint_correct"] += aligned and (position, end, mapping[tag]) in spans
            position = end
        predictions.append(dict(id=index + 1, oracle=oracle, public=predicted))
    for stats in per_tag.values():
        totals.update(stats)
    result = dict(
        metadata(), dataset="khPOS OPEN-TEST, four-category mapping proxy",
        proxy_protocol_sha256=sha256(ROOT / "benchmarks/accuracy/KHPOS_PROXY_PROTOCOL.md"),
        word_sha256=sha256(data / "OPEN-TEST.word"), tag_sha256=sha256(data / "OPEN-TEST.tag"),
        mapping=mapping, sentences=1000, backend_version=importlib.metadata.version("khmer-nltk"),
        model_sha256=sha256(model_path), totals=dict(totals),
        mapped_gold_coverage=totals["gold"] / totals["all_gold_tokens"],
        oracle_tag_accuracy=totals["oracle_correct"] / totals["gold"],
        noun_baseline_accuracy=totals["noun_baseline_correct"] / totals["gold"],
        public_boundary_recall=totals["public_boundary_correct"] / totals["gold"],
        public_joint_recall=totals["public_joint_correct"] / totals["gold"],
        per_original_tag={key: dict(value) for key, value in sorted(per_tag.items())},
        limitations="Partial tag coverage, annotation mismatch, no training-overlap audit. Not overall POS F1.")
    write(data / "accuracy_predictions/pos_proxy.json", predictions)
    write(output / "pos_proxy.json", result)
    print("POS cross-corpus proxy", json.dumps(result), flush=True)


def annotation_rows(data):
    from PIL import Image
    root = data / "khob/level1/khob-dataset/level-1"
    rows = []
    for path in sorted(root.rglob("*.json")):
        annotation = json.loads(path.read_text(encoding="utf-8"))
        image_path = path.parent / Path(annotation["imagePath"]).name
        with Image.open(image_path) as image:
            width, height = image.size
        sx = width / annotation["imageWidth"]
        sy = height / annotation["imageHeight"]
        regions = []
        for shape in annotation["shapes"]:
            points = shape["points"]
            box = (min(x for x, y in points) * sx, min(y for x, y in points) * sy,
                   max(x for x, y in points) * sx, max(y for x, y in points) * sy)
            regions.append((shape["label"].replace("\\t", "\t"), box))
        rows.append(dict(id=path.relative_to(root).with_suffix("").as_posix(),
                         annotation=path, image=image_path, width=width, height=height,
                         scaled=sx != 1 or sy != 1, regions=regions))
    if len(rows) != 60 or sum(len(row["regions"]) for row in rows) != 1862:
        raise ValueError("KHOB data differs from frozen protocol")
    return rows


def evaluate_ocr(data, output):
    import PIL
    import pytesseract
    from PIL import Image
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.lib.utils import ImageReader
    rows, pages, crops, predictions = annotation_rows(data), [], [], []
    cache = data / "accuracy_predictions"
    cache.mkdir(exist_ok=True)
    crop_path = cache / "current_crop.png"
    started = time.perf_counter()
    for row in rows:
        reference = "\n".join(label for label, _ in row["regions"])
        report = ket.khanalyze(row["image"], segment=False)
        layout = report.pages[0].layout
        line_boxes = [(line.box.left, line.box.top, line.box.right, line.box.bottom)
                      for line in layout.lines]
        box_score = matched_boxes([box for _, box in row["regions"]], line_boxes)
        score = dict(id=row["id"], annotation_sha256=sha256(row["annotation"]),
                     image_sha256=sha256(row["image"]), scaled_coordinates=row["scaled"],
                     layout_proxy=box_score, **text_score(reference, report.text))
        pages.append(score)
        predictions.append(dict(id=row["id"], reference=reference, prediction=report.text))
        with Image.open(row["image"]) as image:
            for index in (j * len(row["regions"]) // 4 for j in range(4)):
                label, box = row["regions"][index]
                bounds = (max(0, math.floor(box[0]) - 2), max(0, math.floor(box[1]) - 2),
                          min(row["width"], math.ceil(box[2]) + 2),
                          min(row["height"], math.ceil(box[3]) + 2))
                image.crop(bounds).convert("RGB").save(crop_path)
                crop = ket.khocr_layout(crop_path, psm=7, segment=False)
                crop_score = dict(id=row["id"] + ":" + str(index), **text_score(label, crop.text))
                crops.append(crop_score)
                predictions.append(dict(id=crop_score["id"], reference=label, prediction=crop.text))
        print("OCR", row["id"], "CER", round(score["codepoint_edits"] /
              max(1, score["reference_codepoints"]), 4), flush=True)
    # Lossless image-only PDF with exactly the source dimensions at 200 DPI.
    scans = [row for row in rows if row["id"].startswith("task-3/")]
    pdf_path = cache / "khob_scans.pdf"
    canvas = Canvas(str(pdf_path), pageCompression=1, invariant=1)
    for row in scans:
        width, height = row["width"] * 72 / 200, row["height"] * 72 / 200
        canvas.setPageSize((width, height))
        with Image.open(row["image"]) as image:
            canvas.drawImage(ImageReader(image.convert("RGB")), 0, 0, width=width, height=height)
        canvas.showPage()
    canvas.save()
    pdf = ket.khanalyze(pdf_path, segment=False)
    if len(pdf.pages) != 15:
        raise ValueError("PDF transport lost pages")
    pdf_scores = []
    for row, page in zip(scans, pdf.pages):
        reference = "\n".join(label for label, _ in row["regions"])
        pdf_scores.append(dict(id=row["id"], **text_score(reference, page.layout.text)))
    result = dict(
        metadata(), dataset="KHOB level-1, updated 2026-01-31",
        archive_sha256=sha256(data / "khob/khob-level-1-updated-31012026.zip"),
        engine=str(pytesseract.get_tesseract_version()).splitlines()[0],
        dependencies={name: importlib.metadata.version(name) for name in
                      ("Pillow", "pytesseract", "pypdfium2", "rapidfuzz", "reportlab")},
        config=dict(language="khm", psm=3, preprocess="none", confidence_minimum=0.0),
        pages=aggregate_text(pages), crops=aggregate_text(crops),
        pdf_transport=dict(aggregate_text(pdf_scores), pdf_sha256=sha256(pdf_path)),
        scaled_annotation_pages=sum(row["scaled"] for row in rows),
        per_task={}, per_page=pages, per_crop=crops, seconds=time.perf_counter() - started)
    for task in ("task-1", "task-2", "task-3", "task-4"):
        task_pages = [page for page in pages if page["id"].startswith(task + "/")]
        result["per_task"][task] = dict(aggregate_text(task_pages), layout_proxy=fscore(
            *(sum(page["layout_proxy"][key] for page in task_pages)
              for key in ("correct", "predicted", "gold"))))
    # Hash the actual installed language data; model differences matter.
    import subprocess
    listing = subprocess.check_output(["tesseract", "--list-langs"], stderr=subprocess.STDOUT).decode()
    directory = re.search(r'"([^"]+)"', listing)
    traineddata = Path(directory.group(1)) / "khm.traineddata" if directory else None
    result["khm_traineddata_sha256"] = sha256(traineddata) if traineddata and traineddata.is_file() else None
    write(cache / "ocr_predictions.json", predictions)
    write(output / "ocr.json", result)
    print("OCR aggregate", json.dumps(result["pages"]), flush=True)


def evaluate_challenges(data, output):
    path = ROOT / "benchmarks/accuracy/challenges.json"
    cases = json.loads(path.read_text(encoding="utf-8"))
    sentences = []
    for case in cases["sentences"]:
        result = span_totals(case["text"], case["expected"])
        sentences.append(dict(id=case["id"], **result,
                              predicted=ket.khsentences(case["text"])))
    extractions, total = [], collections.Counter()
    by_kind = collections.defaultdict(collections.Counter)
    for case in cases["extraction"]:
        gold = {}
        for entity in case["expected"]:
            start = case["text"].index(entity["text"], entity.get("after", 0))
            gold[(entity["kind"], start, start + len(entity["text"]))] = entity["value"]
        predicted_items = ket.khextract(case["text"], **case.get("options", {}))
        predicted = {(item.kind, item.start, item.end): item.value for item in predicted_items}
        common = set(gold) & set(predicted)
        values = sum(gold[key] == predicted[key] for key in common)
        total.update(correct=len(common), predicted=len(predicted), gold=len(gold),
                     value_correct=values, exact_cases=predicted == gold)
        for kind in ("url", "email", "phone", "date", "number"):
            stats = by_kind[kind]
            stats["gold"] += sum(key[0] == kind for key in gold)
            stats["predicted"] += sum(key[0] == kind for key in predicted)
            stats["correct"] += sum(key[0] == kind for key in common)
            stats["value_correct"] += sum(key[0] == kind and gold[key] == predicted[key] for key in common)
        extractions.append(dict(id=case["id"], exact=predicted == gold,
                               predicted=[item._asdict() for item in predicted_items]))
    result = dict(
        metadata(), dataset="Agent-authored engineering challenges; not human-independent gold",
        cases_sha256=sha256(path),
        sentences=dict(combine_spans(sentences), failures=[item for item in sentences if not item["exact"]]),
        extraction=dict(fscore(total["correct"], total["predicted"], total["gold"]),
                        cases=len(extractions), exact_cases=total["exact_cases"],
                        value_correct=total["value_correct"],
                        value_accuracy_on_matched=(total["value_correct"] / total["correct"]
                                                   if total["correct"] else None),
                        by_kind={kind: dict(fscore(stats["correct"], stats["predicted"], stats["gold"]),
                                           value_correct=stats["value_correct"])
                                 for kind, stats in sorted(by_kind.items())},
                        failures=[item for item in extractions if not item["exact"]]))
    write(output / "challenges.json", result)
    print("Challenges", json.dumps(result, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checks", nargs="+", choices=("pos", "pos_proxy", "sentences", "ocr", "challenges"))
    parser.add_argument("--data", type=Path, default=ROOT / ".evaluation")
    parser.add_argument("--output", type=Path, default=ROOT / "benchmarks/accuracy/results")
    args = parser.parse_args()
    for check in args.checks:
        globals()["evaluate_" + check](args.data, args.output)


if __name__ == "__main__":
    main()

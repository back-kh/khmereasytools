"""Evaluation-only metrics. Never imported by the runtime package."""
import hashlib
import subprocess
import unicodedata
from pathlib import Path


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def provenance():
    root = Path(__file__).resolve().parents[1]
    source = hashlib.sha256()
    for path in sorted((root / "khmereasytools").rglob("*.py")):
        source.update(path.relative_to(root).as_posix().encode("utf-8"))
        source.update(path.read_bytes())
    return {
        "base_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(root)).decode().strip(),
        "runtime_python_sources_sha256": source.hexdigest(),
    }


def fscore(correct, predicted, gold):
    precision = correct / predicted if predicted else 0.0
    recall = correct / gold if gold else 0.0
    return dict(correct=correct, predicted=predicted, gold=gold,
                precision=precision, recall=recall,
                f1=2 * correct / (predicted + gold) if predicted + gold else 0.0)


def compact(text):
    """Fixed scoring projection: NFC; remove Unicode whitespace and ZWSP."""
    return "".join(c for c in unicodedata.normalize("NFC", text)
                   if not c.isspace() and c != "\u200b")


def distance(reference, prediction):
    # Optional accelerator is evaluation-only. The fallback is exact too.
    try:
        from rapidfuzz.distance.Levenshtein import distance as accelerated
    except ImportError:
        previous = list(range(len(prediction) + 1))
        for i, ref in enumerate(reference, 1):
            row = [i]
            for j, pred in enumerate(prediction, 1):
                row.append(min(row[-1] + 1, previous[j] + 1,
                               previous[j - 1] + (ref != pred)))
            previous = row
        return previous[-1]
    return accelerated(reference, prediction)


def text_score(reference, prediction):
    """Code-point CER; supplementary score uses whitespace-delimited units."""
    folded_ref, folded_pred = compact(reference), compact(prediction)
    raw_ref = " ".join(unicodedata.normalize("NFC", reference).split())
    raw_pred = " ".join(unicodedata.normalize("NFC", prediction).split())
    return {
        "reference_codepoints": len(folded_ref),
        "codepoint_edits": distance(folded_ref, folded_pred),
        "exact_compact": folded_ref == folded_pred,
        "spacefold_reference_codepoints": len(raw_ref),
        "spacefold_codepoint_edits": distance(raw_ref, raw_pred),
        # Khmer whitespace usually delimits phrases, not linguistic words.
        "reference_whitespace_units": len(raw_ref.split()),
        "whitespace_unit_edits": distance(raw_ref.split(), raw_pred.split()),
    }


def aggregate_text(rows):
    fields = ("reference_codepoints", "codepoint_edits",
              "spacefold_reference_codepoints", "spacefold_codepoint_edits",
              "reference_whitespace_units", "whitespace_unit_edits")
    result = {field: sum(row[field] for row in rows) for field in fields}
    result.update(samples=len(rows), exact_compact=sum(row["exact_compact"] for row in rows))
    for key, numerator, denominator in (
            ("compact_codepoint_cer", "codepoint_edits", "reference_codepoints"),
            ("spacefold_codepoint_cer", "spacefold_codepoint_edits",
             "spacefold_reference_codepoints"),
            ("whitespace_unit_error_rate", "whitespace_unit_edits",
             "reference_whitespace_units")):
        result[key] = result[numerator] / result[denominator] if result[denominator] else None
    return result


def iou(left, right):
    x0, y0 = max(left[0], right[0]), max(left[1], right[1])
    x1, y1 = min(left[2], right[2]), min(left[3], right[3])
    intersection = max(0, x1 - x0) * max(0, y1 - y0)
    area = ((left[2] - left[0]) * (left[3] - left[1]) +
            (right[2] - right[0]) * (right[3] - right[1]) - intersection)
    return intersection / area if area else 0.0


def matched_boxes(gold, predicted, threshold=0.5):
    """Deterministic greedy descending-IoU one-to-one proxy, not polygon AP."""
    candidates = sorted(((-iou(a, b), i, j)
                         for i, a in enumerate(gold) for j, b in enumerate(predicted)
                         if iou(a, b) >= threshold))
    used_gold, used_pred = set(), set()
    for _, i, j in candidates:
        if i not in used_gold and j not in used_pred:
            used_gold.add(i)
            used_pred.add(j)
    return fscore(len(used_gold), len(predicted), len(gold))

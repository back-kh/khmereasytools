"""Explicit OCR token metrics; not human-gold Khmer word segmentation."""
from collections import Counter
import unicodedata

from rapidfuzz.distance import Levenshtein


def whitespace_tokens(text):
    return unicodedata.normalize("NFC", text).replace("\u200b", " ").split()


def segmented_tokens(text):
    from khmereasytools import khseg_spans
    return [t.text for t in khseg_spans(unicodedata.normalize("NFC", text))
            if t.kind not in ("whitespace", "boundary")]


def edit_counts(reference, prediction):
    counts = Counter(op.tag for op in Levenshtein.editops(reference, prediction))
    result = dict(substitutions=counts["replace"], deletions=counts["delete"], insertions=counts["insert"],
                  reference_units=len(reference), prediction_units=len(prediction))
    result["edits"] = result["substitutions"] + result["deletions"] + result["insertions"]
    if result["edits"] != Levenshtein.distance(reference, prediction):
        raise ValueError("Alignment count differs from minimum distance")
    result["error_rate"] = result["edits"] / len(reference) if reference else None
    return result


def word_scores(reference, prediction):
    return dict(whitespace_unit_wer=edit_counts(whitespace_tokens(reference), whitespace_tokens(prediction)),
                segmentation_assisted_wer=edit_counts(segmented_tokens(reference), segmented_tokens(prediction)))


def aggregate(rows):
    names = ("substitutions", "deletions", "insertions", "reference_units", "prediction_units", "edits")
    result = {name: sum(row[name] for row in rows) for name in names}
    result["error_rate"] = result["edits"] / result["reference_units"] if result["reference_units"] else None
    return result

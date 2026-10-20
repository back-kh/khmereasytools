"""Evaluate segmentation against a caller-provided space-delimited gold file.

khPOS mode removes its _/~ compound markup inside gold words. No gold words
or frequencies are added to the runtime dictionary. The corpus is not bundled.
"""
import argparse
import hashlib
import json
import platform
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from khmereasytools import khseg


def token_spans(words):
    spans, position = set(), 0
    for word in words:
        spans.add((position, position + len(word)))
        position += len(word)
    return spans


def evaluate(gold_sentences, segment):
    correct = predicted_count = gold_count = exact = 0
    started = time.perf_counter()
    for gold in gold_sentences:
        text = "".join(gold)
        predicted = segment(text)
        if "".join(predicted) != text:
            raise ValueError("Tokenizer changed benchmark input; span scores would be invalid")
        predicted_spans, gold_spans = token_spans(predicted), token_spans(gold)
        correct += len(predicted_spans & gold_spans)
        predicted_count += len(predicted_spans)
        gold_count += len(gold_spans)
        exact += predicted == gold
    precision = correct / predicted_count if predicted_count else 0
    recall = correct / gold_count if gold_count else 0
    return dict(sentences=len(gold_sentences), gold_tokens=gold_count,
                predicted_tokens=predicted_count, correct_tokens=correct,
                precision=precision, recall=recall,
                token_f1=2 * precision * recall / (precision + recall) if precision + recall else 0,
                exact_sentences=exact, seconds=time.perf_counter() - started)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gold", type=Path)
    parser.add_argument("--khpos", action="store_true", help="Remove khPOS compound markup _ and ~ inside gold words")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    raw = args.gold.read_bytes()
    gold_sentences = []
    for line in raw.decode("utf-8-sig").splitlines():
        words = line.split()
        if args.khpos:
            words = [word.replace("\\~", "").replace("\\_", "").replace("_", "").replace("~", "").replace("\u200b", "") for word in words]
        words = [word for word in words if word]
        if words:
            gold_sentences.append(words)
    strategies = {
        "v0.4_legacy_213": dict(dictionary="legacy", strategy="legacy"),
        "legacy_213_lossless_greedy": dict(dictionary="legacy", strategy="longest"),
        "expanded_greedy": dict(dictionary="expanded", strategy="longest"),
        "expanded_coverage": dict(dictionary="expanded", strategy="coverage"),
    }
    manifest = json.loads((Path(__file__).resolve().parents[1] / "khmereasytools/data/dictionary_manifest.json").read_text(encoding="utf-8"))
    result = dict(python=platform.python_version(), corpus_sha256=hashlib.sha256(raw).hexdigest(),
                  dictionary_sha256=manifest["output_sha256"], dictionary_entries=manifest["combined_entries"],
                  protocol="Exact token spans; concatenate gold words; no training or tuning on this file.",
                  gold_markup="Remove _/~ and ZWSP" if args.khpos else "None",
                  results={})
    for name, options in strategies.items():
        result["results"][name] = evaluate(gold_sentences, lambda text: khseg(text, **options))
    output = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()

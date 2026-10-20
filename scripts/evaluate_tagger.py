"""KET-Tagger diagnostics; read benchmarks/accuracy/TAGGER_PROTOCOL.md first."""

import argparse
import importlib
import json
import platform
import sys
import time
import unicodedata
import zipfile
from collections import Counter
from pathlib import Path

from evaluation_metrics import compact, fscore, nova_word_gold, provenance, sha256


ROOT = Path(__file__).resolve().parents[1]
PROJECTION = {
    "NOUN": "n", "PROPN": "n", "PRON": "n", "VERB": "v", "ADJ": "a", "DET": "a",
    "ADV": "o", "ADP": "o", "AUX": "o", "CCONJ": "o", "SCONJ": "o", "PART": "o",
    "NUM": "1", "PUNCT": ".", "INTJ": "+", "SYM": "+", "X": "X",
}


def projected(token):
    return "v" if token.role == "copula" else PROJECTION[token.tag]


def verified_alt(data):
    archive_path = data / "km-nova-181101.zip"
    if sha256(archive_path) != "0c6457d4a3327f3dc0b381704cbad71af120e963bfa1cdb06765fa0ed0c9098a":
        raise ValueError("ALT archive hash differs from the pinned download")
    split_path = data / "URL-test.txt"
    if sha256(split_path) != "6d67d6bf5c4e7574116355d71ef927c66aca2f7ab7267b14591ea250f24ec722":
        raise ValueError("ALT split hash differs from the pinned test split")
    files = ("data_km.km-tok.nova", "data_km.km-tag.nova")
    with zipfile.ZipFile(str(archive_path)) as archive:
        for filename in files:
            names = [name for name in archive.namelist() if Path(name).name == filename]
            if len(names) != 1 or archive.read(names[0]) != (data / filename).read_bytes():
                raise ValueError("ALT extracted annotations differ from the pinned archive: " + filename)
    articles = {line.split("\t")[0].split(".")[1] for line in split_path.read_text(encoding="utf-8").splitlines()}
    tags = dict(line.split("\t", 1) for line in (data / files[1]).read_text(encoding="utf-8").splitlines())
    rows = []
    for line in (data / files[0]).read_text(encoding="utf-8").splitlines():
        key, text = line.split("\t", 1)
        if key.split(".")[1] in articles:
            rows.append((key, nova_word_gold(text.split(), tags[key].split())))
    if len(articles) != 97 or len(rows) != 1018 or sum(len(pairs) for _, pairs in rows) != 26551:
        raise ValueError("Unexpected ALT test coverage")
    return rows, {path.name: sha256(path) for path in (archive_path, split_path) + tuple(data / f for f in files)}


def pairs_to_spans(pairs):
    position, spans = 0, []
    for word, tag in pairs:
        word = compact(word)
        if word:
            spans.append((position, position + len(word), tag))
            position += len(word)
    return spans


def gold_input(pairs, token_type):
    spans, position = [], 0
    for word, _ in pairs:
        kind = ("punctuation" if all(unicodedata.category(c).startswith("P") for c in word)
                else "number" if word.isdecimal() else "word")
        spans.append(token_type(word, position, position + len(word), kind))
        position += len(word)
    return spans


def accuracy_counts(confusion):
    total = sum(confusion.values())
    covered = sum(count for (gold, pred), count in confusion.items() if pred != "X")
    correct = sum(count for (gold, pred), count in confusion.items() if gold == pred)
    lexical = Counter({pair: count for pair, count in confusion.items() if pair[0] in ("n", "v", "a", "o")})
    return dict(tokens=total, correct=correct, covered=covered,
                coverage=covered / total if total else None,
                all_token_coarse_accuracy=correct / total if total else None,
                selective_coarse_accuracy=correct / covered if covered else None,
                lexical_tokens=sum(lexical.values()),
                lexical_covered=sum(count for (g, p), count in lexical.items() if p != "X"),
                lexical_correct=sum(count for (g, p), count in lexical.items() if g == p),
                confusion={gold: {pred: confusion[(gold, pred)] for pred in sorted({p for g, p in confusion if g == gold})}
                           for gold in sorted({g for g, p in confusion})})


def evaluate_rows(rows, raw_tagger, oracle_tagger):
    confusion, predicted_tags = Counter(), Counter()
    boundaries, joint = [0, 0, 0], [0, 0, 0]
    alignment_failures, unknown = 0, 0
    started = time.perf_counter()
    for _, gold in rows:
        oracle = oracle_tagger(gold)
        if [compact(word) for word, _ in oracle] != [word for word, _ in gold]:
            raise ValueError("Gold-boundary adapter changed words or token counts")
        for (_, target), (_, label) in zip(gold, oracle):
            confusion[(target, label)] += 1
        text = "".join(word for word, _ in gold)
        predicted = raw_tagger(text)
        aligned = compact("".join(word for word, _ in predicted)) == text
        alignment_failures += not aligned
        tagged_gold, tagged_pred = set(pairs_to_spans(gold)), set(pairs_to_spans(predicted))
        gold_bounds = {span[:2] for span in tagged_gold}
        pred_bounds = {span[:2] for span in tagged_pred}
        for counter, actual, target in ((boundaries, pred_bounds, gold_bounds), (joint, tagged_pred, tagged_gold)):
            counter[0] += len(actual & target) if aligned else 0
            counter[1] += len(actual)
            counter[2] += len(target)
        predicted_tags.update(label for _, label in predicted)
        unknown += sum(label == "X" for _, label in predicted)
    return dict(sentences=len(rows), seconds=time.perf_counter() - started,
                gold_boundaries=accuracy_counts(confusion),
                reconstructed_text=dict(segmentation=fscore(*boundaries), joint_coarse=fscore(*joint),
                                        unknown_tokens=unknown, predicted_tag_counts=dict(sorted(predicted_tags.items())),
                                        alignment_failures=alignment_failures))


def authored_checks(ket, *, model="compact"):
    path = ROOT / "tests/fixtures/tagger_cases.json"
    cases = json.loads(path.read_text(encoding="utf-8"))["cases"]
    results = []
    for case in cases:
        tokens = ket.khtag(case["text"], with_spans=True, model=model)
        passed = "pairs" not in case or [[t.text, t.tag] for t in tokens] == case["pairs"]
        passed = passed and all([t.role for t in tokens if t.text == word] == [role]
                                for word, role in case.get("roles", {}).items())
        results.append(dict(id=case["id"], specified_assertions_passed=passed))
    return dict(status="Authored development assertions, partial annotations; not independent accuracy.",
                cases=len(cases), passed=sum(r["specified_assertions_passed"] for r in results),
                cases_sha256=sha256(path), per_case=results)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / ".evaluation/alt")
    parser.add_argument("--output", type=Path, default=ROOT / ".evaluation/tagger_v1_replay/results.json")
    parser.add_argument("--with-crf", action="store_true", help="Also evaluate the actual optional CRF")
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT))
    import khmereasytools as ket
    from khmereasytools.tagging import _starter_lexicon
    rows, hashes = verified_alt(args.data)
    tagger = ket.KhmerTagger(model="rules")

    def raw(text):
        return [(token.text, projected(token)) for token in tagger.tag(text, with_spans=True)]

    def oracle(pairs):
        return [(token.text, projected(token)) for token in tagger._tag_spans(gold_input(pairs, ket.TokenSpan))]

    report = dict(status="Exploratory coarse compatibility diagnostic, not fine POS/particle accuracy.",
                  metadata=dict(provenance(), python=platform.python_version(), platform=platform.platform(),
                                protocol_sha256=sha256(ROOT / "benchmarks/accuracy/TAGGER_PROTOCOL.md"),
                                script_sha256=sha256(__file__), alt_files_sha256=hashes,
                                runtime_tagging_sha256=sha256(ROOT / "khmereasytools/tagging.py"),
                                authored_lexicon_entries=len(_starter_lexicon()),
                                projection=PROJECTION, copula_projection="v"),
                  authored_development=authored_checks(ket, model="rules"), ket_tagger=evaluate_rows(rows, raw, oracle))
    if args.with_crf:
        from khmereasytools.pos import _tag_words
        report["optional_crf"] = evaluate_rows(rows, ket.khpos,
                                                lambda pairs: _tag_words([word for word, _ in pairs]))
        backend = importlib.import_module("khmernltk.pos_tag")
        report["metadata"]["crf_model_sha256"] = sha256(backend.model_path)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "metadata"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

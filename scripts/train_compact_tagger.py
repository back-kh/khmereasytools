"""Prepare, train/select, then evaluate a compact research CRF in separate phases.

Read TAGGER_V2_PROTOCOL.md. Training needs python-crfsuite; inference does not.
External corpus text and native training files stay in ignored .evaluation.
"""

import argparse
import gzip
import hashlib
import json
import platform
import sys
import time
import urllib.request
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from khmereasytools.compact_pos import CompactPOS, NATIVE_TO_PUBLIC, features
from evaluation_metrics import compact, fscore, sha256
from evaluate_tagger import verified_alt, pairs_to_spans

REVISION = "0211405c145b0a340ad558569bd06c946b2296b4"
BASE = "https://raw.githubusercontent.com/ye-kyaw-thu/khPOS/" + REVISION + "/"
FILES = {
    "train.word": ("corpus-draft-ver-1.0/data/train6/train6.word", "1f6cbae170f3d9461a7b818bbfb1d5f0d8629560595f37e081a2d68b7adbdfcb"),
    "train.tag": ("corpus-draft-ver-1.0/data/train6/train6.tag", "7e89e630fb986bc7aaf739153dde1024e9d47d5196c80befa11d275cd153a222"),
    "close.word": ("corpus-draft-ver-1.0/data/CLOSE-TEST.word", "790e20756490fb604baa930d701b3853e98725981c72ee867a45da2303e92505"),
    "close.tag": ("corpus-draft-ver-1.0/data/CLOSE-TEST.tag", "23a849931f57b87e8c9369514772425813f99eb9daf87d59c0bfda48483af459"),
    "open.word": ("corpus-draft-ver-1.0/data/OPEN-TEST.word", "1b10b866263e6beb93cbf5c249ffc6a5d4d11dbc7beb90717c9f4e14cb152869"),
    "open.tag": ("corpus-draft-ver-1.0/data/OPEN-TEST.tag", "1714a6aeb0bedb1df6dde577a409799f6700bfd97f107cdf7c5a2624090b2cd4"),
}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def corpus_word(word):
    return compact(word.replace("\\~", "").replace("\\_", "").replace("~", "").replace("_", ""))


def read_pairs(directory, name):
    words = (directory / (name + ".word")).read_text(encoding="utf-8-sig").splitlines()
    tags = (directory / (name + ".tag")).read_text(encoding="utf-8-sig").splitlines()
    if len(words) != len(tags):
        raise ValueError("Corpus line mismatch: " + name)
    result = []
    for index, (word_line, tag_line) in enumerate(zip(words, tags)):
        tokens, labels = [corpus_word(w) for w in word_line.split()], tag_line.split()
        if len(tokens) != len(labels) or not tokens or not all(tokens):
            raise ValueError("Corpus alignment/empty token: {} row {}".format(name, index))
        if any(label not in NATIVE_TO_PUBLIC for label in labels):
            raise ValueError("Unknown native corpus label")
        result.append(("{}:{:05d}".format(name, index), list(zip(tokens, labels))))
    return result


def key(pairs):
    return "".join(word for word, _ in pairs)


def partition_rows(train, close, opened, alt):
    excluded = {key(pairs) for rows in (close, opened, alt) for _, pairs in rows}
    seen, retained, removed, duplicates, conflicts = {}, [], [], [], []
    for identifier, pairs in train:
        text = key(pairs)
        if text in excluded:
            removed.append(identifier)
        elif text in seen:
            duplicates.append(identifier)
            if seen[text] != pairs:
                conflicts.append(identifier)
        else:
            seen[text] = pairs
            retained.append((identifier, pairs))
    training, development = [], []
    for row in retained:
        hashed = hashlib.sha256(("ket-pos-v2-dev\0" + key(row[1])).encode("utf-8")).hexdigest()
        (development if int(hashed[:8], 16) % 10 == 0 else training).append(row)
    return training, development, dict(removed_test_matches=removed, removed_duplicates=duplicates,
                                       conflicting_duplicate_ids=conflicts)


def prepare(directory):
    directory.mkdir(parents=True, exist_ok=True)
    for name, (relative, expected) in FILES.items():
        target = directory / name
        if not target.is_file() or sha256(target) != expected:
            with urllib.request.urlopen(BASE + relative, timeout=45) as response:
                data = response.read(8 * 1024 * 1024 + 1)
            if len(data) > 8 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != expected:
                raise ValueError("Corpus download/hash mismatch: " + name)
            target.write_bytes(data)
    rows = {name: read_pairs(directory, name) for name in ("train", "close", "open")}
    alt_directory = ROOT / ".evaluation/alt"
    alt_directory.mkdir(parents=True, exist_ok=True)
    alt_base = "https://www2.nict.go.jp/astrec-att/member/mutiyama/ALT/"
    for name, expected in (("km-nova-181101.zip", "0c6457d4a3327f3dc0b381704cbad71af120e963bfa1cdb06765fa0ed0c9098a"),
                           ("URL-test.txt", "6d67d6bf5c4e7574116355d71ef927c66aca2f7ab7267b14591ea250f24ec722")):
        target = alt_directory / name
        if not target.is_file():
            with urllib.request.urlopen(alt_base + name, timeout=45) as response:
                data = response.read(16 * 1024 * 1024 + 1)
            if len(data) > 16 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != expected:
                raise ValueError("Pinned ALT download changed")
            target.write_bytes(data)
    with zipfile.ZipFile(str(alt_directory / "km-nova-181101.zip")) as archive:
        for filename in ("data_km.km-tok.nova", "data_km.km-tag.nova"):
            destination = alt_directory / filename
            if not destination.exists():
                names = [n for n in archive.namelist() if Path(n).name == filename]
                if len(names) != 1 or archive.getinfo(names[0]).file_size > 16 * 1024 * 1024:
                    raise ValueError("Invalid ALT annotation archive")
                destination.write_bytes(archive.read(names[0]))
    alt, alt_hashes = verified_alt(alt_directory)
    train, dev, audit = partition_rows(rows["train"], rows["close"], rows["open"], alt)
    sets = {name: {key(pairs) for _, pairs in group} for name, group in
            (("train", train), ("dev", dev), ("close", rows["close"]), ("open", rows["open"]), ("alt", alt))}
    if any(sets["train"] & sets[name] or sets["dev"] & sets[name] for name in ("close", "open", "alt")) or sets["train"] & sets["dev"]:
        raise ValueError("Prepared partitions overlap")
    manifest = dict(protocol_sha256=sha256(ROOT / "benchmarks/accuracy/TAGGER_V2_PROTOCOL.md"),
                    sources={name: dict(url=BASE + relative, sha256=expected) for name, (relative, expected) in FILES.items()},
                    alt_sources_sha256=alt_hashes, **audit,
                    splits={name: dict(sentences=len(group), tokens=sum(len(pairs) for _, pairs in group),
                                       digest=digest(group), row_ids=[identifier for identifier, _ in group])
                            for name, group in (("train", train), ("dev", dev), ("close", rows["close"]), ("open", rows["open"]), ("alt", alt))})
    existing = directory / "partitions.json"
    if existing.exists() and json.loads(existing.read_text(encoding="utf-8")) != manifest:
        raise ValueError("Frozen partition manifest differs; use a new experiment directory")
    write(existing, manifest)
    return train, dev, rows["close"], rows["open"], alt, manifest


def export_model(tagger, train, c1, manifest, target):
    labels, info = list(tagger.labels()), tagger.info()
    indexes = {label: index for index, label in enumerate(labels)}
    states = defaultdict(list)
    for (feature, label), value in info.state_features.items():
        weight = round(value * 1000)
        if weight:
            states[feature].append([indexes[label], weight])
    transitions = [[0] * len(labels) for _ in labels]
    for (left, right), value in info.transitions.items():
        transitions[indexes[left]][indexes[right]] = round(value * 1000)
    counts = defaultdict(Counter)
    for _, pairs in train:
        for word, label in pairs:
            counts[word][indexes[label]] += 1
    model = dict(format="ket-pos-crf-v1", scale=1000, labels=labels,
                 state={f: sorted(v) for f, v in states.items()}, transitions=transitions,
                 lexicon={word: [sum(count.values()), sorted([label, n] for label, n in count.items())]
                          for word, count in counts.items()},
                 metadata=dict(license="CC-BY-NC-SA-4.0", segmentation="frequency", c1=c1,
                               source="khPOS", source_revision=REVISION,
                               source_url="https://github.com/ye-kyaw-thu/khPOS",
                               authors=["Vichet Chea", "Ye Kyaw Thu"],
                               training_sha256=manifest["splits"]["train"]["digest"],
                               training_sentences=len(train), training_tokens=sum(len(pairs) for _, pairs in train),
                               protocol_sha256=manifest["protocol_sha256"]))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(gzip.compress(json.dumps(model, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"), mtime=0))
    return model


def evaluate_native(model, rows, *, profile=None, native=None):
    total = correct = unknown = unknown_correct = majority_correct = disagreement = 0
    boundaries, joint = [0, 0, 0], [0, 0, 0]
    by_tag = defaultdict(Counter)
    majority_global = Counter()
    for distribution in model.lexical.values():
        majority_global.update({model.labels[i]: count for i, count in distribution})
    fallback = max(model.labels, key=lambda label: (majority_global[label], label))
    started = time.perf_counter()
    for identifier, gold in rows:
        words, tags = zip(*gold)
        predicted = model.predict(words)
        if native is not None:
            reference = native.tag([features(words, i) for i in range(len(words))])
            disagreement += sum(a != b for a, b in zip(predicted, reference))
        for word, actual, label in zip(words, tags, predicted):
            total += 1
            correct += actual == label
            unseen = word not in model.word_counts
            unknown += unseen
            unknown_correct += unseen and actual == label
            distribution = model.lexical.get(word)
            majority = model.labels[max(distribution, key=lambda pair: (pair[1], -pair[0]))[0]] if distribution else fallback
            majority_correct += majority == actual
            by_tag[actual]["gold"] += 1
            by_tag[label]["predicted"] += 1
            by_tag[actual]["correct"] += label == actual
        text = key(gold)
        spans = [span for span in model.segment(text, (), profile=profile) if span.kind not in ("whitespace", "boundary")]
        words = [span.text for span in spans]
        if "".join(words) != text:
            raise ValueError("Lossy model segmentation at " + identifier)
        predicted = list(zip(words, model.predict(words)))
        target, actual = set(pairs_to_spans(gold)), set(pairs_to_spans(predicted))
        for counter, a, b in ((joint, actual, target), (boundaries, {p[:2] for p in actual}, {p[:2] for p in target})):
            counter[0] += len(a & b)
            counter[1] += len(a)
            counter[2] += len(b)
    return dict(sentences=len(rows), tokens=total, native_correct=correct, native_accuracy=correct / total,
                answer_rate=1.0, lexical_coverage=(total - unknown) / total,
                unseen_tokens=unknown, unseen_correct=unknown_correct,
                unseen_accuracy=unknown_correct / unknown if unknown else None,
                majority_word_baseline_correct=majority_correct, majority_word_baseline_accuracy=majority_correct / total,
                native_export_disagreements=disagreement if native is not None else None,
                segmentation=fscore(*boundaries), joint_native=fscore(*joint),
                alignment_failures=0, per_tag={label: dict(stats) for label, stats in sorted(by_tag.items())},
                seconds=time.perf_counter() - started)


def train_select(directory, train, dev, manifest):
    import pycrfsuite
    if (directory / "selection.json").exists():
        raise ValueError("Selection is already frozen; do not retrain this experiment")
    x = []
    for _, pairs in train:
        words = [word for word, _ in pairs]
        x.append([features(words, i) for i in range(len(words))])
    y = [[label for _, label in pairs] for _, pairs in train]
    candidates = []
    for c1 in (0.1, 0.5):
        print("Training native CRF", c1, len(train), "sentences", flush=True)
        trainer = pycrfsuite.Trainer(verbose=False)
        for words, tags in zip(x, y):
            trainer.append(words, tags)
        trainer.set_params({"c1": c1, "c2": 0.1, "max_iterations": 100, "feature.possible_transitions": True})
        native_path = directory / ("candidate-{}.crfsuite".format(c1))
        trainer.train(str(native_path))
        tagger = pycrfsuite.Tagger()
        tagger.open(str(native_path))
        path = directory / ("candidate-{}.json.gz".format(c1))
        export_model(tagger, train, c1, manifest, path)
        for profile in ("frequency", "model"):
            model = CompactPOS(path)
            scores = evaluate_native(model, dev, profile=profile, native=tagger)
            candidates.append(dict(c1=c1, segmentation=profile, file=path.name, sha256=sha256(path),
                                   bytes=path.stat().st_size, development=scores))
            print("Development", c1, profile, scores["native_accuracy"], scores["joint_native"]["f1"], path.stat().st_size, flush=True)
    eligible = [candidate for candidate in candidates if candidate["bytes"] <= 2 * 1024 * 1024]
    if not eligible:
        raise ValueError("No candidate meets the frozen size limit")
    chosen = max(eligible, key=lambda c: (c["development"]["joint_native"]["f1"], c["development"]["native_accuracy"], -c["bytes"], -candidates.index(c)))
    selected_data = json.loads(gzip.decompress((directory / chosen["file"]).read_bytes()).decode("utf-8"))
    selected_data["metadata"]["segmentation"] = chosen["segmentation"]
    selected = directory / "selected.json.gz"
    selected.write_bytes(gzip.compress(json.dumps(selected_data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"), mtime=0))
    selection = dict(protocol_sha256=manifest["protocol_sha256"], partition_manifest_sha256=sha256(directory / "partitions.json"),
                     candidates=candidates, selected=chosen, selected_sha256=sha256(selected),
                     selected_bytes=selected.stat().st_size, train_digest=manifest["splits"]["train"]["digest"],
                     status="Frozen after development selection, before reserved predictions.")
    write(directory / "selection.json", selection)
    print("Frozen selection", chosen["c1"], chosen["segmentation"], sha256(selected), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "train", "evaluate"))
    parser.add_argument("--data", type=Path, default=ROOT / ".evaluation/tagger_v2")
    args = parser.parse_args()
    train, dev, close, opened, alt, manifest = prepare(args.data)
    print("Partitions", {name: (r["sentences"], r["tokens"]) for name, r in manifest["splits"].items()}, flush=True)
    if args.phase == "prepare":
        print("Purge/dedup", {name: len(rows) for name, rows in manifest.items() if name.startswith(("removed", "conflicting"))})
    elif args.phase == "train":
        train_select(args.data, train, dev, manifest)
    else:
        selection = json.loads((args.data / "selection.json").read_text(encoding="utf-8"))
        if selection["partition_manifest_sha256"] != sha256(args.data / "partitions.json"):
            raise ValueError("Partitions changed since selection")
        model = CompactPOS(args.data / "selected.json.gz", expected_sha256=selection["selected_sha256"])
        result = dict(protocol_sha256=manifest["protocol_sha256"], selection_sha256=sha256(args.data / "selection.json"),
                      selected_sha256=model.sha256, python=platform.python_version(), platform=platform.platform(),
                      close=evaluate_native(model, close), open=evaluate_native(model, opened))
        write(args.data / "reserved-native-results.json", result)
        print(json.dumps({name: {k: v for k, v in value.items() if k != "per_tag"} for name, value in result.items() if name in ("close", "open")}, indent=2), flush=True)


if __name__ == "__main__":
    main()

"""Record v2 reserved/native and comparable public-output diagnostics.

Run only after development selection is frozen. Never overwrite v1 artifacts.
"""

import argparse
import json
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import khmereasytools as ket
from khmereasytools.compact_pos import default_model, public_tag
from evaluation_metrics import provenance, sha256
from evaluate_tagger import authored_checks, evaluate_rows, gold_input, projected
from train_compact_tagger import prepare, evaluate_native


def public_evaluation(rows, tagger, *, nova=False):
    if not nova:
        rows = [(identifier, [(word, public_tag(word, tag)) for word, tag in pairs]) for identifier, pairs in rows]

    def convert(tokens):
        return [(token.text, projected(token) if nova else token.tag) for token in tokens]

    result = evaluate_rows(rows, lambda text: convert(tagger.tag(text, with_spans=True)),
                           lambda pairs: convert(tagger._tag_spans(gold_input(pairs, ket.TokenSpan))))
    if not nova:
        oracle = result["gold_boundaries"]
        oracle["all_token_mapped_upos_accuracy"] = oracle.pop("all_token_coarse_accuracy")
        oracle["selective_mapped_upos_accuracy"] = oracle.pop("selective_coarse_accuracy")
        for field in ("lexical_tokens", "lexical_covered", "lexical_correct"):
            oracle.pop(field)
        result["reconstructed_text"]["joint_mapped_upos"] = result["reconstructed_text"].pop("joint_coarse")
    return result


def timing():
    text = "ខ្ញុំកំពុងអានសៀវភៅ។ សិស្ស៣នាក់រៀននៅសាលារៀន។"
    tagger = ket.KhmerTagger()
    tagger.tag(text)
    elapsed = []
    for _ in range(100):
        started = time.perf_counter()
        tagger.tag(text)
        elapsed.append(time.perf_counter() - started)
    script = '''
import json,sys,time
started=time.perf_counter()
import khmereasytools as ket
ket.khtag("ខ្ញុំកំពុងអានសៀវភៅ។ សិស្ស៣នាក់រៀននៅសាលារៀន។")
report={"import_and_first_tag_ms":(time.perf_counter()-started)*1000}
try:
 import resource
 report["peak_rss_mib"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/(1024**2 if sys.platform=="darwin" else 1024)
except ImportError:
 pass
print(json.dumps(report))
'''
    cold = json.loads(subprocess.check_output([sys.executable, "-c", script], cwd=str(ROOT)).decode("utf-8"))
    return dict(cold, warm_median_ms=statistics.median(elapsed) * 1000,
                warm_p95_ms=sorted(elapsed)[94] * 1000, warm_repetitions=100, input_codepoints=len(text),
                note="Local single-process diagnostics, not a cross-device performance guarantee.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / ".evaluation/tagger_v2")
    parser.add_argument("--output", type=Path, default=ROOT / ".evaluation/tagger_v2/replay-results.json")
    args = parser.parse_args()
    train, dev, close, opened, alt, partitions = prepare(args.data)
    published = ROOT / "benchmarks/accuracy/tagger-v2"
    selection_path = published / "selection.json"
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    model = default_model()
    if model.sha256 != selection["selected_sha256"] or sha256(args.data / "partitions.json") != selection["partition_manifest_sha256"]:
        raise ValueError("Bundled model differs from frozen reserved evaluation")
    native = {"close": evaluate_native(model, close), "open": evaluate_native(model, opened)}
    rules, trained = ket.KhmerTagger(model="rules"), ket.KhmerTagger()
    result = dict(metadata=dict(provenance(), protocol_sha256=partitions["protocol_sha256"],
                                selection_sha256=sha256(selection_path),
                                partitions_sha256=sha256(args.data / "partitions.json"),
                                model_sha256=model.sha256, model_bytes=selection["selected_bytes"],
                                model_vocabulary_entries=len(model.word_counts),
                                state_features=len(model.state), python=platform.python_version(), platform=platform.platform(),
                                model_license="CC-BY-NC-SA-4.0", software_license="MIT",
                                script_sha256=sha256(__file__)),
                  partition_audit=dict(train_sentences=len(train), development_sentences=len(dev),
                                       removed_test_matches=len(partitions["removed_test_matches"]),
                                       removed_duplicates=len(partitions["removed_duplicates"]),
                                       conflicting_duplicates=len(partitions["conflicting_duplicate_ids"]),
                                       exact_train_dev_test_text_overlap=0,
                                       note="No source document IDs; related templates/articles may remain."),
                  authored_development=authored_checks(ket), performance=timing())
    for name, rows in (("close", close), ("open", opened)):
        result[name] = dict(native_23_labels=native[name],
                            rules_public=public_evaluation(rows, rules), compact_public=public_evaluation(rows, trained))
        print(name, "native", native[name]["native_accuracy"], "public", result[name]["compact_public"]["gold_boundaries"]["all_token_mapped_upos_accuracy"], flush=True)
    result["alt"] = dict(note="Previously observed cross-corpus diagnostic; lossy seven-class NOVA projection, not fine POS gold.",
                          rules=public_evaluation(alt, rules, nova=True), compact=public_evaluation(alt, trained, nova=True))
    old = json.loads((ROOT / "benchmarks/accuracy/tagger/results.json").read_text(encoding="utf-8"))["ket_tagger"]
    if result["alt"]["rules"]["gold_boundaries"]["correct"] != old["gold_boundaries"]["correct"]:
        raise ValueError("Rules baseline differs from the frozen v1 result")
    initial_path = published / "results-initial.json"
    if initial_path.exists():
        initial = json.loads(initial_path.read_text(encoding="utf-8"))
        for name, modes in (("close", ("rules_public", "compact_public")),
                            ("open", ("rules_public", "compact_public")), ("alt", ("rules", "compact"))):
            for mode in modes:
                for field in ("gold_boundaries", "reconstructed_text"):
                    if result[name][mode][field] != initial[name][mode][field]:
                        raise ValueError("Role amendment changed POS/span counts: " + name + "/" + mode)
        result["role_adapter_amendment"] = dict(
            initial_results_sha256=sha256(initial_path),
            amendment_sha256=sha256(ROOT / "benchmarks/accuracy/TAGGER_V2_ROLE_AMENDMENT.md"),
            native_public_pos_and_span_counts_unchanged=True,
            status="Adapted authored role development; no independent role gold or model retuning.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("ALT comparable", result["alt"]["rules"]["gold_boundaries"]["all_token_coarse_accuracy"],
          result["alt"]["compact"]["gold_boundaries"]["all_token_coarse_accuracy"], flush=True)
    print("Performance", result["performance"], flush=True)


if __name__ == "__main__":
    main()

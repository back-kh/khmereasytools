# KET-Tagger: compact supervised Khmer POS

Development, model training and tagger research are maintained in the separate
[KET-Tagger repository](https://github.com/back-kh/ket-tagger). The implementation
remains bundled in KhmerEasyTools with the same `khtag`/`KhmerTagger` interfaces.
Its source commit, file hashes and model licensing are recorded in
[`ket_tagger_source.json`](../khmereasytools/data/ket_tagger_source.json);
maintainers can run `python scripts/check_tagger_source.py` offline to verify
the bundled copy. Users do not install another package or fetch code at runtime.

`khtag` now uses a **239 KiB trained CRF model**, with pure-Python inference.
It works offline after installation, with no runtime dependency, model
download, service or GPU. Software is MIT; the bundled model and its
corpus-derived vocabulary/counts are **CC BY-NC-SA 4.0**, for research and
noncommercial use. [Model notice and full license](../khmereasytools/data/research/LICENSE.txt).
The user-approved research model is separate from the original authored
helper, still available as `model="rules"`.

## Daily use

```python
import khmereasytools as ket

assert ket.khtag("ខ្ញុំអានសៀវភៅ។") == [
    ("ខ្ញុំ", "PRON"), ("អាន", "VERB"),
    ("សៀវភៅ", "NOUN"), ("។", "PUNCT")]

for token in ket.khtag("សិស្ស៣នាក់កំពុងអាន។", with_spans=True):
    print(token.text, token.label_km, token.role, token.reason)

# Local names/domain tags; explicit overrides take priority.
tagger = ket.KhmerTagger({"និមល": "PROPN"})
assert tagger.tag("និមលអាន។")[0] == ("និមល", "PROPN")
```

Detailed records include original `text`, `start`, `end`, public POS `tag`,
Khmer `label_km`, grammatical `role`, lexical `candidates`, decision `rule` and
`reason`. Ends are exclusive Python code-point offsets into unchanged source.
Whitespace and ZWSP separators are omitted; retain original text for gaps.
No spelling correction or Unicode reordering of output text is applied.

```bash
khmereasytools tag notes.txt
khmereasytools ket-tagger notes.txt --term និមល=PROPN
khmereasytools tag notes.txt --model rules
```

Commands return UTF-8 JSON; omit the file for stdin. Python callers can select
`model="rules"` or give a local compatible gzip JSON model path. Rules mode
does not open research weights. It retains the 312-entry authored v1 lexicon
and explicit X abstention. The compact model predicts labels for unseen words;
its explanations identify those guesses. Candidates are observed lexical
alternatives, not probabilities or exhaustive analyses. No calibrated
confidence is claimed.

## Learned labels and heuristic roles

The model learns 23 native khPOS categories from human-tagged sentences.
An independent standard-library Viterbi decoder uses exported integer weights.
The 7,121-entry **training-only** vocabulary/counts also improve the tagger's
boundaries. `khseg`, its 81,005-entry dictionary and its shared frequency table
are unchanged. Default `khtag` boundaries can therefore differ from `khseg`.

Native labels are projected to the familiar 17-name POS interface: e.g. PRO
to PRON, PN to PROPN, VB to VERB, M to NOUN with classifier role. The full
mapping is in the [protocol](../benchmarks/accuracy/TAGGER_V2_PROTOCOL.md).
It is not independently validated Universal Dependencies annotation. Native
labels remain visible in explanations; Unicode token types and user tags
remain explicit overrides. The existing optional `khpos` NOVA CRF is unchanged.

Khmer roles cover negation, questions, progressive/habitual aspect, ability,
necessity, classifiers, repetition and final/discourse particles. These are
**heuristic hypotheses**, separate from learned POS. KhPOS can label a modal
VERB where the helper uses AUX; the ability role can still be useful. A
role-only adapter correction was made after inspecting authored cases; its
[amendment](../benchmarks/accuracy/TAGGER_V2_ROLE_AMENDMENT.md) and initial
results are retained. It changes no learned weight, POS label or boundary.
There is no independent fine-role gold, dependency parsing or general spelling
validation in these evaluations.

## Data and leakage controls

Source: [khPOS](https://github.com/ye-kyaw-thu/khPOS), revision
`0211405c145b0a340ad558569bd06c946b2296b4`. We found **all 1,000 CLOSE-TEST
sentences in the published training file**. Before training, normalized
unsegmented matches against CLOSE-TEST, OPEN-TEST and ALT test were purged:
1,023 rows removed. Another 52 duplicates were removed, including one
conflicting duplicate; the first original annotation is retained. Development
membership is deterministic by sentence hash.

The frozen partition has 9,827 training sentences / 106,702 tokens, 1,098
development sentences / 11,600 tokens, and 1,000 reserved CLOSE-TEST sentences
/ 10,397 tokens. Exact normalized train/dev/test overlap is zero. There are
no source document IDs: related articles/templates may remain. CLOSE-TEST
originated in published training data, so the explicit purge is essential;
this is not a new-domain test. OPEN-TEST and ALT have historical toolkit
results and are labeled as previously observed diagnostics. Their words and
counts never enter this trained model.

Two CRF L1 settings and two segmentation profiles were compared only on dev.
The selected L1=0.1 model and training-word costs were frozen before reserved
predictions. Quantization disagreed with native CRFsuite on **0/11,600 dev
tokens**; this is observed agreement, not a claim that rounding is always exact.
Native training files and corpus sentences stay outside the distribution.

## Measured accuracy

All errors and unseen-word predictions remain in denominators.

| Reserved khPOS CLOSE-TEST | Result |
| --- | ---: |
| Native 23-label POS accuracy, **gold word boundaries** | **95.94%** (9,975 / 10,397) |
| Training-word majority baseline at gold boundaries | 93.47% |
| Exact word-span F1 from unsegmented reconstruction | 91.21% |
| Joint native word/POS F1 from unsegmented reconstruction | **87.78%** |
| Public mapped POS accuracy at gold boundaries | 94.23% |
| Public mapped joint word/POS F1 from unsegmented reconstruction | 86.04% |
| Training-vocabulary coverage | 97.74% |
| Native POS accuracy on 235 unseen gold words | 76.17% |

The previously observed OPEN-TEST gives 95.83% native gold-boundary accuracy
and 88.16% joint native F1. These in-corpus figures do not establish equivalent
accuracy on arbitrary daily text, OCR errors or a new domain.

For the **same full ALT test and same lossy NOVA scoring** used for v1:

| ALT, 1,018 sentences / 26,551 whole words | V1 rules | V2 compact |
| --- | ---: | ---: |
| All-token coarse accuracy at gold boundaries | 37.61% | **81.07%** |
| Non-X answer rate | 46.80% | 100% |
| Joint coarse word/POS F1 from unsegmented reconstruction | 30.80% | **57.54%** |

100% answer rate is **not** 100% accuracy or vocabulary coverage. ALT is a
cross-corpus diagnostic with different compound/pronoun/particle conventions;
its seven classes cannot validate fine roles. The old 37.61% and new 95.94%
figures use different datasets/tagsets and are not a direct before/after pair.

Authored cases have partial assertions and are adapted development, not
independent native gold. The current adapter passes 34/37 specified cases;
initially it passed 24/37. Remaining failures and identical corpus POS/span
counts are retained in [current results](../benchmarks/accuracy/tagger-v2/results.json)
and [initial adapter results](../benchmarks/accuracy/tagger-v2/results-initial.json).
See the [partition audit](../benchmarks/accuracy/tagger-v2/partitions.json),
[frozen selection](../benchmarks/accuracy/tagger-v2/selection.json), and
[unchanged v1 results](../benchmarks/accuracy/tagger/results.json).

## Reproduce

Replay published accuracy with the bundled model, without a training package:

```bash
python scripts/evaluate_trained_tagger.py
```

This verifies/downloads only pinned text data and writes ignored replay output.
Published results and weights are preserved. For a new training experiment,
install optional `python-crfsuite`; daily inference needs none of its dependencies:

```bash
python -m pip install python-crfsuite
python scripts/train_compact_tagger.py prepare --data .evaluation/new-tagger-study
python scripts/train_compact_tagger.py train --data .evaluation/new-tagger-study
python scripts/train_compact_tagger.py evaluate --data .evaluation/new-tagger-study
python -m unittest discover -s tests -v
```

Training refuses to overwrite a frozen selection; use a new experiment folder
for a new study. Native installation and corpus-replay records are described
in [validation](VALIDATION.md). Existing OCR results, translation evaluation
status and the Word report are unchanged.

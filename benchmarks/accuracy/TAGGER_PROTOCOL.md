# KET-Tagger v1 evaluation protocol

This addition is an authored rule-based utility, not a learned competitor to
the optional CRF. The runtime lexicon and rules were written from ordinary
Khmer usage, informed by the cited annotation guidelines, before running this
corpus evaluation. No ALT/khPOS vocabulary, counts, labels or parameters may be
harvested into the distributed runtime. External datasets stay in ignored
`.evaluation`. Do not change OCR evidence or the report's frozen results.

## Authored development cases

`tests/fixtures/tagger_cases.json` contains 37 authored examples. They exercise
specified word/POS pairs or selected roles, not full gold annotations for every
case. These are development assertions, not held-out accuracy, native review,
or evidence of research novelty. The initial 36-case run exposed a compound
boundary failure for `នៅផ្ទះ`; retain its unmet target and observed abstention,
and add a separately spaced variant to isolate the lexical rule. Functional
tests can assert that known current behavior while the evaluation still counts
the linguistic target as failed. Do not change expected targets to match output.

## Full external corpus check

Use the same pinned ALT Khmer test split and independently tested whole-word
NOVA adapter as the earlier improvements comparison: 97 articles, 1,018
sentences, 26,551 word-level gold tokens. Verify the original archive, split,
and extracted annotation bytes against the existing pinned download. Evaluate
all sentences; do not select words/sentences based on known vocabulary.

ALT is CC BY-NC-SA 4.0, used only for this research evaluation. No corpus text
or predictions will be redistributed. Save derived counts, source hashes and
mapping policy. The new authored cases and code remain under the package MIT
license. No training or tuning on this test split is authorized by this protocol.

NOVA has seven broad classes; it cannot validate our fine POS/particle roles.
Freeze this explicitly lossy, heuristic projection before scoring:

| KET-Tagger | NOVA proxy |
| --- | --- |
| NOUN, PROPN, PRON | n |
| VERB | v |
| ADJ, DET | a |
| ADV, ADP, AUX, CCONJ, SCONJ, PART | o |
| NUM | 1 |
| PUNCT | . |
| INTJ, SYM | + |
| X | X (abstention, always wrong against gold) |

Exception: `role="copula"` projects to `v`, consistent with the ALT copula
convention. NOVA's possessive-pronoun, adjective/adverb and weak-particle
conventions still differ. This is a coarse compatibility diagnostic, not a
fine-grained POS accuracy claim or comparison of equivalent tagsets.

Report both:

1. **At gold word boundaries:** tag all gold words using the internal span
   adapter; report all-token coarse accuracy with X counted wrong, coverage
   (non-X/all), accuracy conditional on a non-X answer, and confusion counts.
   Include a separate lexical-only denominator (gold n/v/a/o) to show how
   punctuation/numbers affect scores. Never headline selective accuracy alone.
2. **From reconstructed unsegmented text:** concatenate compact gold words
   under the established NFC/whitespace/ZWSP scoring projection; report exact
   span segmentation F1 and joint coarse word/tag F1. All predicted words,
   including X, count in denominators. Verify exact input coverage before
   accepting spans; alignment failures score zero intersections.

The optional `--with-crf` check runs the actual installed model at the same
gold boundaries and on the same reconstructed strings. It is a reference
utility comparison, with different tagsets and possible ALT training overlap;
it does not establish a fair held-out model ranking. Record the model hash.

Corpus scores are observations, not pass/fail thresholds. Functional tests,
native installed-wheel checks, and linguistic evaluation are separate evidence.
If runtime changes after observing scores, label any repeated corpus run as
adapted development and preserve earlier results.

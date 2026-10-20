# KET-Tagger v2: compact supervised research model

Frozen before v2 training or accuracy predictions, 2026-10-20. The user
explicitly accepts research/noncommercial weights. Software stays MIT;
corpus-derived weights, word counts and lexical features remain separately
CC BY-NC-SA 4.0, with attribution. No test vocabulary/counts enter the model.
Preserve all v1, OCR and Word-report results. V1 runtime is commit 325c1c5.

## Sources and partitioning

Use khPOS revision 0211405c145b0a340ad558569bd06c946b2296b4, train6 word/tag,
CLOSE-TEST and OPEN-TEST, plus the previously pinned ALT test for a separate
cross-corpus diagnostic. Inputs are checksum-pinned in the fetch/prepare script.
KhPOS has 23 observed native labels. Use its gold labels, not model-generated
annotations. Word-internal `_`, `~` and their escaped forms are annotation
markers removed under the existing repository projection; then NFC and removal
of whitespace/ZWSP define the matching key. Preserve source row identifiers.
Reject malformed word/tag alignment; do not silently drop scoring examples.

Inspection before predictions found all 1,000 CLOSE-TEST sentences in the
12,000-row training file (1,012 matching training rows), plus 12 OPEN-TEST
matches. CLOSE and OPEN share one sentence. Purge training by normalized
unsegmented sentence text against **all CLOSE, OPEN and ALT test strings**.
Deduplicate remaining training by the same key, retaining the first original
row deterministically; count conflicting annotations. Select development by
SHA-256 of `ket-pos-v2-dev\0` plus the normalized string, first eight hex
digits modulo 10 equal to zero. All other rows train. Never retrain on dev or
test after selection. Keep manifest hashes, row IDs and overlap audits.

Primary reserved evaluation: all 1,000 CLOSE-TEST sentences (10,397 tokens).
These were not previously scored by this toolkit but originated in published
training data; the explicit purge is essential. OPEN-TEST (1,000 / 10,778)
and ALT (1,018 / 26,551 whole words) have historical measurements, so describe
them as previously observed diagnostics, not newly unseen benchmarks. There
are no source document IDs for khPOS; sentence deduplication does not exclude
related articles or templates. Disclose that remaining generalization limit.

## Candidate family and selection

Train a linear-chain CRF on the retained training partition using Python
CRFsuite only at build/evaluation time. Runtime inference is an independent
standard-library linear-chain Viterbi implementation. No torch, numpy,
sklearn, CRFsuite, internet connection or download is needed for daily use.
Features: bias, normalized word, script/number shape, bounded length, first
and last 1/2/3 code points, Khmer nominal-prefix indicators, adjacent +/-1/2
normalized words, adjacent shapes, BOS/EOS. These feature strings do not
change source text or output offsets. Candidate L1 coefficients: 0.1, 0.5;
L2 0.1; L-BFGS up to 100 iterations; all possible transitions enabled.

Export native weights as bounded gzip JSON with integer weights at scale
1,000. Evaluate native-versus-exported prediction agreement on development;
retain and report any differences, rather than calling quantization exact.
Model files must be <= 2 MiB compressed. Runtime validates schema, dimensions,
finite/bounded weights, size, metadata and checksums; no pickle or execution.

Compare two segmentation profiles on development: existing frequency decoder;
and a model-local frequency decoder using **training-only** word counts and
the existing structurally safe boundary rules. Model-local vocabulary must
not mutate the shared 81,005-entry dictionary or khseg behavior. Choose the
(L1, segmentation) pair with highest development joint native word/tag F1;
tie-break by gold-boundary native accuracy, then smaller model, then original
profile ordering. Do not inspect reserved predictions before this choice.

The model-local profile considers the union of the existing dictionary and
training vocabulary, with add-0.1 smoothed training word costs. Dictionary-only
words use the unseen-word cost. No development/test word changes this index.

## Reporting and public labels

Report native 23-label accuracy at gold boundaries as the primary POS metric,
plus exact segmentation and joint native word/tag F1 from reconstructed text,
unseen-word accuracy, training-lexicon coverage, all-token answer rate, per-tag
counts and alignment failures. Keep all words in denominators. Include the
training-only majority-word baseline with global-majority backoff. Compare
v1 rules versus v2 public output on a separately documented fixed projection.

Native-to-public mapping: AB/NN/M->NOUN, AUX->AUX, CC->CCONJ, CD->NUM,
DBL/PA/QT->PART, DT->DET, ETC/RB->ADV, IN->ADP, JJ/VB_JJ->ADJ, KAN->PUNCT,
PN->PROPN, PRO/RPN->PRON, SYM->SYM, UH->INTJ, VB/VCOM->VERB. Existing authored
negative-marker forms under RB map to PART as a documented interface choice.
This is a projection, not independent UD gold. Khmer roles remain heuristic;
native model labels are retained in explanations. User overrides take priority.

ALT comparison uses the frozen v1 NOVA proxy; report this lossy compatibility
diagnostic separately, including adjective/pronoun conventions. It cannot
validate the fine Khmer roles or establish equivalence between tagsets.

After dev selection, freeze the selected model and selection manifest before
scoring CLOSE/OPEN/ALT. No accuracy-driven modifications afterwards. Repeat
runs after any such change become adapted development and preserve earlier
reports. Measure compressed size, cold/warm latency and process memory as
local diagnostics. Test fresh core and extras wheel installations on Windows,
macOS and Linux, including real existing OCR/CRF, with licensed model notices.
Passing software checks is separate from measured linguistic accuracy.

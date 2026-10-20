# Supplementary cross-corpus POS proxy

Frozen after ALT results but before any khPOS tagging predictions, 2026-10-18.

Use all 1,000 khPOS OPEN-TEST sentences and original gold word boundaries;
remove compound _/~ markup exactly as in the existing segmentation benchmark.
Use the complete sentence as CRF context. Do not train or tune any model.

Before prediction, restrict comparable gold labels to this four-tag mapping:
NN (common noun) -> n; PN (proper noun) -> n; VB (verb) -> v;
KAN (full stop) -> ".". All other gold categories remain unscored because
their contextual use and the ALT NOVA categories need linguistic adjudication.
The mapping follows the upstream khPOS README definitions and the official
NOVA guidelines (nominal tokens include common/proper nouns).

Report the number/proportion of gold tokens covered by this proxy, oracle
gold-token tag accuracy, per-category accuracy, and an always-noun baseline
on the same restricted subset. For public khpos on concatenated unspaced
input, report exact-boundary recall and exact-boundary-plus-tag recall for
that gold subset. Do not call this partial-coverage result overall POS F1.

The source corpus differs from ALT, but training-instance deduplication and
the backend tokenizer's split have not been audited. This is a cross-corpus,
cross-annotation proxy with possible lexical/document overlap, not a verified
fully held-out POS benchmark.

Upstream source revision: 0211405c145b0a340ad558569bd06c946b2296b4.
License: CC BY-NC-SA 4.0, evaluation only, excluded from distributions.

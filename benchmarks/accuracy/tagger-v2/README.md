# Compact KET-Tagger research evidence

- `partitions.json`: pinned sources, original row IDs, exact-text overlap purge,
  duplicate/conflict counts and deterministic training/development membership.
- `selection.json`: four development comparisons, quantization agreement,
  model sizes and frozen chosen model SHA-256, before reserved scoring.
- `results-initial.json`: initial reserved/public evaluation, including 24/37
  authored assertions before the documented role-only adapter correction.
- `results.json`: current native/public metrics, v1 comparisons, remaining
  authored failures and a check that the role correction changes no corpus
  POS/span count. Corpus data and full external predictions are not included.

The frozen [training protocol](../TAGGER_V2_PROTOCOL.md) and later
[role amendment](../TAGGER_V2_ROLE_AMENDMENT.md) distinguish model selection,
reserved scoring and adapted authored development. Source corpus: khPOS by
Vichet Chea and Ye Kyaw Thu, revision 0211405c145b0a340ad558569bd06c946b2296b4,
under CC BY-NC-SA 4.0. ALT is a separate, previously observed coarse diagnostic.
The model is separately licensed and attributed in `khmereasytools/data/research`.

Report native gold-boundary accuracy together with unsegmented joint span F1.
Do not equate khPOS's 23-label results with the lossy ALT projection or interpret
100% answer rate as correctness. Source document IDs are unavailable, so exact
sentence purging does not establish separation of related articles/templates.

Native installed-wheel corpus replays download only pinned test annotations
outside the checkout, and compare all counts with these frozen references.
They require no native POS/ML package. The existing optional OCR/CRF checks
remain part of the separate all-extras installation tests.

# Accuracy evaluation protocol

Frozen before running model predictions, 2026-10-18. Runtime baseline:
9e5e39738e630b3e17789ab20c46061c99ce1a07. This is an engineering evaluation,
not a claim of a representative population sample. No dataset vocabulary,
correction rules, or model weights enter the runtime package.

- OCR: all 60 KHOB level-1 page images in the 2026-01-31 archive (15
  underlying documents, four correlated acquisition variants). Use public
  khanalyze defaults: Khmer, PSM 3, no preprocessing, engine reading order,
  all confidence >= 0, segmentation disabled because it does not alter text.
  Reference labels remain in annotation-array order. Decode literal backslash-t
  to tab. Report micro code-point CER after NFC and removal of whitespace/ZWSP;
  additionally report whitespace-folded CER and whitespace-unit error rate.
  Whitespace units are not linguistic Khmer words. CER may exceed 100%;
  neither 1-CER nor Tesseract confidence is document accuracy.
- Layout diagnostic: compare OCR line rectangles with axis-aligned envelopes
  of labeled polygons, deterministic descending-IoU one-to-one matching at 0.5.
  Scale annotation coordinates by actual image / metadata dimensions when
  different. This is a box proxy: it does not evaluate semantic layout,
  exact polygons, tables, columns, or independently verified reading order.
- Recognition diagnostic: exactly four evenly spaced annotation indices
  per page, floor(j*N/4), j=0..3 (240 crops). Scale coordinates as above,
  crop each envelope with 2px padding, PSM 7, no resizing/preprocessing.
  This gives the recognizer gold regions and must remain separate from
  full-page performance. Crops may contain annotation noise or multiple lines.
- PDF transport: embed all 15 physical scanner images (task 3), losslessly,
  in annotation filename order, at 200 DPI in one image-only PDF. Analyze
  the complete PDF at default 200 DPI. This is a derived PDF transport test,
  not a separate independent PDF benchmark.
- POS: all 1,018 sentences from the official ALT article-based test IDs.
  Parse NOVA leaf tags (ignore compound-parent tags; remove leaf suffix "-").
  Compare seven coarse labels without mapping into Universal Dependencies.
  Join gold words into unspaced input. Report public khpos exact-token and
  exact-token-plus-tag span F1, direct backend on raw input, and CRF accuracy
  with oracle gold tokenization; include a majority-noun oracle baseline.
  Ignore whitespace/ZWSP only in span alignment; text-changing outputs are
  counted as alignment failures with zero correct spans, never silently dropped.
  The backend was trained on ALT and its exact split membership is unavailable;
  these scores may contain training overlap and are not held-out generalization.
- Sentences: reconstruct all 97 ALT test articles in original sentence order
  by joining unspaced gold sentences with one ASCII space. Score internal
  sentence-end boundaries (exclude forced article-end), exact sentence spans,
  and exact articles. This is a reconstruction from sentence annotations,
  not the original document typography.
- Challenge cases: author expected outputs before examining predictions;
  score sentence boundaries/spans and extraction (kind,start,end) precision/
  recall plus normalized-value correctness. Include negative and adversarial
  cases. These cases are authored by the implementing agent and do not supply
  independent native-speaker gold or production frequency estimates.
- Translation: pending by user choice; no provider calls or quality score.
  Existing local HTTP tests validate the client protocol only.

Report hashes, engine/model versions, source fingerprint, totals, errors and
limitations. Keep full external references/predictions in ignored .evaluation;
commit aggregates and authored challenge data only. Any changes made after
seeing results must be labeled adapted development results, not untouched
held-out evaluation. External sources and licenses are linked in the final guide.

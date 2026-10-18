# Historical accuracy baseline, 2026-10-18

These results describe the earlier defaults. See [the current paired
improvements](IMPROVEMENTS.md) for frequency-based segmentation, direct POS
tagging, OCR preprocessing and the corrected whole-word POS comparison.

OCR and POS execute successfully, but their output needs review. Passing
installation tests is not proof of linguistic accuracy. These measurements
use real public documents and annotated text, plus clearly labeled authored
cases. They concern unreleased 0.5.0.dev0 source, not published PyPI 0.4.0.
Core runtime dependencies remain empty; benchmark dependencies are optional.
Accuracy measurements here ran on macOS. Windows/macOS/Linux CI separately
checks installation and actual backend integration, not the full corpora.

## Results

| Check | Sample | Observed result | Practical limit |
| --- | --- | --- | --- |
| Full-page OCR, defaults | 60 KHOB images: 15 documents in four variants | 18.07% micro code-point character error rate (CER); 0/60 exact pages | Requires proofreading; variants are correlated |
| OCR through PDF input | 15 physical scans embedded losslessly in one image-only PDF | 15.77% CER; all 15 pages processed | Derived transport test, not a separate PDF corpus |
| Public segmentation + POS | 1,018 ALT sentences / 36,007 tokens | 69.38% exact-token F1; 67.37% exact-token-and-tag F1 | Model trained on ALT; split overlap unknown |
| POS with oracle gold words | Same ALT sample, actual installed CRF | 96.23% tag accuracy; noun baseline 41.72% | Gold boundaries hide segmentation errors; possible training overlap |
| Cross-corpus POS proxy | 1,000 khPOS sentences; 5,975 mapped tokens (55.44% coverage) | 92.95% oracle tag accuracy; noun baseline 72.45%; public joint recall 76.20% | Four-category mapping only; not overall POS F1 |
| Sentence boundaries | 97 reconstructed ALT articles / 1,018 sentences | 99.51% internal-boundary F1; 90/97 exact articles | Gold sentences joined by artificial spaces; original typography unavailable |
| Sentence challenges | 40 agent-authored Khmer/mixed cases | Baseline 36/40 exact; after initials fix 37/40 | Development cases, not independent gold |
| Extraction challenges | 50 agent-authored cases including negatives | Baseline 49/50 exact; after phone fix 50/50; all 50 gold entities and values match | Adapted development result, not production precision/recall |
| Live translation | User elected to keep pending | No provider requests or quality score | HTTP fixture tests validate the client only |

### OCR

Configuration: Tesseract 5.5.2, Khmer fast model, PSM 3, no preprocessing,
engine reading order, confidence minimum 0. Segmentation is disabled because
it does not change OCR text. Language-data SHA-256:
47f110575341b322052f3becbefee61a3ecf1ef549352b5d4d33d28afe30d099.

| Acquisition | Pages | Compact code-point CER |
| --- | ---: | ---: |
| Clean PDF exports, task 1 | 15 | 12.58% |
| Messenger compression, task 2 | 15 | 21.88% |
| Physical scanner, task 3 | 15 | 15.62% |
| Scanner app, task 4 | 15 | 22.09% |

There are 20,825 Levenshtein edits against 115,223 reference code points.
Scoring applies NFC and removes whitespace/ZWSP; it does not correct spelling
or reorder Khmer marks. Labels decode literal backslash-t and retain annotation
order. Whitespace-folded CER is 18.12%. A supplementary whitespace-unit error
rate is recorded, but Khmer spaces usually separate phrases, so this is not
linguistic word error rate. CER is an edit rate, not a percentage of correct
documents. Tesseract confidence is not a calibrated probability.

Annotation metadata dimensions differ from actual images on 27/60 pages.
Scaling coordinates fixes dimensions, but visual inspection of goc_3 scans
still shows residual alignment errors. Box-IoU and the 240 sampled crop scores
are diagnostics only: crops may cut text or include adjacent lines. Their
36.89% aggregate crop CER is not a valid isolated recognizer-accuracy claim.
Semantic layout, tables, column order, and handwriting accuracy remain
unmeasured. Full-page CER is independent of crop coordinates, but still
depends on label spelling, completeness, and unverified reading order.

### POS

The actual backend is khmer-nltk 1.6, with seven coarse NOVA labels:
n, v, a, o, 1, "." and "+". These are not Universal Dependencies labels.
The adapter removes compound-parent tags and leaf-tag suffix hyphens.
All 20,106 ALT sentences have matching leaf/token counts. NFC changes zero
ALT word tokens.

Oracle scoring supplies gold words directly to the installed CRF. Public
scoring calls khpos on unspaced gold text and checks exact start/end/tag triples
after ignoring whitespace/ZWSP. No alignment failures occurred. The backend
also returns 30,799 whitespace pairs, excluded from linguistic token counts.
No model training or runtime POS change was made.

Direct backend tagging of raw input scores 64.61% joint F1 versus the public
wrapper's 67.37%. This comparison follows ALT's morpheme-oriented annotations;
it does not make compound boundaries universally wrong. The backend was
trained on ALT and exact membership is unavailable. The official test split
therefore cannot be claimed held out from this model.

The khPOS proxy maps only NN/PN to n, VB to v, and KAN to ".". It retains full
sentence context but leaves other categories unscored because contextual
mapping requires linguistic adjudication. Joint recall is 4,553/5,975 mapped
gold tokens, not precision/F1 across all categories. Training-instance
deduplication and the backend tokenizer's split remain unaudited.

### Fixes and remaining heuristics

Baseline results are preserved. Consecutive initials such as "T. P. Jones"
no longer split a sentence. A phone before a sentence-ending period and a
following year is now extracted; overly long sequences are still rejected.
Separate regression examples cover both fixes.

The challenge suite was rerun after fixes, so improved scores are adapted
development results. Abbreviations at sentence ends ("U.S.", "etc.") can
still merge sentences, and an internal ellipsis can split one. Extraction
recognizes common patterns, not full RFC syntax, active contacts, semantic
dates, or general named entities. Fifty authored successes do not establish
production precision/recall.

## Reproduce

The harness needs Python 3.9+ and optional OCR/POS dependencies, plus Tesseract
and khm. Measurements used macOS arm64, Python 3.9.6. Use a maintained Python
for new environments; core compatibility is unchanged.

~~~bash
python -m pip install '.[all]'
python -m pip install -r requirements-evaluation.txt
# Review independent dataset licenses before fetching:
python scripts/fetch_accuracy_data.py
python scripts/evaluate_accuracy.py pos pos_proxy sentences challenges ocr
KET_RUN_OCR_TESTS=1 KET_RUN_POS_TESTS=1 python -m unittest discover -s tests -v
~~~

Accuracy checks never call translation. Downloads are SHA-256 pinned;
evaluation is offline. Full external references/predictions stay in ignored
.evaluation, outside Git/packages. Aggregates, baseline/adapted measurements,
source fingerprints and authored cases are in
[benchmarks/accuracy](../benchmarks/accuracy/README.md).
The [main protocol](../benchmarks/accuracy/PROTOCOL.md) and
[cross-corpus protocol](../benchmarks/accuracy/KHPOS_PROXY_PROTOCOL.md)
were each frozen before their predictions. Metric tests independently check
edit counts and one-to-one box matching.

## Sources and licenses

- [KHOB by EKYC Solutions and collaborators](https://github.com/EKYCSolutions/khmer-ocr-benchmark-dataset):
  level-1 archive updated 2026-01-31, upstream MIT notice. Government documents
  and correlated variants do not represent all daily documents.
- [NICT Asian Language Treebank](https://www2.nict.go.jp/astrec-att/member/mutiyama/ALT/):
  Khmer annotations dated 2018-11-01, CC BY-NC-SA 4.0. Credit NICT/NIPTICT
  and Riza et al., "Introduction of the Asian Language Treebank"
  (Oriental COCOSDA, 2016). The separate parallel translation corpus is not used.
- [NOVA guidelines by Ding, Kaing, Utiyama, Chea and Sumita](https://www2.nict.go.jp/astrec-att/member/mutiyama/ALT/Khmer-annotation-guideline.pdf)
  and [khmer-nltk POS documentation](https://github.com/VietHoang1512/khmer-nltk/blob/2228cfb8f02d3f0ce0969cb69583f33a08a9216f/khmernltk/pos_tag/README.md)
  establish annotation definitions and the upstream ALT training notice.
- [khPOS by Ye Kyaw Thu and Vichet Chea](https://github.com/ye-kyaw-thu/khPOS/tree/0211405c145b0a340ad558569bd06c946b2296b4):
  OPEN-TEST, CC BY-NC-SA 4.0. Credit Thu, Chea and Sagisaka, "Comparison of
  Six POS Tagging Methods on 12K Sentences Khmer Language POS Tagged Corpus"
  (ONA, 2017). The proxy uses published tag definitions.

Noncommercial corpora are used for research evaluation only here, without
incorporating data, vocabulary, frequencies or model weights into the package.
For stronger release claims, obtain independently reviewed daily-document
annotations, POS data with confirmed training exclusion and reconciled
tagsets, corrected layout annotations, and an explicitly configured provider
evaluation. Live translation remains pending as requested.

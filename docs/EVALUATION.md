# Segmentation evaluation

## Protocol and source

The fixed algorithm was evaluated on **1,000 sentences / 10,778 gold tokens** from [khPOS OPEN-TEST](https://github.com/ye-kyaw-thu/khPOS/blob/0211405c145b0a340ad558569bd06c946b2296b4/corpus-draft-ver-1.0/data/OPEN-TEST.word), revision `0211405c145b0a340ad558569bd06c946b2296b4`.

Corpus SHA-256: `1b10b866263e6beb93cbf5c249ffc6a5d4d11dbc7beb90717c9f4e14cb152869`.

The corpus authors describe manual segmentation and POS annotation. Its [upstream license notice](https://github.com/ye-kyaw-thu/khPOS/blob/0211405c145b0a340ad558569bd06c946b2296b4/README.md) is CC BY-NC-SA 4.0. It is used here for noncommercial research evaluation only and is excluded from Git/distributions. Reusing it requires complying with its own terms. No words, frequencies, model weights, or correction rules are extracted from it into the library.

The adapter splits each gold line on whitespace, removes its `_`/`~` compound markup (including escaped forms) and ZWSP inside gold words, and concatenates the resulting words into an unspaced input. A predicted token is correct only when both its start and end equal a gold token's boundaries. Scores are micro-averaged over all sentences. Punctuation and numbers count as tokens. Every tokenizer must reconstruct exactly this input before it can be scored.

| System | Precision | Recall | Exact-token F1 | Exact sentences |
| --- | ---: | ---: | ---: | ---: |
| 0.4 `khseg`, 213 entries | 32.17% | 6.49% | 10.81% | 1 / 1,000 |
| 0.4-style lossless greedy, 213 entries | 38.85% | 25.03% | 30.45% | 9 / 1,000 |
| Expanded greedy, 81,005 entries | 74.57% | 78.29% | 76.39% | 387 / 1,000 |
| Expanded maximum coverage | 75.49% | 79.01% | 77.21% | 386 / 1,000 |

The old `khseg` fallback consumed the rest of an unknown Khmer run, explaining its particularly low recall. The new dictionary supplies most of the gain. Global decoding adds about **0.82 F1 percentage points** over expanded greedy matching; it does not dominate every metric (one fewer exact sentence).

## Interpretation

This is a single-corpus engineering comparison, not proof of universal accuracy, novelty, or superiority over trained Khmer segmenters. No model-based external baseline was run. Gold compound conventions may disagree with application preferences or ICU line-breaking entries. This test does not assess OCR noise, Unicode spelling variants, language identification, or downstream search quality. Do not describe 77.21 F1 as “77.21% of all Khmer text is correct.”

The decoder has no learned weights: minimize unknown Khmer code points, then the final number of tokens. Unit tests compare this objective with exhaustive search on small generated examples. No evaluation-set tuning or dictionary additions were performed. Runtime timings in the JSON are diagnostic only; cache state differs between successive variants, so they are not fair throughput comparisons.

Machine-readable measurements are in [benchmarks/khpos_open_test.json](../benchmarks/khpos_open_test.json). Reproduce only if authorized to use the corpus under its noncommercial terms:

```bash
python scripts/fetch_evaluation_data.py
python scripts/benchmark_segmentation.py .evaluation/OPEN-TEST.word --khpos --output benchmarks/khpos_open_test.json
```

## Migration

`khseg(text)` and `khfilter(text)` now use the expanded lexicon and coverage decoder by default. Their signatures remain convenient, but **token boundaries change intentionally**. Unknown runs no longer swallow later recognized words. Numbers, punctuation, and text boundaries are handled through the span tokenizer. Custom vocabulary is accepted per call.

For frozen old pipelines, use `khseg(text, dictionary="legacy", strategy="legacy")` and the corresponding `khfilter` options. `khseg_spans` remains lossless and offers `strategy="longest"` plus either lexicon for comparisons. `khsyllable` is unchanged. Stable downstream annotations should not be resegmented automatically.

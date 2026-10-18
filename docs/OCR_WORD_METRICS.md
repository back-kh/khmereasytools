# OCR word metrics and historical failures

The [added metric report](../benchmarks/accuracy/ocr-word-errors/results.json)
uses the original frozen predictions. It does not rerun OCR, repair references,
remove repetitive output or clip error rates. It checks 8,736 predictions using
26,208 independent distance computations, after 1,039 dynamic-programming
self-checks of the independent bit-vector implementation. Counts and S/D/I are
retained privately; the public file gives aggregates, provenance hashes and audit
coverage. The original CER reports remain unchanged.

## What WER means here

All three rates are sums of minimum edit counts divided by sums of reference
units. Empty and failed predictions retain the reference denominator. Rates
can exceed 100 percent when insertions are numerous.

- Compact CER: NFC followed by removing Unicode whitespace and U+200B. Unit:
  Python Unicode code point, not a Khmer visual character or grapheme cluster.
- Whitespace-unit WER: NFC, treat U+200B as a space, then `str.split()`. Khmer
  spaces often separate phrases, so these units are not annotated words. This
  explicit U+200B policy differs from the older whitespace diagnostic.
- Segmentation-assisted WER: run the same pinned default frequency-based
  `khseg_spans` decoder on NFC reference and prediction, discard whitespace and
  boundary spans, retain punctuation, case and digits. This depends on the
  toolkit's imperfect dictionary segmentation; it is not human-gold word WER.

Neither token metric substitutes for CER. Independent human word boundaries
would be needed for a stronger linguistic word-accuracy claim. The scorer's
S/D/I are one optimal alignment; ties can yield other equally optimal
decompositions with the same total edit count. The metric convention follows
minimum edit distance, as used in [JiWER](https://github.com/jitsi/jiwer).

## Scene text and printed pages

Percent error; lower is better. KET-OCR is the Khmer Easy Tools preparation and
document pipeline using the same Tesseract recognizer, not a new recognition
model. Degraded images are derived versions and add no independent documents.

| Collection | Images or crops | System | CER | Whitespace-unit WER | Segmentation-assisted WER |
|---|---:|---|---:|---:|---:|
| KhmerST original crops | 3,563 | Tesseract fast | 67.07 | 106.41 | 100.54 |
| KhmerST original crops | 3,563 | KET-OCR | 65.74 | 106.91 | 101.78 |
| KhmerST half-size JPEG40 | 320 | Tesseract fast | 71.84 | 102.73 | 97.31 |
| KhmerST half-size JPEG40 | 320 | KET-OCR | 67.60 | 107.52 | 98.09 |
| KHOB original page images | 40 | Tesseract fast | 16.59 | 60.04 | 45.65 |
| KHOB original page images | 40 | KET-OCR | 10.68 | 52.04 | 39.38 |

KET-OCR reduces CER on these samples but **does not improve either added WER
on KhmerST**. With frequent missing and wrong words, scene-text recognition
remains poor. The mostly insertion-driven historical failure has a different
error pattern: KhmerST's original crop errors are mainly deletions, including
empty output (994 Tesseract, 964 KET-OCR crops in the original report).

## Why historical CER exceeds 500 percent

On all 150 historical palm-leaf pages, the reference has 67,487 compact code
points. The audit decomposes the unchanged primary edit count as follows.

| System | Substitutions | Deletions | Insertions | CER | Insertions as share of edits |
|---|---:|---:|---:|---:|---:|
| Tesseract fast / KET-OCR | 21,770 | 43,227 | 409 | 96.92% | 0.63% |
| Surya 2 GGUF first pass | 58,149 | 1,010 | 310,793 | 548.18% | 84.01% |
| PaddleOCR-VL 1.6 MLX 4-bit | 47,847 | 19,640 | 298,027 | 541.61% | 81.54% |
| DeepSeek-OCR MLX 4-bit | 57,196 | 9,391 | 475,615 | 803.42% | 87.72% |

These are unacceptable recognition results for transcription use. The ratios
are mathematically valid: the numerator can exceed the reference length when
an output invents or repeats large amounts of text. Existing
[length and eightgram diagnostics](../benchmarks/accuracy/document-ocr/generation-diagnostics.json)
also show repetitive, often capped generations. This is evidence of generation
failure under the recorded profiles, not proof that every implementation or
checkpoint of these model families must fail. It does not demonstrate useful
historical OCR, and WER does not rescue the result.

The Qwen comparison remains restricted to the same 30 official historical test
pages; see the metric JSON for its separate S/D/I and WER counts. No matched
150-page Qwen result is claimed. Modern KH-FUNSD business images use a separate
new protocol and are not combined with these historical results.

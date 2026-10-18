# KH-FUNSD operational-reference comparison

This is a new experiment. It does not replace the frozen historical or scene-text results.

## Inputs and references

The author identifies the supplied 148 image files as KH-FUNSD. Exact source-image
deduplication leaves 146 pages: 96 receipts, 34 invoices and 16 quotations. We do
not infer a mapping to all 158 documents described by the public dataset paper.
Folder labels Digital/Scanned are acquisition strata, not verified capture types.

At the author's instruction, the 146 existing Codex-generated transcripts are
the operational ground truth for this comparison. They are machine-generated
and have not been independently reviewed. Results measure agreement with these
references, not verified human transcription accuracy. Keep all original review
flags false. Freeze original transcript hashes and image hashes before inference.
Do not edit a transcript after seeing a prediction. Retain all pages, including
uncertainty: the literal `[ILLEGIBLE]` marker stays in the primary reference.
Also report the predefined subset without this marker as a sensitivity analysis;
it is neither an easier replacement benchmark nor certified human ground truth.

All five primary systems process the same 146 upright RGB PNGs. Two Qwen models
process the same fixed 30-page subset. Choose this subset by proportional largest
remainder allocation over category x acquisition-folder strata, with hash order
`khmereasytools-business-ocr-20261018/` plus page ID within each stratum. Freeze
the selected IDs before any prediction. No reference text reaches GPU inference.
Source images, generated transcripts and predictions remain private.

## Recognition profiles

Reuse the existing pinned model bytes and installed runtime from the historical
experiment; retain its results unchanged. Tesseract: fast khm+eng, OEM 1, PSM 3,
one OpenMP thread/call, four CPU workers, 240 second timeout. KET-OCR is the
KhmerEasyTools image preparation and document pipeline using this same Tesseract
recognizer: auto preparation, engine reading order, no segmentation or confidence
filter. KET-OCR is a pipeline name, not a newly trained recognition model.

Surya 0.22.1: existing GGUF plus projector, native high-accuracy bounding-box prompt,
first pass only, batch/parallel 4, greedy temperature 0, top_p 0.1, 4096 output
tokens, 240 seconds, no retry or regeneration. Use the existing native transport.
PaddleOCR-VL-1.6 4-bit and DeepSeek-OCR 4-bit: existing MLX-CUDA checkpoints,
native single-image chat templates, respectively `OCR:` and `Free OCR.`, temperature
0, 4096 tokens, 240 seconds, seed 20261018, batch 1, 16 GiB per-process allocation.
Qwen2.5-VL-3B and Qwen3-VL-2B: existing BF16 SDPA checkpoints, original literal
transcription prompt, 112896..1003520 native image pixels, greedy 4096 tokens,
240 seconds, seed 20261018, batch 1, allocator fraction 0.2. No prompt tuning,
repetition penalty changes, truncation, deduplication, retry or selective rerun.
GPU 2 is shared with unrelated work. No speed comparison is justified across hosts.

Record a separate immutable environment identity for each execution backend,
including imported adapter hashes, dependency versions, images, model inventory,
framework inventory where applicable, and this protocol. Verify cache provenance
on resume. Count errors and empty/capped predictions; include failed pages in
the full reference denominator. Keep any partial output returned by the adapter.

## Scoring

Retain the original compact CER: NFC, then remove Unicode whitespace and U+200B;
unit-cost Levenshtein edits divided by reference code points. Strip only the
existing serializer markup from neural outputs with `visible_text`. Do not strip
repeated recognized words. Tesseract/KET outputs are plain text.

Add two explicitly named token metrics to every OCR collection: (1) whitespace
unit WER, using NFC, U+200B treated as a space, and `str.split()`; (2)
segmentation-assisted WER, using the identical bundled frequency-based
`khseg_spans` decoder, expanded dictionary and frequency table for reference and
prediction, excluding whitespace and boundary spans, retaining punctuation,
case and digits. Pin the decoder and lexicon hashes. Neither is human-annotated
Khmer word WER. CER and both WERs are micro-averages of total edit counts over
total reference units. They can exceed 100 percent; never cap them. Report
S/D/I from a minimum edit alignment; ties may produce different optimal S/D/I
decompositions, but total edits must match an independent distance computation.
Report full 146 and matched 30 separately, category/acquisition breakdowns and
the marker-free sensitivity subset. Do not compare Qwen30 against unmatched146.

For historical CER over 100 percent, add a posthoc S/D/I and output-length audit
without changing original scores. For KhmerST, add both token metrics to all
3563 original crops and the separate 320 degraded crops using cached predictions.
These added metrics are not evidence of a new recognition improvement.

Translation and KhmerRAG are functional interfaces. Translation quality and
end-to-end RAG answer quality are outside this OCR experiment.

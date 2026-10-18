# Full page Khmer OCR comparison protocol

This protocol is fixed before predictions on any new evaluation page. Runtime
code remains the installed 0.5.0.dev0 wheel previously evaluated, whose Python
source bytes match b062be0. No OCR model is trained or fine-tuned in this study.

## Sources and selection

- **Historical stress test:** 150 complete palm-leaf page images from the
  SleukRith subset of `stanford-oval/churro-dataset`, pinned at
  `cbeaba69179d5de122fbbc9e97b2a7d97942f688`. The complete released Khmer inventory
  has 622 pages: 562 train, 30 development and 30 test. Select all 30 official
  test pages and the first 120 train pages ordered by SHA-256 of UTF-8
  `khmereasytools-document-ocr-20261018/` plus `example_id`. Do not use the
  development split. The 120 source-train pages are an external evaluation for
  this untrained toolkit; they are not presented as CHURRO's official test set.
- Fetch the pinned Hugging Face viewer JPEGs, verify their embedded revision and
  advertised dimensions, apply EXIF orientation, and convert to RGB PNG. These
  are viewer-delivered page images, not certified byte-identical original
  SleukRith scans. No line crops, supplied polygons, text-only masks, synthetic
  degradations, manual perspective correction or reference-informed processing.
- Use the released `original_transcription` verbatim. Do not score generated
  `cleaned_transcription` XML descriptions or metadata. Record transcript and
  input-image hashes before inference. All 150 selected input hashes and raw
  reference hashes must be distinct.
- **Modern printed candidates:** 11 Khmer Wikisource pages marked proofread
  level 3 were acquired with pinned reference revisions and original PDF
  hashes. Exclude this entire collection from numerical scoring before
  inference: visual inspection of page 107688 showed printed header text
  missing from the reference and stray markup in the transcript. Covers and
  sparse pages also limit usefulness. Proofread status alone does not establish
  complete page OCR gold. Keep the exclusion audit, without presenting these
  files as 11 valid new OCR test pages.
- Keep previous KHOB/KhmerST results separate. Historical leaves do not replace
  a modern printed-document/phone-scan benchmark. Check exact image hashes
  against earlier inventories; no claim excludes all possible near duplicates.
- CHURRO-DS permits research use; its paper lists SleukRith permission for
  research. Original images and transcriptions are not redistributed. Public
  manifests contain source identities, hashes, dimensions and counts.

## Systems and fixed settings

Evaluate each available system on the same complete 150-page set. Run setup and
API checks only on KHOB development page `task-1/goc_3`, never on a selected new
test page. Pin every model file and checkpoint revision in `model-inventory.json`.

1. **Plain Tesseract fast:** local Tesseract, `khm+eng`, PSM 3, OEM 1. The
   original fast Khmer and English files match the earlier paired study. This
   is a pretrained LSTM recognition baseline; it is not a newly trained CRNN.
2. **KhmerEasyTools fast:** same executable/models/language order and PSM;
   `khocr_layout(preprocess="auto", reading_order="engine", segment=False,
   min_confidence=0)`. Fast files are LSTM-only, so the toolkit's default OEM
   also executes LSTM. This compares packaged pipelines, not an isolated
   preprocessing ablation.
3. **Surya OCR 2:** `surya-ocr==0.22.1`, official
   `datalab-to/surya-ocr-2-gguf` files, local llama.cpp Metal backend. Official
   `RecognitionPredictor(full_page=True)`, no supplied layout and no
   progressive-temperature regeneration. Four independent inference slots,
   batches of four pages, 4,096 output tokens per page; retain the final smaller
   batch. The library's native full-page HTML prompt is unchanged.
4. **PaddleOCR-VL 1.6, MLX community 4-bit conversion:** pinned
   `mlx-community/PaddleOCR-VL-1.6-4bit`; native MLX-VLM implementation and
   checkpoint processor, prompt `OCR:`, temperature 0, maximum 4,096 output
   tokens, batch one. This is a standalone whole-image VLM evaluation, not the
   complete PaddleOCR document pipeline with its layout detector. No claim is
   made that standard PP-OCR recognition checkpoints support Khmer.
5. **DeepSeek-OCR, MLX community 4-bit conversion:** pinned
   `mlx-community/DeepSeek-OCR-4bit`; native MLX-VLM implementation and default
   processor (base 1024, image 640, dynamic cropping), official free-OCR prompt
   `<image>\nFree OCR.`, temperature 0, maximum 4,096 output tokens, batch one.
   It is not the original unquantized CUDA/FlashAttention implementation.

External baseline packages and model weights stay in an ignored, isolated
research environment. They do not become toolkit dependencies or wheel content.
No cloud inference, paid compute or translation service is used.

Use at most four CPU workers and `OMP_THREAD_LIMIT=1` for Tesseract pipelines.
Each backend call has a 240-second deadline; a Surya batch has an additional
20-second client margin. Runtime/model setup failures make that system
unavailable, not an invented 100%-CER result. Actual page-call failures are
retained with empty output; partial returned Surya blocks are retained and
flagged. Resume only with matching frozen hashes and environment versions.

## Scoring and interpretation

- Primary: micro character error rate on NFC-normalized code points, removing
  Unicode whitespace and ZWSP, exactly as in earlier studies. Retain every
  reference denominator, including failures and successful empty responses;
  CER can exceed 100% when insertions exceed the reference length.
- Remove output serialization with fixed, reference-independent HTML/Markdown
  handling; retain all recognized prose, including hallucinated explanations.
  Do not modernize spelling, fix Khmer Unicode sequences beyond NFC, select
  favorable outputs, or run a language model over predictions.
- Report the 150-page aggregate and the source test/train partitions separately.
  Include exact pages, empty outputs, failures and MLX token-cap hits. Surya's
  high-level result does not expose decoder token counts, so its cap-hit count
  is unknown rather than assumed zero.
- Compare with plain Tesseract using 5,000 paired cluster-bootstrap replicates,
  seed 20261018. Groups are conservative manuscript-prefix heuristics from
  released filenames (27 selected groups), not independently verified book
  identities. Intervals are descriptive; manuscript dependence, small official
  test sample, uncertain training overlap, upstream annotation errors and
  multiple comparisons prevent broad significance/generalization claims.
- Time measurements describe this concurrent local experiment. Surya uses
  batches of four and records amortized per-page time; other VLMs use batch
  one. No controlled speed superiority or cross-platform accuracy claim.
- This is historical handwriting outside the toolkit's printed-page design
  scope. Poor results must be reported; lower CER alone cannot establish
  dependable manuscript transcription, modern document robustness, layout
  accuracy or superiority of original unquantized models.

## Primary sources

- https://huggingface.co/datasets/stanford-oval/churro-dataset
- https://aclanthology.org/2025.emnlp-main.1763/
- https://github.com/donavaly/SleukRith-Set
- https://github.com/back-kh/KH-FUNSD (data not publicly downloadable at inspection)
- https://huggingface.co/datasets/Darachhat/khmer-document-corpus (no OCR gold)
- https://github.com/datalab-to/surya
- https://huggingface.co/datalab-to/surya-ocr-2-gguf
- https://huggingface.co/mlx-community/PaddleOCR-VL-1.6-4bit
- https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6
- https://github.com/deepseek-ai/DeepSeek-OCR
- https://huggingface.co/mlx-community/DeepSeek-OCR-4bit

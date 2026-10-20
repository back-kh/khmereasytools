# KH-FUNSD operational-reference OCR comparison

This new study uses the author-identified KH-FUNSD folder: 148 files, 146 unique upright images after exact deduplication (96 receipts, 34 invoices, 16 quotations). The author designated the frozen Codex transcripts as operational ground truth. They have **zero independent human reviews**. Scores measure agreement with those machine-generated references, not verified human OCR accuracy.

All 146 images remain included, including 491 literal `[ILLEGIBLE]` markers on 91 pages. Those markers contribute 5,401 of 55,867 compact reference code points. The predefined marker-free sensitivity subset has 55 pages and still does not certify reference completeness. Folder labels Digital/Scanned and distinct image hashes do not establish independent documents, camera conditions or mapping to all 158 documents described by the KH-FUNSD publication.

A separate [focused document diagnostic](CLEAN_DOCUMENT_DIAGNOSTIC.md) retains
eight business images after input/reference-flag screening, alongside ten KHOB
digital-export pages in a different track. Its post hoc agreement results do
not replace this full comparison or promote the references to human gold.

[Frozen protocol](../benchmarks/accuracy/BUSINESS_OCR_PROTOCOL.md) · [counts and profiles](../benchmarks/accuracy/business-ocr/results.json) · [independent audit](../benchmarks/accuracy/business-ocr/consistency-audit.json)

## All 146 images

Percent error, lower is better. All rates are unbounded micro edit ratios. Whitespace-unit and segmentation-assisted WER use the conventions in [the metric guide](OCR_WORD_METRICS.md); neither uses human-annotated Khmer word boundaries. Cap counts denote the 4096-token output limit; n/a applies to non-autoregressive Tesseract profiles.

| System | CER | Whitespace-unit WER | Segmentation-assisted WER | Empty | Errors | Caps |
|---|---:|---:|---:|---:|---:|---:|
| Tesseract fast LSTM | 55.29% | 63.87% | 62.78% | 7 | 0 | n/a |
| KET-OCR (Tesseract) | 53.76% | 62.04% | 62.81% | 3 | 0 | n/a |
| Surya 2 GGUF first pass | 69.65% | 68.10% | 67.17% | 1 | 0 | 23 |
| PaddleOCR-VL 1.6 MLX 4-bit | 406.95% | 344.19% | 651.63% | 1 | 0 | 56 |
| DeepSeek-OCR MLX 4-bit | 494.82% | 429.33% | 891.42% | 0 | 0 | 63 |

KET-OCR is the Khmer Easy Tools preparation/layout pipeline using Tesseract, not a newly trained recognizer. Overall agreement CER is lower than plain Tesseract, but segmentation-assisted WER is slightly higher. Receipts improve while invoice/quotation and Scanned-folder CER do not. These strata do not isolate a causal preprocessing effect.

## Matched 30 images

Both Qwen models use exactly the same fixed 30 images as the primary systems below: 20 receipts, seven invoices, three quotations, and 20 Digital/ten Scanned folder labels. Selection used proportional allocation and hash order before predictions. Do not compare Qwen on 30 against unmatched primary systems on 146.

| System | CER | Whitespace-unit WER | Segmentation-assisted WER | Empty | Errors | Caps |
|---|---:|---:|---:|---:|---:|---:|
| Tesseract fast LSTM | 57.63% | 60.68% | 61.19% | 3 | 0 | n/a |
| KET-OCR (Tesseract) | 54.32% | 58.29% | 61.61% | 1 | 0 | n/a |
| Surya 2 GGUF first pass | 85.84% | 64.68% | 73.85% | 0 | 0 | 6 |
| PaddleOCR-VL 1.6 MLX 4-bit | 455.07% | 527.09% | 578.85% | 1 | 0 | 13 |
| DeepSeek-OCR MLX 4-bit | 673.91% | 580.48% | 1296.81% | 0 | 0 | 16 |
| Qwen2.5-VL 3B BF16 | 432.54% | 432.98% | 545.44% | 0 | 0 | 11 |
| Qwen3-VL 2B BF16 | 597.58% | 671.91% | 878.37% | 0 | 0 | 19 |

These are poor recognition results under the recorded single-image profiles. They do not rank every implementation of the model families. Neural calls do not reproduce complete vendor layout/region-cropping pipelines, and the recorded quantizations, prompts, native processing and output limits constrain interpretation. No semantic layout, field-extraction or document-classification accuracy is measured.

## Integrity and scope

- All 790 records are complete: 730 primary predictions plus 60 Qwen predictions. Failed, empty and capped outputs retain their reference denominators; no clipping, repetition repair or selective retry.
- The separate bit-vector audit checks all 2,370 projected distances, all 146 image hashes and all aggregate counts, after 1,039 dynamic-programming self-checks. It verifies arithmetic/provenance, not human reference quality.
- All352 GPU output files match the final remote SHA-256 inventory after transfer. No reference text was sent to the GPU inference host.
- Existing b062be0 recognition code and pinned checkpoint bytes are retained. New KET-OCR, KhmerRAG and translation interfaces do not change the recognizer.
- Mac runs Tesseract/KET/Surya; Linux CUDA runs the two MLX profiles and Qwen. Qwen3 moved from device 2 to available shared device 3 before its first prediction; its separately frozen [execution amendment](../benchmarks/accuracy/business-ocr/execution-amendment.json) preserves recognition settings. Shared hosts do not support a speed ranking.
- Images, transcripts and predictions remain private. Recomputing these scores needs the private frozen references and images; hashes/scripts alone do not provide them. The Codex provider snapshot is unavailable, so regenerating identical transcripts is not guaranteed.

Scoring commands, with the private frozen inputs and downloaded execution profiles in place:

```bash
python -I scripts/report_business_ocr.py
python -I scripts/audit_business_ocr.py
```

A private `--preview` report is available while collecting results; it cannot publish an incomplete final comparison. Preserve all older historical/KhmerST studies. See [reference review](REFERENCE_REVIEW.md) for a future human-correction workflow, [native function validation](VALIDATION.md), and [simple KhmerRAG](RAG.md).

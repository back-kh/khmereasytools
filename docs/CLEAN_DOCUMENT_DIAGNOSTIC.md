# Smaller printed-document diagnostic

A focused subset retains **18 images** after screening 20 candidates: ten
KHOB digital-export pages and eight KH-FUNSD business images. This is a post hoc
diagnostic for easier-to-inspect inputs, prepared after the larger results were
known. It is not a new held-out benchmark or a substitute for the full studies.
The two tracks have different reference provenance and are not pooled.

[Selection protocol](../benchmarks/accuracy/CLEAN_DOCUMENT_DIAGNOSTIC_PROTOCOL.md)
· [frozen selection and exclusions](../benchmarks/accuracy/clean-document-diagnostic/selection.json)
· [all measured counts](../benchmarks/accuracy/clean-document-diagnostic/results.json)
· [separate implementation audit](../benchmarks/accuracy/clean-document-diagnostic/consistency-audit.json)

## How the images were selected

- **KHOB:** retain every task-1 digital-export image in the existing comparison
  partition, one acquisition per source document. Ten source documents remain;
  the other three acquisitions are still in the original 40-image report.
- **KH-FUNSD:** require no recorded draft uncertainty, no `[ILLEGIBLE]` marker,
  at least 50 Khmer letter/mark code points, a shortest edge of at least 500
  pixels and a longest edge of at least 1,000. The thresholds select candidates;
  they are not validated readability or transcription-quality measures.
- An assistant then inspected all 20 candidate source images for readability,
  gross clipping, obstruction and orientation. Two business screenshots were
  rejected because notification banners overlay the receipt interface. Their
  identities and reasons remain recorded. There was no replacement selection.
- Candidate selection and visual decisions used no per-image OCR outputs,
  confidence values or error rates. The final 18-image selection was frozen
  before subset scores were produced. All recognition outputs were reused from
  the earlier frozen studies, with no new OCR calls or parameter changes.

Of 146 business images, 47 drafts have neither an uncertainty span nor an
unreadable marker. Many of these contain little or no Khmer. Applying the
Khmer-content and dimension criteria leaves ten candidates, and the visual
screen retains eight. They comprise **seven Digital-folder receipts and one
Scanned-folder quotation, with no invoices**. Several receipts share a template;
these are not eight verified independent document types. Folder labels are not
certified capture conditions.

The image screen does not certify each reference character. All KH-FUNSD
`human_reviewed` and `reference_complete` flags remain false. Their references
are the original machine-generated operational ground truth. KHOB keeps its
existing upstream transcripts, without a new independent human review. Some
digital-export pages retain fine print, stamps and handwritten administrative
fields; this selection does not mean pristine typeset pages.

## Results on the fixed selected images

Percent error; lower is better. WER conventions are the same as the
[existing metric guide](OCR_WORD_METRICS.md): neither token metric uses human
Khmer word-boundary gold. Rates remain unbounded. Empty, failed and capped
outputs are retained in every selected-system denominator.

**KHOB digital-export track: ten pages, 19,694 compact reference code points.**

| System | CER | Whitespace-unit WER | Segmentation-assisted WER |
|---|---:|---:|---:|
| Tesseract fast LSTM | 12.60% | 53.57% | 37.80% |
| KET-OCR | 12.00% | 55.00% | 37.98% |

KET-OCR makes 2,364 character edits, versus 2,482 for Tesseract. Both added WERs
are slightly worse for KET-OCR on this track. The ten-page selection does not
meet the sub-10% CER target, despite its clearer acquisition scope. Both systems
return nonempty text on all ten pages, with no runtime errors.

**KH-FUNSD screened track: eight images, 2,480 compact reference code points.**
These are agreement scores against unreviewed machine references.

| Frozen implementation | Agreement CER | Whitespace-unit WER | Segmentation-assisted WER | Token caps |
|---|---:|---:|---:|---:|
| Tesseract fast LSTM | 36.45% | 39.86% | 42.31% | n/a |
| KET-OCR | 20.44% | 30.31% | 28.30% | n/a |
| Surya 2 GGUF first pass | 9.84% | 15.99% | 14.56% | 0 |
| PaddleOCR-VL 1.6 MLX 4-bit | 218.19% | 54.65% | 660.85% | 1 |
| DeepSeek-OCR MLX 4-bit | 482.66% | 245.11% | 1332.55% | 4 |

All five systems have complete coverage of these same eight images, with zero
empty outputs and zero runtime errors. KET-OCR has 507 character edits and Surya
244. Surya's result is **not** evidence that KET-OCR or general Khmer OCR has
achieved independently verified sub-10% CER. It is a descriptive agreement
score on a small, narrowly selected, unreviewed-reference sample. Qwen's earlier
30-image selection does not cover this complete track, so no unmatched Qwen
comparison is presented here.

The larger [KH-FUNSD](KHFUNSD_OCR.md), [scene-text](EXPANDED_OCR.md) and
[historical](DOCUMENT_OCR.md) results remain available and unchanged. Their
failures must not be hidden by replacing them with this focused sample. This
diagnostic can guide everyday-use development; stronger paper claims require
independently corrected references and newly held-out documents.

## Reproduction and checks

The separate audit verifies all 18 selected image hashes, 60 scored predictions,
180 projected edit distances and seven system/track aggregates. Its bit-vector
distance implementation passes 1,039 checks against dynamic programming.
Selection eligibility is independently reconstructed from the source metadata.
These checks establish consistency, not human reference quality.

Preparation requires the private caches from the original studies and Pillow;
scoring/auditing use the existing research environment and unchanged metric
dependencies. Nothing is added to the toolkit's core runtime dependencies.

```bash
python scripts/prepare_clean_document_diagnostic.py
python scripts/render_clean_document_review.py
# Inspect every candidate image; record decisions in the private
# .evaluation/clean_document_diagnostic/visual-screen.json.
python scripts/report_clean_document_diagnostic.py --freeze-only
python scripts/report_clean_document_diagnostic.py
python scripts/audit_clean_document_diagnostic.py
```

Preparation and scoring refuse to overwrite an existing selection or report.
The review viewer contains source images/references and no OCR predictions.
Private images, transcripts and the viewer stay on Drive F; the source repository
contains only scripts, protocol, identifiers, counts, hashes and decisions.

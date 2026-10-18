# Development selection before reserved comparisons

2026-10-18. No candidate predictions on the reserved split have been examined.
Historical baseline aggregate results existed before this work.

- Fixed SIL unigram decoder: ALT whole-word development segmentation F1
  67.0837 -> 69.1508; public POS joint span F1 68.0114 -> 68.5541.
  Retain this candidate without hyperparameter tuning.
- Direct POS adapter loads only the POS CRF, not the 17.7 MB word-tokenizer
  model. The same development process peaked at 142.3 MiB versus 162.4 MiB
  for the old two-model wrapper (process RSS, not an isolated model size).
- OCR development CER: original 22.9309%; 2x 19.3460%; 3x 19.3951%;
  2x grayscale/autocontrast 18.9676%. Select the last option.
  Apply only when the longest image edge is below 1600 pixels, with unchanged
  source coordinates and an explicit preprocess="none" escape hatch.
  All KHOB images satisfy that size condition. Larger-image accuracy is
  unmeasured; their pixels retain the previous processing path.

The historical leaf-tag POS report is not used as the before score. Both
before and after here collapse NOVA compounds, following upstream preparation.
Corpus overlap and imperfect OCR labels still limit claims.

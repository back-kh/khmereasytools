# README artwork and poster

These graphics describe KhmerEasyTools **0.5.0.dev0 source**, dated
**2026-10-20**. They use existing checked-in results and already documented
examples. No external corpus, model training, new evaluation run or selected
test subset was introduced to make the artwork.

| Asset | Purpose | Formats |
| --- | --- | --- |
| `overview` | Feature/footprint banner | PNG, SVG |
| `architecture` | Local core, optional Tesseract OCR, explicit provider clients | PNG, SVG |
| `tagging-workflow` | Actual documented Khmer POS example with original source spans | PNG, SVG |
| `evaluation` | Three separate fixed segmentation/POS/OCR comparisons | PNG, SVG |
| `poster` | A3 portrait technical overview, ready for printing | PNG, PDF |

The [manifest](manifest.json) records exact values, source SHA-256 hashes,
asset hashes, authoring versions, font identity and actual tagging output.
SVG text is outlined for consistent display. PNG is used in the README for
portable rendering. The poster PDF is one A3 page with vector artwork.

## Scope of each plotted comparison

- **Word segmentation:** `khseg` exact-token F1, earlier coverage decoder
  77.21% versus frequency costs 78.46%. khPOS OPEN, 1,000 sentences / 10,778
  tokens. Previously observed single-corpus diagnostic.
- **Coarse POS:** authored v1 37.61% versus compact v2 81.07%, on the same
  1,018 ALT sentences / 26,551 whole words. Gold boundaries and a lossy
  seven-class projection. Unknown/incorrect predictions remain in denominators.
- **OCR:** earlier default 15.99% versus auto preprocessing 11.43% code-point
  CER; lower is better. Same 40 KHOB images: 10 underlying documents, four
  variants each. Same Khmer model, local macOS comparison. Reference alignment
  and reading-order limits apply; these are not 40 independent documents.

The panels have separately labeled axes and cannot be compared as the same
metric. There are no confidence intervals or statistical-significance claims.
The POS chart does not compare ALT's 37.61% against khPOS's 95.94%.
The poster separately labels native gold-boundary accuracy and joint raw-text
F1, and discloses the public-label projection. Source details:

- [Earlier paired results](../../benchmarks/accuracy/improvements/baseline_reserved.json)
- [Improved paired results](../../benchmarks/accuracy/improvements/improved_reserved.json)
- [Compact tagger results](../../benchmarks/accuracy/tagger-v2/results.json)
- [Training/selection protocol](../../benchmarks/accuracy/TAGGER_V2_PROTOCOL.md)
- [Native installation records](../../benchmarks/accuracy/tagger-v2/native-validation.json)

## Regenerate

Use a separate authoring environment, preferably Python 3.12:

```bash
python -m pip install -r requirements-visuals.txt
python scripts/build_readme_visuals.py --khmer-font /path/to/KhmerOSBattambang-Regular.ttf
```

The command runs from the repository root, reads only local checked-in data,
and writes these assets plus the manifest. It checks model/source data
consistency, paired sample counts and text clipping. The documented example
is obtained from the actual `khtag` API and checks source offsets.

The artwork was rendered with Khmer OS Battambang, typeface copyright Danh
Hong (2010). Khmer text is shaped with HarfBuzz and exported as glyph outlines;
the font file is not bundled. Supply a compatible font for regeneration.
Matplotlib's bundled DejaVu font supplies Latin labels.

These authoring packages are **not runtime dependencies** of KhmerEasyTools.
Review generated PNGs and the rendered PDF after any layout change. Preserve
the frozen result JSON/protocols; change the drawing rather than adjusting
research numbers to fit a presentation.

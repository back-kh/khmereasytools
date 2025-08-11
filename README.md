# Khmer Easy Tools

[![PyPI version](https://img.shields.io/pypi/v/khmereasytools.svg)](https://pypi.org/project/khmereasytools/)
[![Python versions](https://img.shields.io/pypi/pyversions/khmereasytools.svg)](https://pypi.org/project/khmereasytools/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](#license)

`khmereasytools` is a lightweight, self-contained Python library designed for essential Khmer Natural Language Processing (NLP) tasks. It emphasizes simplicity, ease of use, and minimal dependencies, making it suitable for quick deployment in environments where installing heavy NLP frameworks is impractical. Advanced capabilities are available as optional “extras,” allowing users to install only the features they need.

- **Core:** Khmer word segmentation, keyword filtering, and syllable segmentation are implemented using a built-in Khmer Stop Dictionary and Khmer Segmentation Dictionary. Part-of-speech tagging and OCR functionalities are integrated via existing, well-established libraries. These implementations are intentionally lightweight and straightforward, which may introduce certain limitations in accuracy or coverage compared to large-scale NLP toolkits; however, they remain efficient, portable, and well-suited for resource-constrained environments.
---

## Table of Contents

- [Installation](#installation)
  - [Base](#base)
  - [Optional extras](#optional-extras)
  - [OCR prerequisite](#ocr-prerequisite)
  - [Troubleshooting](#troubleshooting)
- [Quickstart](#quickstart)
- [API Overview](#api-overview)
  - [`is_khmer(text)`](#is_khmertext)
  - [`khseg(text)`](#khsegtext)
  - [`khfilter(text)`](#khfiltertext)
  - [`khsyllable(text)`](#khsyllabletext)
  - [`khpos(text)` *(extra)*](#khpostext-extra)
  - [`khocr(image_path)` *(extra)*](#khocrimage_path-extra)
- [Examples](#examples)
- [License](#license)
- [Contributing](#contributing)
- [Citation](#citation)
- [Changelog](#changelog)

---

## Installation

### Base

Install the core package (no heavy deps):

```bash
pip install khmereasytools
```

## Quickstart

```python
import khmereasytools as ket

text = "ខ្ញុំស្រឡាញ់ភាសាខ្មែរ"

print(ket.is_khmer(text))          # True
print(ket.khseg(text))             # ['ខ្ញុំ', 'ស្រឡាញ់', 'ភាសាខ្មែរ']
print(ket.khfilter("នេះគឺជាប្រាសាទអង្គរវត្តដ៏ស្រស់ស្អាត"))
# 'ប្រាសាទ អង្គរវត្ត ដ៏ ស្រស់ស្អាត'
print(ket.khsyllable("សាលារៀន"))   # ['សា', 'លា', 'រៀន']
```

---

## API Overview

### `is_khmer(text)`
- **Purpose:** Detect presence of Khmer Unicode characters.
- **Input:** `str`
- **Returns:** `bool`

### `khseg(text)`
- **Purpose:** Word segmentation using a built-in dictionary and longest-match.
- **Input:** `str`
- **Returns:** `List[str]`

### `khfilter(text)`
- **Purpose:** Keyword extraction via segmentation + Khmer stop-word removal.
- **Input:** `str`
- **Returns:** `str` (space-joined keywords)

### `khsyllable(text)`
- **Purpose:** Syllable segmentation via simple rules.
- **Input:** `str`
- **Returns:** `List[str]`

### `khpos(text)` *(extra)*
- **Requires:** `pip install "khmereasytools[khmernltk]"`
- **Purpose:** Part-of-speech tagging using `khmernltk`.
- **Input:** `str`
- **Returns:** `List[Tuple[str, str]]` — `(word, POS)`

### `khocr(image_path)` *(extra)*
- **Requires:** `pip install "khmereasytools[ocr]"` + system Tesseract + Khmer traineddata
- **Purpose:** Extract Khmer text from images.
- **Input:** `str` — path to image file
- **Returns:** `str`

---

## Examples

### Khmer character validation

```python
import khmereasytools as ket

print(ket.is_khmer("សួស្តី"))  # True
print(ket.is_khmer("Hello"))   # False
```

### Word segmentation

```python
import khmereasytools as ket

words = ket.khseg("ខ្ញុំស្រឡាញ់ភាសាខ្មែរ")
print(words)  # ['ខ្ញុំ', 'ស្រឡាញ់', 'ភាសាខ្មែរ']
```

### Keyword extraction

```python
import khmereasytools as ket

keywords = ket.khfilter("នេះគឺជាប្រាសាទអង្គរវត្តដ៏ស្រស់ស្អាត")
print(keywords)  # 'ប្រាសាទ អង្គរវត្ត ដ៏ ស្រស់ស្អាត'
```

### Syllable segmentation

```python
import khmereasytools as ket

print(ket.khsyllable("នេះជាសាលារៀន"))  # ['នេះ', 'ជា', 'សា', 'លា', 'រៀ', 'ន']
```

### POS tagging *(extra)*

```python
import khmereasytools as ket

tags = ket.khpos("ខ្ញុំស្រឡាញ់ភាសាខ្មែរ")
print(tags)  # [('ខ្ញុំ', 'n'), (' ', 'n'), ('ស្រឡាញ់', 'v'), (' ', 'n'), ('ភាសា', 'n'), ('ខ្មែរ', 'n')]

### OCR from image *(extra)*

```python
# System: Tesseract with Khmer data; Python: pip install "khmereasytools[ocr]"
import khmereasytools as ket

try:
    text = ket.khocr("path/to/khmer_text.png")
    print(text)
except Exception as e:
    print("OCR error:", e)

```
### OCR prerequisite

For `khocr`, install the **Tesseract OCR engine** (system package) and the **Khmer language data (`khm`)**:

- Windows: Install Tesseract from the official installer and select Khmer (`khm`) during setup (or add later).  
- macOS: `brew install tesseract` then add Khmer traineddata.  
- Linux: `sudo apt-get install tesseract-ocr tesseract-ocr-khm` (package names may vary by distro).

Python side is handled by the `ocr` extra (`pytesseract`, `Pillow`).

### Troubleshooting

- **`khmernltk>=2.2` not found:** Use base install without extras or try a different Python version (3.9–3.11 usually safest), then reinstall the `khmernltk` extra when available.
- **Tesseract not found:** Ensure `tesseract` is on your system `PATH` (Windows) or installed in standard locations (macOS/Linux). Verify with `tesseract --version`.
- **Khmer OCR garbled:** Confirm Khmer language data is installed and pass `lang="khm"` if your wrapper exposes it.

---
### Optional extras

Install only the features you need:

```bash
# POS tagging (requires khmernltk)
pip install "khmereasytools[khmernltk]"

# OCR (requires pytesseract + Pillow)
pip install "khmereasytools[ocr]"

# Everything
pip install "khmereasytools[all]"
```
- **Extras (optional):** POS tagging via `khmernltk`, OCR via Tesseract (`pytesseract` + `Pillow`)
> **Note:** If your environment cannot resolve `khmernltk` (e.g., older Python or OS wheels unavailable), install the base package and skip the `khmernltk` extra. Core features will still work.


## License

This project is licensed under the **MIT License**. See [`LICENSE`](./LICENSE) for full text.

---

## Contributing

Issues and pull requests are welcome!  
- Report bugs with a minimal repro and environment details.  
- For new features, open an issue to discuss scope and API shape before submitting a PR.

---

## Citation

If this toolkit assists academic or industry work, consider citing the repository:

```bibtex
@article{thuon2024ksw, title={KSW: Khmer Stop Word based Dictionary for Keyword Extraction}, author={Thuon, Nimol and Zhang, Wangrui and Thuon, Sada}, journal={arXiv preprint arXiv:2405.17390}, year={2024} }
```

---

## Changelog

See [`CHANGELOG.md`](./CHANGELOG.md) for version history (features, fixes, breaking changes).






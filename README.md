
# Khmer Easy Tools

A simple, user-friendly, and self-contained Python library for common Khmer Natural Language Processing (NLP) tasks. This package provides easy-to-use functions for keyword extraction and segmentation without requiring complex external dependencies for its core features.

## Installation

Install the base package:
```bash
pip install khmereasytools
```

### Installing Optional Features

You can install the features you need.

```bash
# To install support for POS tagging (khpos)
pip install khmereasytools[khmernltk]

# To install support for OCR (khocr)
pip install khmereasytools[ocr]

# To install all optional features
pip install khmereasytools[all]
```

**For OCR functionality**, you must also install Google's Tesseract OCR engine on your system.
-   [Tesseract Installation Guide](https://github.com/tesseract-ocr/tesseract/wiki)
-   Make sure to install the Khmer (`khm`) language data.

## How to Use

### Keyword Extraction (`khfilter`)
Uses a built-in segmentation algorithm to find words and remove stop words by using Khmer Stop Word and Segmentaion Dictionary.
```python
import khmereasytools as ket
text = "នេះគឺជាប្រាសាទអង្គរវត្តស្ថិតនៅក្នុងខេត្តសៀមរាប"
keywords = ket.khfilter(text)
print(f"Keywords: '{keywords}'")
```

### Text Segmentation (`khseg`)
Uses a built-in segmentation algorithm to split text into words.
```python
import khmereasytools as ket
text = "នេះគឺជាប្រាសាទអង្គរវត្ត"
words = ket.khseg(text)
print(f"Segmented Words: {words}")
```

### Syllable Segmentation (`khsyllable`)
Uses a built-in rule-based method to split text into syllables.
```python
import khmereasytools as ket
text = "សាលារៀន"
syllables = ket.khsyllable(text)
print(f"Syllables: {syllables}")
```

### Part-of-Speech Tagging (`khpos`)
*Requires `khmernltk` to be installed.*
```python
import khmereasytools as ket
# pip install khmereasytools[khmernltk]
text = "ខ្ញុំស្រឡាញ់ភាសាខ្មែរ"
tags = ket.khpos(text)
print(f"POS Tags: {tags}")
```

### OCR from Image (`khocr`)
*Requires `ocr` dependencies to be installed.*
```python
import khmereasytools as ket
# pip install khmereasytools[ocr]
# text_from_image = ket.khocr('khmer_text.png')
# print(f"Text from OCR: {text_from_image}")
```

# Khmer Easy Tools

Khmer Easy ToolsPyPI Project: https://pypi.org/project/khmereasytools/A simple, user-friendly, and self-contained Python library for common Khmer Natural Language Processing (NLP) tasks. This package provides easy-to-use functions for keyword extraction and segmentation without requiring complex external dependencies for its core features.InstallationInstall the base package (which includes is_khmer, khseg, khfilter, and khsyllable):pip install khmereasytools
Installing Optional FeaturesYou can install extra features as needed. This modular approach prevents installation errors if a dependency is not compatible with your system.# To install support for Part-of-Speech tagging (khpos)
pip install khmereasytools[khmernltk]

# To install support for Optical Character Recognition (khocr)
pip install khmereasytools[ocr]

# To install all optional features at once
pip install khmereasytools[all]
Important Note for OCR: To use the khocr function, you must also install Google's Tesseract OCR engine on your system and the Khmer language pack.Tesseract Installation GuideUsage ExamplesHere is how to use the functions available in the library:Khmer Character Validation (is_khmer)Checks if a string contains any Khmer characters.import khmereasytools as ket

print(f"'សួស្តី' is Khmer: {ket.is_khmer('សួស្តី')}")
# Expected Output: 'សួស្តី' is Khmer: True

print(f"'Hello' is Khmer: {ket.is_khmer('Hello')}")
# Expected Output: 'Hello' is Khmer: False
Text Segmentation (khseg)Uses a built-in dictionary-based algorithm to split text into words.import khmereasytools as ket

text = "ខ្ញុំស្រឡាញ់ភាសាខ្មែរ"
words = ket.khseg(text)
print(f"Segmented Words: {words}")
# Expected Output: Segmented Words: ['ខ្ញុំ', 'ស្រឡាញ់', 'ភាសាខ្មែរ']
Keyword Extraction (khfilter)Segments text into words and then removes common stop words.import khmereasytools as ket

text = "នេះគឺជាប្រាសាទអង្គរវត្តដ៏ស្រស់ស្អាត"
keywords = ket.khfilter(text)
print(f"Keywords: '{keywords}'")
# Expected Output: Keywords: 'ប្រាសាទ អង្គរវត្ត ដ៏ ស្រស់ស្អាត'
Syllable Segmentation (khsyllable)Uses a built-in rule-based method to split text into its component syllables.import khmereasytools as ket

text = "សាលារៀន"
syllables = ket.khsyllable(text)
print(f"Syllables: {syllables}")
# Expected Output: Syllables: ['សា', 'លា', 'រៀន']
Part-of-Speech Tagging (khpos)Requires khmernltk to be installed. Tags each word with its grammatical function (e.g., Noun, Verb).import khmereasytools as ket
# pip install khmereasytools[khmernltk]

text = "ខ្ញុំស្រឡាញ់ភាសាខ្មែរ"
tags = ket.khpos(text)
print(f"POS Tags: {tags}")
# Expected Output: POS Tags: [('ខ្ញុំ', 'PRO'), ('ស្រឡាញ់', 'VERB'), ('ភាសាខ្មែរ', 'NOUN')]
OCR from Image (khocr)Requires ocr dependencies and Tesseract to be installed. Extracts Khmer text from an image file.import khmereasytools as ket
# pip install khmereasytools[ocr]

try:
    # Make sure you have an image file e.g., 'khmer_text.png'
    text_from_image = ket.khocr('path/to/your/khmer_text.png')
    print(f"Text from OCR: {text_from_image}")
except Exception as e:
    print(e)
LicenseThis project is licensed under the MIT License. See the LICENSE file for details.

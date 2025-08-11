# Khmer Easy Tools

**PyPI Project Link:** [https://pypi.org/project/khmereasytools/](https://pypi.org/project/khmereasytools/)

This link takes you to the official project page on the Python Package Index (PyPI), where the library is hosted. Users can find version history and other package details here.

---

`khmereasytools` is a simple, user-friendly, and self-contained Python library for common Khmer Natural Language Processing (NLP) tasks. The main goal of this package is to provide easy-to-use functions for essential text manipulations like keyword extraction and word segmentation, without forcing users to install complex dependencies that might fail on their system.

## Installation

### Base Installation

You can install the core library, which is lightweight and has no heavy dependencies, using `pip`. This will give you access to the foundational functions: `is_khmer`, `khseg` (word segmentation), `khfilter` (keyword extraction), and `khsyllable` (syllable segmentation).

```bash
pip install khmereasytools
```
##Installing Optional Features
For more advanced tasks, khmereasytools uses "extras". This allows you to install additional features only when you need them, preventing installation errors if a particular dependency is not compatible with your system (a common issue with some NLP libraries on Windows).




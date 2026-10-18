# Khmer Easy Tools

[![PyPI version](https://img.shields.io/pypi/v/khmereasytools.svg)](https://pypi.org/project/khmereasytools/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/back-kh/khmereasytools/blob/v0.4.0/LICENSE)

Lightweight Khmer NLP and **traceable text preparation**, with no runtime dependencies for core features. Inspect suspicious text, choose cleanup rules explicitly, and map cleaned text or tokens back to their source. Everything runs locally.

Version 0.4.0 adds a text-quality workflow for OCR review, annotation, search preprocessing, and corpus preparation. This is an engineering focus, **not a claim of research novelty or superior segmentation accuracy**. See [design, prior art, and limitations](https://github.com/back-kh/khmereasytools/blob/v0.4.0/docs/DESIGN.md).

## Installation

Version **0.4.0** includes the text-quality APIs below and preserves the legacy core APIs.

```bash
# Install or upgrade from PyPI:
python -m pip install --upgrade khmereasytools

# From a source checkout:
python -m pip install .
```

Python 3.6+; use a maintained Python version for new projects. Core features do not download models or import optional OCR/POS libraries.

```bash
# Optional extras:
python -m pip install 'khmereasytools[khmernltk]'  # installs the khmer-nltk distribution
python -m pip install 'khmereasytools[ocr]'       # pytesseract + Pillow
python -m pip install 'khmereasytools[all]'
```

OCR also requires a system installation of [Tesseract](https://tesseract-ocr.github.io/tessdoc/Installation.html) and Khmer language data (`khm`). The import name for POS is `khmernltk`; its **PyPI distribution name is `khmer-nltk`**.

## Inspect before cleaning

```python
import khmereasytools as ket

raw = "\ufeffកាា\u200b ១២\r\nខ្មែរ"
report = ket.khaudit(raw)
for issue in report.issues:
    print(issue.code, issue.severity, issue.start, issue.end)
# bom warning 0 1
# repeated_khmer_mark warning 3 4
# zero_width_space info 4 5
```

`khaudit` flags repeated Khmer marks, orphan marks, dangling coeng, discouraged inherent vowels, replacement characters, unassigned Khmer code points, and selected invisible/control characters. **These are review hints, not spelling judgments.** ZWSP and shaping controls are informational because they can be intentional.

The report also includes character counts and `khmer_letter_ratio`: Khmer letters / all Unicode letters. Marks, digits, punctuation, and spaces are excluded from that ratio; inputs with no letters return `0.0`. It is not a language-identification probability.

## Cleanup with an edit record

```python
result = ket.khnormalize(
    raw,
    zero_width_space="space",
    digits="ascii",
    collapse_spaces=True,
)
print(repr(result.text))  # 'កាា 12\nខ្មែរ'

# The repeated vowel is flagged by the audit, not silently guessed away.
for edit in result.edits:
    print(edit.start, edit.end, repr(edit.original),
          repr(edit.replacement), edit.reason)

# Source span corresponding to the first cleaned character:
assert result.source_spans[0] == (1, 2)
assert result.original == raw
```

All offsets are **Python Unicode code points**, with exclusive ends: `text[start:end]`. They are not byte positions or JavaScript UTF-16 positions. Each output character has one source span. A collapsed space maps to the entire consumed source run. Edits contain both source and output spans, enabling reconstruction in either direction by applying edits right to left.

| Option | Default | Behavior |
| --- | --- | --- |
| `remove_bom` | `True` | Remove BOMs at the leading edge, including those exposed by selected cleanup rules |
| `normalize_newlines` | `True` | Convert CRLF and CR to LF |
| `zero_width_space` | `"preserve"` | `"preserve"`, `"space"`, or `"remove"` for U+200B |
| `digits` | `"preserve"` | `"preserve"`, `"ascii"`, or `"khmer"` |
| `collapse_spaces` | `False` | Collapse horizontal whitespace, including tabs/NBSP; retain line breaks |
| `strip` | `False` | Trim leading/trailing whitespace |
| `remove_inherent_vowels` | `False` | Remove U+17B4 and U+17B5 explicitly |

Joiners, punctuation, spelling, and Khmer character order are preserved. This function does **not** implement NFC/NFKC, Khmer canonical reordering, OCR correction, or transliteration. Disabling `remove_bom` and `normalize_newlines` with other defaults makes cleanup an identity operation. Results include the original text and per-character mappings, so process large corpora document by document.

## Lossless tokens and domain vocabulary

```python
text = "ឋខ្ញុំ\u200b Khmer ២០២៦។"
tokens = ket.khseg_spans(text)
assert "".join(token.text for token in tokens) == text
assert all(text[token.start:token.end] == token.text for token in tokens)
assert [token.text for token in tokens[:2]] == ["ឋ", "ខ្ញុំ"]

# Add names, terminology, or multiword phrases without changing global state.
tokens = ket.khseg_spans("ខ្ញុំស្រឡាញ់", custom_words=["ខ្ញុំស្រឡាញ់"])
assert len(tokens) == 1
assert tokens[0].kind == "word"
```

Token kinds are `word` (dictionary match), `unknown_khmer`, `latin` (ASCII letter runs), `number` (Unicode decimal-digit runs), `whitespace`, `boundary` (ZWSP), `punctuation`, and `other`. `word` does not imply a confidence score. Non-ASCII foreign letters fall under `other`; this is not a general multilingual tokenizer. Names and unknown words still need review. Unlike legacy `khseg`, `khseg_spans` preserves all input and can resume matching after an unknown Khmer run. It avoids matches that cut immediately before a Khmer mark/join control or after coeng; it is not a full grapheme or syllable parser.

## Khmer digits without losing formatting

```python
assert ket.khdigits("០០៧ / ១២.៥%") == "007 / 12.5%"
assert ket.khdigits("2026", target="khmer") == "២០២៦"
```

Only ASCII and Khmer digit characters are translated. Leading zeros and separators are retained. Number words, arithmetic, locale parsing, dates, and other scripts' digits are outside its scope.

## Command line

Commands accept a UTF-8 file or `-`/omitted input for stdin. They write to stdout and never overwrite the source file. `audit`, `segment`, and `normalize` produce JSON; `normalize --text-only` and `digits` produce text without adding a newline.

```bash
khmereasytools audit document.txt
khmereasytools normalize document.txt --digits ascii --zero-width-space space --collapse-spaces
khmereasytools normalize document.txt --text-only > cleaned.txt
khmereasytools segment document.txt --word 'ភាសាខ្មែរ'
khmereasytools digits document.txt --target khmer
python -m khmereasytools --help
```

Audit findings do not change the exit code: success is `0`, input/usage errors are `2`. Review the issue severities in JSON when implementing corpus acceptance policies.

## Legacy APIs

Existing signatures and text behavior remain available:

| API | Purpose / limitations |
| --- | --- |
| `is_khmer(text)` | Presence check for U+1780–U+17FF; not full validation or language detection |
| `khseg(text)` | Longest dictionary match; removes ZWSP and spaces; unknown runs may consume later known words |
| `khfilter(text, stop_words=None)` | Segmentation plus stop-word removal; no keyword ranking |
| `khsyllable(text)` | Legacy regex heuristic; not linguistically reliable syllabification |
| `get_default_stop_words()` | A fresh set of 379 built-in stop words |
| `load_stop_words_from_file(path)` | Load column one of a UTF-8 CSV; legacy missing-file behavior prints an error and returns an empty set |
| `khpos(text)` | Optional `khmer-nltk` wrapper; lazily imports its dependency |
| `khocr(image_path)` | Optional Tesseract wrapper with `lang="khm"`; retains legacy error-string behavior |

```python
assert ket.khseg("ខ្ញុំស្រឡាញ់ភាសាខ្មែរ") == ["ខ្ញុំ", "ស្រឡាញ់", "ភាសាខ្មែរ"]
assert ket.khfilter("ខ្ញុំស្រឡាញ់ភាសាខ្មែរ", stop_words={"ខ្ញុំ"}) == "ស្រឡាញ់ ភាសាខ្មែរ"
```

The inherited word dictionary has **213 entries**. Its size and heuristic fallback limit coverage. No held-out accuracy benchmark has been run for this development update, and none of the new diagnostics can recover information already lost to OCR or decoding.

## Development

```bash
python -m unittest discover -s tests -v
python -m pip install build twine
python -m build
python -m twine check dist/*
```

Tests cover source-offset preservation, reversible edits, cleanup stability, mixed scripts, legacy compatibility, optional imports, CLI errors, and deterministic randomized inputs. CI also installs the built wheel into an isolated environment. See [CHANGELOG.md](https://github.com/back-kh/khmereasytools/blob/v0.4.0/CHANGELOG.md) and [source provenance](https://github.com/back-kh/khmereasytools/blob/v0.4.0/docs/SOURCE_PROVENANCE.md).

Contributions should include a minimal example, expected behavior, and tests. Changes to spelling rules or linguistic accuracy claims need native-speaker review and an independently annotated evaluation set.

## Citation and license

The original README cites the related stop-word research; it does not evaluate the new text-quality APIs:

```bibtex
@article{thuon2024ksw,
  title={KSW: Khmer Stop Word based Dictionary for Keyword Extraction},
  author={Thuon, Nimol and Zhang, Wangrui and Thuon, Sada},
  journal={arXiv preprint arXiv:2405.17390},
  year={2024}
}
```

MIT License. See [LICENSE](https://github.com/back-kh/khmereasytools/blob/v0.4.0/LICENSE).

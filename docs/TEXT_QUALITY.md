# Text quality and source mappings

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

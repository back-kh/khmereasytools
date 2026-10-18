# Dictionary provenance and footprint

The default lexicon combines 80,999 retained ICU entries with the 213 legacy entries: **81,005 unique entries**. Entries can be words, compounds, or phrases. Membership is segmentation evidence, not spelling authority or confidence.

- Source: [unicode-org/icu khmerdict.txt](https://github.com/unicode-org/icu/blob/ad484f3d6c036ba06193ac7c3bc2233a53ab68b8/icu4c/source/data/brkitr/dictionaries/khmerdict.txt)
- Revision: `ad484f3d6c036ba06193ac7c3bc2233a53ab68b8`
- Raw SHA-256: `87bee2d17cd5148aa36957eb05409eefc124de8ad519b81b789298ef3e60b5d9`
- Derived SHA-256: `f398bea51287dc36d52d2482f0005ecff817733cedb84936fd8e5b72b73d9cf8`
- Source entries: 81,028; retained: 80,999.
- License: Unicode-3.0, with original Unicode/IBM notices retained in the package.

The transformation ignores comments/blank lines, deduplicates, keeps only entries consisting of Khmer-block letters and marks, then sorts by code point. It performs no Unicode normalization, spelling correction, or corpus-driven ranking. The combined lexicon retains six additional legacy entries absent from the filtered ICU list.

```bash
python scripts/rebuild_dictionary.py --check
```

The runtime never downloads data. It loads the dictionary on first use and caches a word set plus possible lengths indexed by the first two code points. This avoids a nested Python trie for every character. A local Python 3.9 `tracemalloc` smoke measurement, starting before library import and one segmentation call, observed about **13.7 MB retained / 17.7 MB peak Python allocations**. That is not total process RSS and excludes OCR/PDF engines; hardware/runtime differences apply. No general speed claim is made.

`get_khmer_dictionary()` returns an independent mutable set. `get_khmer_dictionary("legacy")` returns the original 213 entries. New APIs accept `dictionary="legacy"` or a caller-provided iterable. Neither custom words nor evaluation data modifies the cached default lexicon.

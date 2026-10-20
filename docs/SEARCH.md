# Local Khmer search and retrieval

`khsearch(query, documents)` accepts an iterable of text strings (IDs are zero-based integers) or a mapping from string/integer IDs to text. It returns `SearchHit` records with `document_id`, ranking `score`, unchanged source `text`, a review `snippet`, and `matches`. Each `SearchMatch` has `text`, `start`, and exclusive `end` in original Python code points. Matches highlight the whole indexed token, including an enclosing Khmer compound.

```python
from khmereasytools import khindex, khsearch

index = khindex({"a": "សិស្សអានសៀវភៅ។", "b": "ភាសាខ្មែរ"})
hits = khsearch("សៀវភៅ", index, limit=5)
print(index.get(hits[0].document_id))

# Require every distinct token in a multi-term query.
hits = index.search("សិស្ស សៀវភៅ", match="all")
```

Build an index once for repeated queries. It snapshots its input; rebuild after changing documents. `get(id)` returns unchanged source text and raises `KeyError` for an absent ID. Input text is never normalized in place or sent to a service. Document extraction is separate: index `khanalyze(file).text` when you explicitly want OCR output searched.

## Matching and ranking

Index and query use the same `khseg_spans` tokenizer and optional `khindex(..., custom_words=[...])` vocabulary. Whitespace and punctuation do not become terms. Matching folds case and Khmer digits to ASCII; it does not reorder Khmer characters, strip shaping controls, fix OCR errors, stem words, or translate queries. Unknown Khmer runs remain searchable.

The score uses positive-IDF BM25 with `k1=1.2` and `b=0.75`: `idf = log(1 + (N - df + .5)/(df + .5))`. See the [Lucene BM25 reference](https://lucene.apache.org/core/9_12_1/core/org/apache/lucene/search/similarities/BM25Similarity.html). Each distinct query term contributes once. Ties preserve input document order; scores are neither probabilities nor comparable across different collections.

Khmer substring recall checks the vocabulary so a query `ខ្មែរ` can retrieve an indexed compound `ភាសាខ្មែរ`. Each matching occurrence contributes a weighted term frequency: `1` for exact matches, otherwise `.5 * len(query_term)/len(indexed_term)`. Document frequency is the union of matching documents for that query term. This is a documented retrieval heuristic, not standard exact-term-only BM25. Latin/numeric partial words are not expanded. Spaces and dictionary phrase choices can still produce different boundaries; there is no exact-phrase operator or general fuzzy/semantic search.

The default `match="any"` returns documents matching at least one query term. `match="all"` requires all distinct query terms. Empty/punctuation-only queries and unmatched queries return an empty list. `limit` must be a positive integer. Stop words are retained, allowing users to search for them explicitly.

## Scope and evaluation

This is an in-memory index for small everyday collections. Vocabulary scanning for Khmer partial matches and keeping original strings/positions both have a cost. There is no disk persistence, distributed service, embedding download, or large-corpus performance claim. Pin the package/dictionary version when repeatable historical rankings matter.

Tests check Khmer relevance examples, compound recall, ranking against a hand-calculated BM25 score, mixed Khmer/Latin/digit matching, AND queries, stable ties, original offsets, snapshots, and invalid input. These are functional regressions, not an independent information-retrieval benchmark. Broader ranking quality needs user-representative documents and relevance judgments held separate from implementation decisions.

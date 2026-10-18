# Design and evidence

This document records the 0.4 design. In 0.5, segmentation defaults intentionally change; see [evaluation and migration](EVALUATION.md). The simple daily-use API and offline, optional OCR/PDF dependencies are described in the main README.

## Direction

Make Khmer text preparation **inspectable**: show what was found, what was changed, and where it came from. This helps people maintain alignment between OCR output, cleaned corpora, and annotations. The package remains usable offline with no core runtime dependencies.

This is a product differentiation proposal, not a verified claim that no other tool offers similar capabilities. No new segmentation algorithm or state-of-the-art result is claimed.

## Existing work checked

Repository documentation checked on 2026-10-18:

- [khmer-nltk](https://github.com/VietHoang1512/khmer-nltk): sentence and word tokenization plus POS tagging.
- [khmercut](https://github.com/seanghay/khmercut): Khmer word segmentation with model-based backends.
- [khmernormalizer](https://github.com/seanghay/khmernormalizer): character reordering and broader normalization, including whitespace, spelling, and URL/hashtag handling.
- [SIL Khmer Character Specification](https://github.com/sillsdev/khmer-character-specification): script documentation and the `khnormal` normalization/testing implementation.

Adding another generic tokenizer or unqualified normalizer would not by itself establish novelty. This update instead combines explicit cleanup policies, edit provenance, source mappings, structural review hints, and local command-line use. The comparison above is a scoped documentation review, not an exhaustive feature audit.

## Unicode grounding

[Unicode 17.0, section 16.4](https://www.unicode.org/versions/Unicode17.0.0/core-spec/chapter-16/) describes Khmer encoding. Its guidance motivates preserving join controls and intentional ZWSP boundaries, and reporting discouraged inherent vowels rather than silently changing spelling. Runtime character categories come from Python's bundled Unicode database.

The audit uses a small set of structural heuristics. It accepts consonants and independent vowels after coeng. It does not implement the full Khmer Encoding Structure grammar, check every ordering constraint, or prove that a sequence is linguistically valid. Informational findings distinguish invisible layout controls from suspected errors.

## Contracts

- Text APIs accept `str`; new APIs reject unsupported modes and wrong input types.
- Offsets use Python code points, start-inclusive/end-exclusive. Frontends using UTF-16 must convert offsets explicitly.
- `khnormalize` never guesses a missing/repeated letter or changes Khmer character order. Each edit contains original/replacement text and source/output spans.
- Applying forward edits right to left reconstructs cleaned text. Applying inverse edits right to left reconstructs source text. Adjacent deletions can share an output offset; keep the recorded order.
- `source_spans[i]` identifies the source consumed to produce output character `i`. A collapsed space can cover several input characters; this is a provenance interval, not a one-to-one alignment.
- Cleanup is intended to be idempotent with identical options. Tests exercise interacting options with deterministic randomized input.
- `khseg_spans` preserves every character, including malformed text. Dictionary membership is exposed as a token kind, never as probabilistic confidence.
- Existing `khseg`, `khfilter`, and `khsyllable` semantics are retained. The newer span tokenizer is opt-in to avoid silently changing downstream annotations.
- Optional POS and OCR imports occur only when called. Their external models/engines are not covered by the core accuracy claims or unit tests.

## Evaluation needed before stronger claims

1. Build a licensed, independently annotated test set spanning news, names, web text, OCR, mixed Khmer/Latin, and legitimate join-control usage.
2. Record document provenance and keep duplicates out of train/test splits.
3. Measure diagnostic precision/recall per rule, including false positives in legitimate script sequences.
4. Measure token boundary precision/recall/F1 separately from exact reconstruction. Add throughput and memory measurements with hardware and input sizes.
5. Compare any normalization-induced changes against native-speaker judgments; evaluate resulting OCR/search/annotation performance, not merely the number of edits.
6. Compare against pinned versions of relevant tools under their intended configurations. Do not treat a tiny handpicked example set as a quality benchmark.

The current tests establish software invariants and regressions. They do not establish linguistic accuracy or research novelty.

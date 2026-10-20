# KET-Tagger: inspectable Khmer grammar tags

`khtag` adds an offline, dependency-free Khmer grammar helper. It uses a
**312-entry authored starter POS lexicon** and small contextual rules, with
unknown words explicitly tagged `X`. The existing 81,005-entry segmentation
dictionary supplies boundaries, not POS labels. Membership in that dictionary
does not make a word a noun. This is a rule-based utility, not a trained model
or a demonstrated research novelty.

For broader general POS coverage, the existing optional CRF remains available
through `khpos`. KET-Tagger does not replace it or change its defaults.

## Everyday use

```python
import khmereasytools as ket

assert ket.khtag("ខ្ញុំអានសៀវភៅ។") == [
    ("ខ្ញុំ", "PRON"), ("អាន", "VERB"),
    ("សៀវភៅ", "NOUN"), ("។", "PUNCT")]

for token in ket.khtag("សិស្ស៣នាក់កំពុងអាន។", with_spans=True):
    print(token.text, token.label_km, token.role, token.reason)
```

No model, internet connection, installation extra, or configuration is needed.
Whitespace and zero-width space separators are omitted from the returned
tokens. `start` and `end` index the unchanged source in Python code points,
with an exclusive end: `text[token.start:token.end] == token.text`.
Keep the original text if you need to reconstruct spaces between annotations.
No spelling correction or Unicode reordering is applied.

Detailed `TaggedToken` records contain:

| Field | Meaning |
| --- | --- |
| `text`, `start`, `end` | Original token and source positions |
| `tag`, `label_km` | POS label and Khmer display name |
| `role` | Additional Khmer grammatical role; empty when unspecified |
| `candidates` | Ordered lexical alternatives, including the chosen tag |
| `rule`, `reason` | Stable rule identifier and explanation of the decision |

Candidates are neither probabilities nor an exhaustive list of possible
analyses. A single candidate is not a certainty claim. Ambiguity may remain
even when a rule selects one tag. There is no fabricated confidence score.

## Khmer-specific behavior

| Input/pattern | Tag and role |
| --- | --- |
| `ខ្ញុំ`, `គាត់` | PRON; personal pronoun |
| `មិន`, `ពុំ`, `កុំ`, `មិនមែន`, `មិនទាន់` | PART; negation |
| `ខ្ញុំមិនដឹងទេ។` | Final `ទេ`: PART; `negative_final` |
| `តើ`, `ឬទេ`; `អ្នកអានទេ?` | PART; question or question-final marker |
| `ទេ។` | INTJ; standalone negative response |
| `កំពុង`, `ធ្លាប់` | AUX; progressive or habitual |
| `នឹង` before a known predicate/auxiliary chain | AUX; future candidate |
| `បានអាន` / `អានបាន` / `បានប្រាក់` | Perfective AUX / ability AUX / lexical VERB |
| `អាច`, `គួរ`, `ត្រូវ` before a known predicate | AUX; ability, advisability, necessity |
| `៣នាក់`, `បីនាក់` | `នាក់`: NOUN with role `classifier` |
| `សៀវភៅនេះ` / `នេះជាសៀវភៅ` | `នេះ`: DET after a known noun / PRON elsewhere |
| `ហើយ` at the clause tail / inside a clause | Completion PART / conjunction candidate |
| `ទៅចុះ` / `គាត់ចុះ` | Directive-final PART / lexical VERB candidate |
| `លឿន` after a known verb | Manner ADV candidate; otherwise the lexical ADJ default |
| `បាទ`, `ចាស` | INTJ; polite response |
| `ៗ` | PART; repetition marker, without inferred scope |

Rules stop at punctuation and line breaks. They do not resolve sentence
structure, negation scope, quotation scope, kinship terms used as pronouns,
all serial-verb constructions, or unrestricted word-class conversion.
Some apparently simple sentences remain ambiguous. In particular, `នៅផ្ទះ`
is currently retained as a dictionary compound and returned as `X`; the tagger
does not split accepted dictionary compounds solely to expose particles.
Unknown Khmer, unsupported foreign words and unlisted compounds receive `X`.
Unicode decimal digits receive NUM; punctuation PUNCT; symbols SYM.

The POS interface uses the 17 names in the [Universal Dependencies v2
inventory](https://universaldependencies.org/u/pos/), with Khmer-specific roles
defined here. This is not an independently validated UD annotation scheme or
a dependency parser. Khmer particle and ambiguity distinctions are informed
by the [NICT Khmer annotation guidelines](https://www2.nict.go.jp/astrec-att/member/mutiyama/ALT/Khmer-annotation-guideline.pdf)
and the [khPOS author's tag descriptions](https://github.com/ye-kyaw-thu/khPOS).
Their annotation systems differ; our labels are not interchangeable with them.
Runtime entries and examples are independently authored, not extracted from
these research corpora. Native linguistic review of the fine tags is pending.

## Add your vocabulary locally

```python
# Domain terms and names; explicit overrides also set their token boundaries.
tagger = ket.KhmerTagger({"និមល": "PROPN", "KET": "PROPN"})
assert tagger.tag("និមលអាន។")[0] == ("និមល", "PROPN")

# Ordered alternatives are kept for review. The first supplied tag wins.
tokens = ket.khtag("KET", lexicon={"KET": ("PROPN", "NOUN")}, with_spans=True)
assert tokens[0].candidates == ("PROPN", "NOUN")
```

Overrides are copied and local to the tagger/call. Context rules do not replace
an explicit user tag. Keys and `custom_words` must be contiguous nonempty words
without whitespace or ZWSP. `custom_words` adjusts segmentation without
inventing a POS. Reuse `KhmerTagger` for repeated or concurrent calls.

```bash
khmereasytools tag notes.txt
khmereasytools ket-tagger notes.txt --term និមល=PROPN
```

Both commands produce the detailed UTF-8 JSON records. Omit the file to read
UTF-8 from stdin. `doctor` lists KET-Tagger under core and keeps the optional
CRF's setup status separate.

## Evaluation and limits

The [frozen protocol](../benchmarks/accuracy/TAGGER_PROTOCOL.md) and
[derived results](../benchmarks/accuracy/tagger/results.json) retain failures
and unknowns. All 1,018 ALT test sentences / 26,551 whole-word tokens were
included. This uses a deliberately lossy mapping to NOVA's seven coarse
classes; it cannot validate the new fine POS labels or particle roles.

| Full ALT diagnostic | KET-Tagger | Optional actual CRF |
| --- | ---: | ---: |
| All-token coarse accuracy at gold boundaries, X counted wrong | 37.61% | 99.35% |
| Answer coverage at gold boundaries | 46.80% | 100% |
| Coarse accuracy conditional on answering | 80.36% | 99.35% |
| Joint coarse word/tag F1 from unsegmented reconstruction | 30.80% | 67.67% |
| Exact segmentation span F1 | 68.29% | 68.29% |

These numbers establish the starter tagger's limited coverage. Conditional
accuracy excludes unknowns; it must not be reported as overall accuracy.
The CRF may have ALT training overlap and uses native NOVA labels rather than
our projected tags, so this is not a fair held-out model ranking. The corpus
is used only for evaluation under its CC BY-NC-SA license; no corpus text,
predictions, learned lexicon or trained weights ship with the package.

The authored development set passes specified assertions on **36/37 cases**.
The remaining compound-boundary target stays failed in the evaluation. Cases
with only role assertions do not have complete token-level annotations. These
checks were developed alongside the code, not independently native-reviewed.
The regression suite records the known abstention while retaining the unmet
linguistic target. Passing software tests does not erase that failure.

Reproduce against the pinned data already used by this repository:

```bash
python scripts/fetch_accuracy_data.py
python scripts/evaluate_tagger.py
# Optional reference comparison after installing .[khmernltk]:
python scripts/evaluate_tagger.py --with-crf
python -m unittest discover -s tests -v
```

The [native Windows/macOS/Linux run](https://github.com/back-kh/khmereasytools/actions/runs/39355812094)
passed at runtime commit `9892070`: 181 passed / 19 skipped in each fresh core
install, and 195 passed / 5 skipped in each extras install, including real OCR
and CRF POS. [Machine-readable records](../benchmarks/accuracy/tagger/native-validation.json)
and [validation details](VALIDATION.md) distinguish these software checks from
linguistic accuracy. No OCR benchmark, live translation result or paper
accuracy claim is changed by adding this API.

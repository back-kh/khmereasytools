"""KET-Tagger: compact learned Khmer POS with inspectable grammar helpers.

The authored starter lexicon remains available with model='rules'. The default
uses separately licensed khPOS research weights. Standard POS names are an
interface, not validated Universal Dependencies annotation. See docs/TAGGER.md.
"""

import unicodedata
import os
from collections.abc import Mapping
from functools import lru_cache
from types import MappingProxyType
from typing import NamedTuple, Tuple

from .segmentation import _validated_words, khseg_spans
from .text_quality import _require_text


class TaggedToken(NamedTuple):
    text: str
    start: int
    end: int
    tag: str
    label_km: str
    role: str
    candidates: Tuple[str, ...]
    rule: str
    reason: str


_LABELS = {
    "ADJ": "គុណនាម", "ADP": "ធ្នាក់", "ADV": "កិរិយាវិសេសន៍",
    "AUX": "កិរិយាសព្ទជំនួយ", "CCONJ": "សន្ធានសព្ទភ្ជាប់",
    "DET": "ពាក្យកំណត់", "INTJ": "ឧទានសព្ទ", "NOUN": "នាម",
    "NUM": "សំខ្យា", "PART": "និបាតសព្ទ", "PRON": "សព្វនាម",
    "PROPN": "នាមអសាធារណ៍", "PUNCT": "សញ្ញាវណ្ណយុត្ត",
    "SCONJ": "សន្ធានសព្ទរណប", "SYM": "និមិត្តសញ្ញា",
    "VERB": "កិរិយាសព្ទ", "X": "មិនស្គាល់",
}

# Independently authored common words, under the package's MIT license. These
# are deliberately small sets, not POS guesses for the 81,005-word dictionary.
# Ordering within a candidate tuple specifies the fallback analysis only.
_GROUPS = (
    (("PRON",), "personal", "ខ្ញុំ អ្នក គាត់ នាង វា គេ យើង ពួកយើង ពួកគេ ពួកអ្នក ខ្លួន ឯង ខ្ញុំបាទ"),
    (("PRON",), "interrogative", "អ្វី នរណា អ្នកណា"),
    (("PRON", "DET"), "demonstrative", "នេះ នោះ ទាំងនេះ ទាំងនោះ"),
    (("NOUN",), "", "សៀវភៅ ប្រាក់ ផ្ទះ សាលា សាលារៀន គ្រូ សិស្ស កូន កុមារ មនុស្ស ស្ត្រី បុរស ការងារ ក្រុមហ៊ុន ពេល ពេលវេលា ថ្ងៃ ខែ ឆ្នាំ ព្រឹក ល្ងាច យប់ អាហារ បាយ ទឹក តែ កាហ្វេ ផ្សារ ហាង ផ្លូវ ឡាន រថយន្ត ម៉ូតូ កង់ កុំព្យូទ័រ ទូរស័ព្ទ ភាសា ភាសាខ្មែរ ខ្មែរ សំណួរ ចម្លើយ ព័ត៌មាន បច្ចេកវិទ្យា កម្មវិធី ឯកសារ រូបភាព លេខ ទិន្នន័យ ប្រទេស ក្រុង ភូមិ រាជធានី ស្រុក ខេត្ត ឪពុក ម្តាយ បង ប្អូន មិត្ត មិត្តភក្តិ សុខភាព អ្នកគ្រូ លោកគ្រូ គ្រួសារ សង្គម សាកលវិទ្យាល័យ មន្ទីរពេទ្យ ចំនួន រឿង តម្លៃ ហេតុផល កន្លែង មុខ មាត់ ដៃ ជើង"),
    (("PROPN",), "", "កម្ពុជា ភ្នំពេញ បាត់ដំបង សៀមរាប"),
    (("VERB",), "", "អាន សរសេរ រៀន បង្រៀន ដឹង យល់ និយាយ ស្តាប់ ឃើញ មើល គិត ស្រឡាញ់ ចូលចិត្ត ញ៉ាំ ស៊ី ហូប ផឹក ទៅ មក ចូល ចេញ រស់ មាន ធ្វើ ធ្វើការ ទិញ លក់ ផ្តល់ ឱ្យ អោយ យក ដាក់ បើក បិទ សួរ ឆ្លើយ ដើរ រត់ ជិះ លេង ចាំ រង់ចាំ ជួយ រក ស្វែងរក ប្រើ ប្រើប្រាស់ បកប្រែ សិក្សា ទទួល សុំ ស្នើ ចង់ ត្រូវការ បញ្ចប់ សម្រាក ធ្វើដំណើរ គ្មាន"),
    (("ADJ",), "", "ល្អ អាក្រក់ ធំ តូច ថ្មី ចាស់ ស្រស់ ឆ្ងាញ់ ងាយ ពិបាក ត្រឹមត្រូវ សំខាន់ សប្បាយ ឈឺ ភ្លឺ ងងឹត ក្តៅ ត្រជាក់ ខ្ពស់ ទាប ខ្លី វែង ក្រហម ខៀវ ស លឿង ខ្មៅ"),
    (("ADJ", "ADV"), "", "លឿន យឺត ស្អាត ពីរោះ"),
    (("ADV",), "degree", "ណាស់ ពេក ជាង កាន់តែ តិច ច្រើន"),
    (("ADV",), "", "ឥឡូវ ឥឡូវនេះ ម្សិលមិញ ថ្ងៃនេះ ថ្ងៃស្អែក មុន បន្ទាប់ ញឹកញាប់ ឆាប់ បន្តិច ស្ទើរ តែងតែ ជានិច្ច ប៉ុណ្ណោះ ឆ្ងាយ ជិត ទីនេះ ទីនោះ ក៏"),
    (("AUX",), "progressive", "កំពុង កំពុងតែ"),
    (("AUX",), "habitual", "ធ្លាប់"),
    (("ADP", "AUX"), "", "នឹង"),
    (("VERB", "AUX"), "", "បាន"),
    (("AUX", "VERB"), "", "អាច គួរ ត្រូវ"),
    (("AUX", "ADP"), "copula", "ជា"),
    (("AUX",), "copula", "គឺ"),
    (("VERB", "ADP"), "", "នៅ"),
    (("ADP",), "", "ក្នុង លើ ក្រោម ពី ដល់ តាម ចំពោះ ដើម្បី សម្រាប់ រវាង ជាមួយ ដោយ អំពី ក្បែរ ក្រៅ ចាប់ពី រហូតដល់"),
    (("CCONJ",), "", "និង ឬ ឬក៏ ប៉ុន្តែ"),
    (("PART", "CCONJ"), "", "ហើយ"),
    (("SCONJ",), "", "ព្រោះ ពីព្រោះ បើ ប្រសិនបើ ទោះបី ដូច្នេះ"),
    (("SCONJ", "PRON"), "relative", "ដែល"),
    (("DET", "PRON"), "interrogative", "ណា ប៉ុន្មាន"),
    (("PART",), "negation", "មិន ពុំ កុំ មិនមែន មិនទាន់"),
    (("PART",), "question", "តើ"),
    (("PART", "INTJ"), "", "ទេ"),
    (("PART",), "question_final", "ឬទេ"),
    (("PART",), "additive", "ដែរ"),
    (("PART",), "sequence", "សិន"),
    (("PART",), "appeal", "ណា៎"),
    (("VERB", "PART"), "", "ចុះ"),
    (("INTJ",), "polite_response", "បាទ ចាស ចា៎ ចា"),
    (("INTJ",), "", "សួស្តី ជម្រាបសួរ អរគុណ អូ អូហូ"),
    (("NUM",), "", "សូន្យ មួយ ពីរ បី បួន ប្រាំ ប្រាំមួយ ប្រាំពីរ ប្រាំបី ប្រាំបួន ដប់ ម្ភៃ សាមសិប សែសិប ហាសិប ហុកសិប ចិតសិប ប៉ែតសិប កៅសិប រយ ពាន់ ម៉ឺន សែន លាន"),
    (("NOUN",), "", "នាក់ រូប ក្បាល គ្រឿង កែវ ដើម ច្បាប់ គូ ខ្នង ដុំ សន្លឹក"),
)

_NEGATION = frozenset(("មិន", "ពុំ", "កុំ", "មិនមែន", "មិនទាន់"))
_CLASSIFIERS = frozenset(("នាក់", "រូប", "ក្បាល", "គ្រឿង", "កែវ", "ដើម", "ច្បាប់", "គូ", "ខ្នង", "ដុំ", "សន្លឹក"))
_DEMONSTRATIVES = frozenset(("នេះ", "នោះ", "ទាំងនេះ", "ទាំងនោះ"))
_LINE_BREAKS = frozenset("\r\n\f\u2028\u2029")
_PREDICATE_SKIP = _NEGATION | {"ក៏", "តែ"}
# Aspect/discourse roles are orthogonal to the corpus POS convention. In
# particular, khPOS often calls modal/aspect words VERB or ADV rather than AUX.
_INDEPENDENT_ROLES = frozenset((
    "negation", "negative_final", "negative_response", "question", "question_final",
    "progressive", "habitual", "future", "perfective", "ability", "advisability",
    "necessity", "completion", "coordination", "additive", "polite_response",
    "sequence", "appeal", "directive_final", "reduplication", "classifier", "manner", "degree",
))


@lru_cache(maxsize=1)
def _starter_lexicon():
    entries = {}
    for tags, role, words in _GROUPS:
        for word in words.split():
            if word in entries:
                raise RuntimeError("Duplicate KET-Tagger starter entry: " + word)
            entries[word] = (tags, role)
    return MappingProxyType(entries)


def _custom_lexicon(lexicon):
    if lexicon is None:
        return {}
    if not isinstance(lexicon, Mapping):
        raise TypeError("lexicon must be a mapping of words to POS tags")
    entries = {}
    for word, labels in lexicon.items():
        if not isinstance(word, str):
            raise TypeError("lexicon words must be str")
        if not word or any(char.isspace() or char == "\u200b" for char in word):
            raise ValueError("lexicon words must be nonempty, without whitespace or ZWSP")
        if isinstance(labels, str):
            labels = (labels,)
        else:
            if isinstance(labels, (set, frozenset, Mapping)):
                raise TypeError("lexicon tag alternatives must be ordered")
            try:
                labels = tuple(labels)
            except TypeError as exc:
                raise TypeError("lexicon tags must be a tag or an ordered iterable of tags") from exc
        if not labels:
            raise ValueError("each lexicon word needs at least one POS tag")
        unique = []
        for label in labels:
            if not isinstance(label, str):
                raise TypeError("every POS tag must be str")
            if label not in _LABELS:
                raise ValueError("unknown POS tag: " + label)
            if label not in unique:
                unique.append(label)
        entries[word] = tuple(unique)
    return entries


class KhmerTagger:
    """Reusable offline POS tagger, with local vocabulary overrides.

    lexicon maps a contiguous word to a POS tag or ordered alternatives; its
    first tag wins and contextual rules never override an explicit user tag.
    custom_words changes segmentation only. No shared dictionaries are edited.
    model='compact' uses bundled CC BY-NC-SA research weights; 'rules' retains
    the MIT authored v1 helper. A local gzip JSON model path is also accepted.
    """

    def __init__(self, lexicon=None, *, custom_words=None, model="compact"):
        self._custom = MappingProxyType(_custom_lexicon(lexicon))
        words = _validated_words(custom_words) if custom_words is not None else set()
        if any(any(char.isspace() or char == "\u200b" for char in word) for word in words):
            raise ValueError("custom_words must be contiguous words without whitespace or ZWSP")
        self._words = frozenset(words | set(self._custom))
        if not isinstance(model, (str, os.PathLike)):
            raise TypeError("model must be 'compact', 'rules', or a local gzip JSON path")
        if not os.fspath(model):
            raise ValueError("model must not be empty")
        self._model_choice, self._loaded_model = os.fspath(model), None

    def _model(self):
        if self._model_choice == "rules":
            return None
        if self._loaded_model is None:
            from .compact_pos import CompactPOS, default_model
            loaded = default_model() if self._model_choice == "compact" else CompactPOS(self._model_choice)
            self._loaded_model = loaded
        return self._loaded_model

    def tag(self, text, *, with_spans=False):
        """Return (word, tag) pairs, or TaggedToken explanations with spans.

        Whitespace and ZWSP separators are omitted; all returned offsets index
        the unchanged input, in Python code points with exclusive end offsets.
        Role heuristics stop at punctuation and line breaks. Candidates are possible
        lexical analyses, not confidence scores or exhaustive disambiguation.
        """
        _require_text(text)
        if not isinstance(with_spans, bool):
            raise TypeError("with_spans must be bool")
        model = self._model()
        spans = model.segment(text, self._words) if model is not None else khseg_spans(text, custom_words=self._words)
        tokens = self._tag_spans(spans)
        return tokens if with_spans else [(token.text, token.tag) for token in tokens]

    def _tag_spans(self, spans):
        spans = list(spans)
        rules = self._rules_spans(spans)
        model = self._model()
        if model is None or not rules:
            return rules
        from .compact_pos import public_tag
        # Keep hard line/sentence boundaries, and include final punctuation in
        # the model sentence. Commas/colons remain useful internal context.
        predicted, batch = [], []
        for span in spans:
            if span.kind in ("whitespace", "boundary"):
                if any(c in _LINE_BREAKS for c in span.text) and batch:
                    predicted.extend(model.predict(batch))
                    batch = []
                continue
            batch.append(span.text)
            if span.text in ("។", "៕", "?", "!"):
                predicted.extend(model.predict(batch))
                batch = []
        if batch:
            predicted.extend(model.predict(batch))
        if len(predicted) != len(rules):
            raise RuntimeError("Compact POS adapter changed token count")
        output = []
        for token, native in zip(rules, predicted):
            if token.rule == "user.lexicon":
                output.append(token)
                continue
            tag = public_tag(token.text, native)
            role = token.role if token.tag == tag or token.role in _INDEPENDENT_ROLES else ""
            role = {"M": "classifier", "DBL": "reduplication", "QT": "question", "RPN": "relative"}.get(native, role)
            if token.rule in ("unicode.number", "unicode.punctuation", "unicode.symbol", "khmer.reduplication"):
                tag, role = token.tag, token.role
            candidates = [tag]
            distribution = model.lexical.get(token.text, ())
            for index, count in sorted(distribution, key=lambda pair: (-pair[1], pair[0])):
                candidate = public_tag(token.text, model.labels[index])
                if candidate not in candidates:
                    candidates.append(candidate)
            status = "word seen in training" if token.text in model.word_counts else "word unseen in training; model prediction may be wrong"
            reason = "Compact CRF predicted {} ({}).".format(native, status)
            if tag != public_tag(token.text, native):
                reason += " Public label follows the Unicode token type."
            if role and token.role == role:
                reason += " Role heuristic: " + token.reason
            output.append(TaggedToken(token.text, token.start, token.end, tag, _LABELS[tag],
                                      role, tuple(candidates), "model.crf", reason))
        return output

    def _rules_spans(self, spans):
        # This internal path also allows the research script to measure tags
        # at externally supplied gold boundaries, separately from raw text.
        items, groups, endings, clause = [], {}, {}, 0
        starter = _starter_lexicon()
        for span in spans:
            if span.kind in ("whitespace", "boundary"):
                if any(char in _LINE_BREAKS for char in span.text):
                    clause += 1
                continue
            items.append((span, clause))
            if span.kind == "punctuation":
                endings[clause] = span.text
                clause += 1
            else:
                groups.setdefault(clause, []).append(len(items) - 1)

        analyses = []
        for span, _ in items:
            if span.text in self._custom:
                analyses.append((self._custom[span.text], "custom"))
            elif span.text == "ៗ":
                analyses.append((("PART",), "reduplication"))
            elif span.kind == "punctuation":
                analyses.append((("PUNCT",), ""))
            elif span.text.isdecimal():
                analyses.append((("NUM",), ""))
            elif span.text in starter:
                analyses.append(starter[span.text])
            elif all(unicodedata.category(char).startswith("S") for char in span.text):
                analyses.append((("SYM",), ""))
            else:
                analyses.append((("X",), "foreign" if span.kind in ("latin", "other") else "unknown"))

        contexts = {}
        for number, indexes in groups.items():
            negative = any(items[i][0].text in _NEGATION for i in indexes)
            question = endings.get(number) == "?" or any(items[i][0].text in ("តើ", "ឬទេ") for i in indexes)
            for offset, index in enumerate(indexes):
                contexts[index] = (indexes, offset, negative, question)

        result = []
        for index, (span, _) in enumerate(items):
            candidates, role = analyses[index]
            tag, rule = candidates[0], "lexicon"
            reason = "Known word in the authored starter lexicon; context may admit other analyses."
            word = span.text
            if role == "custom":
                rule, reason = "user.lexicon", "Explicit local lexicon; first supplied tag is preserved."
            elif tag == "X":
                rule, reason = "unknown", "No entry in the small tagging lexicon; no POS guessed."
            elif tag == "PUNCT":
                rule, reason = "unicode.punctuation", "Punctuation token; contextual rules stop here."
            elif tag == "NUM" and word.isdecimal():
                rule, reason = "unicode.number", "Khmer or other Unicode decimal digits."
            elif tag == "SYM":
                rule, reason = "unicode.symbol", "Unicode symbol; no lexical POS inferred."
            elif word == "ៗ":
                rule, reason = "khmer.reduplication", "Khmer repetition marker; its scope is not inferred."
            elif index in contexts:
                indexes, offset, negative, question = contexts[index]
                prev_index = indexes[offset - 1] if offset else None
                next_index = indexes[offset + 1] if offset + 1 < len(indexes) else None
                prev_tag = analyses[prev_index][0][0] if prev_index is not None else None
                next_tag = analyses[next_index][0][0] if next_index is not None else None
                final = next_index is None

                def following_predicate():
                    # Bound lookahead; do not search across a noun or clause.
                    for following in indexes[offset + 1:offset + 4]:
                        if analyses[following][0][0] in ("VERB", "AUX", "ADJ"):
                            return True
                        if items[following][0].text not in _PREDICATE_SKIP:
                            break
                    return False

                if word in _DEMONSTRATIVES:
                    tag = "DET" if prev_tag in ("NOUN", "PROPN") else "PRON"
                    rule, reason = "khmer.demonstrative", "After a known noun: determiner; otherwise demonstrative pronoun (heuristic)."
                elif word in _CLASSIFIERS and prev_tag == "NUM":
                    role = "classifier"
                    rule, reason = "khmer.classifier", "Classifier candidate immediately after a numeral; POS remains NOUN."
                elif word == "នឹង" and following_predicate():
                    tag, role = "AUX", "future"
                    rule, reason = "khmer.future", "នឹង before a known predicate or auxiliary chain: future auxiliary candidate."
                elif word == "បាន" and prev_tag == "VERB" and (final or next_tag in ("ADJ", "ADV")):
                    tag, role = "AUX", "ability"
                    rule, reason = "khmer.postverbal_ability", "បាន after a known verb at the clause tail: ability/result candidate."
                elif word == "បាន" and following_predicate():
                    tag, role = "AUX", "perfective"
                    rule, reason = "khmer.perfective", "បាន before a known predicate: perfective auxiliary candidate."
                elif word in ("អាច", "គួរ", "ត្រូវ") and following_predicate():
                    tag, role = "AUX", {"អាច": "ability", "គួរ": "advisability", "ត្រូវ": "necessity"}[word]
                    rule, reason = "khmer.modal", "Modal candidate before a known predicate or auxiliary chain."
                elif word == "នៅ" and prev_tag in ("VERB", "ADJ") and next_tag in ("NOUN", "PROPN", "PRON"):
                    tag, role = "ADP", "location"
                    rule, reason = "khmer.locative", "នៅ between a known predicate and nominal: locative adposition candidate."
                elif word == "ហើយ":
                    tag, role = ("PART", "completion") if final else ("CCONJ", "coordination")
                    rule, reason = "khmer.completion", "Final ហើយ: completion particle; otherwise conjunction candidate."
                elif word == "ទេ":
                    if negative and offset:
                        tag, role = "PART", "negative_final" if final else "negation"
                    elif question:
                        tag, role = "PART", "question_final" if final else "question"
                    elif offset == 0 and final:
                        tag, role = "INTJ", "negative_response"
                    else:
                        tag, role = "PART", "final"
                    rule, reason = "khmer.final_te", "Local negation/question context distinguishes final ទេ from a standalone negative response."
                elif word == "ចុះ" and final and prev_tag in ("VERB", "AUX"):
                    tag, role = "PART", "directive_final"
                    rule, reason = "khmer.directive", "Clause-final ចុះ after a known verb: directive particle candidate."
                elif tag == "ADJ" and "ADV" in candidates and prev_tag in ("VERB", "AUX"):
                    tag, role = "ADV", "manner"
                    rule, reason = "khmer.manner", "Known adjective/adverb after a known verb: manner-adverb candidate."
            result.append(TaggedToken(word, span.start, span.end, tag, _LABELS[tag],
                                      role, candidates, rule, reason))
        return result


@lru_cache(maxsize=1)
def _default_tagger():
    return KhmerTagger()


def khtag(text, *, with_spans=False, lexicon=None, custom_words=None, model="compact"):
    """Easy, offline KET-Tagger; see KhmerTagger.tag for contracts and limits."""
    tagger = _default_tagger() if lexicon is None and custom_words is None and model == "compact" else KhmerTagger(
        lexicon, custom_words=custom_words, model=model)
    return tagger.tag(text, with_spans=with_spans)

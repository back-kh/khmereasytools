"""Lazy POS adapter that preserves word boundaries and avoids a second model."""
import importlib
import threading

from .text_quality import _require_text

_POS_LOCK = threading.RLock()


def _tag_words(words):
    try:
        import khmernltk
        backend = importlib.import_module("khmernltk.pos_tag")
    except ImportError as exc:
        raise ImportError(
            "POS dependencies are unavailable. Install khmereasytools[khmernltk] "
            "(the distribution is named khmer-nltk)."
        ) from exc
    # sklearn-crfsuite reuses a mutable native tagger. Coordinate our callers.
    with _POS_LOCK:
        try:
            if backend.crf_model is None:
                backend.crf_model = backend.load_model(backend.model_path)
            labels = backend.crf_model.predict([backend.create_word_features(words)])[0]
        except AttributeError as exc:
            raise RuntimeError("Incompatible khmer-nltk POS backend; reinstall khmereasytools[khmernltk].") from exc
        if len(labels) != len(words):
            raise RuntimeError("POS backend returned an unexpected number of labels")
        return [(word, str(label)) for word, label in zip(words, labels)]


def tag_text(text, *, custom_words=None):
    from .segmentation import _validated_words
    from .sentences import khsentences
    from .tools import khseg
    _require_text(text)
    custom = _validated_words(custom_words) if custom_words is not None else None
    result = []
    for sentence in khsentences(text):
        words = khseg(sentence, custom_words=custom)
        if words:
            result.extend(_tag_words(words))
    return result

"""Versioned, locally bundled dictionaries. No network access at runtime."""

from functools import lru_cache
import math
from pathlib import Path


@lru_cache(maxsize=2)
def _words(source="expanded"):
    if source not in ("expanded", "legacy"):
        raise ValueError("dictionary must be 'expanded', 'legacy', or an iterable of words")
    directory = Path(__file__).parent / "data"
    words = set((directory / "legacy_words.txt").read_text(encoding="utf-8").splitlines())
    if source == "expanded":
        words.update((directory / "khmer_words.txt").read_text(encoding="utf-8").splitlines())
    return frozenset(words)


def get_khmer_dictionary(source="expanded"):
    """Return an independent mutable copy; use source='legacy' for 0.4's lexicon."""
    return set(_words(source))


@lru_cache(maxsize=1)
def _frequency_costs():
    """Integer negative log unigram probabilities, with add-one smoothing."""
    path = Path(__file__).parent / "data" / "word_frequencies.txt"
    counts = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        word, count = line.rsplit("\t", 1)
        counts[word] = int(count)
    total = sum(counts.values()) + len(_words("expanded"))
    # Integers make path comparisons reproducible and avoid accumulated floats.
    return ({word: max(1, round(-math.log((count + 1) / total) * 1000))
             for word, count in counts.items()}, round(math.log(total) * 1000))

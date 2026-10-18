"""Versioned, locally bundled dictionaries. No network access at runtime."""

from functools import lru_cache
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

# Restored source provenance

The inspected GitHub baseline was commit `ae40f21` on `main`. It contained a root `__init__.py` importing `.tools`, but no `tools.py` or `khmereasytools/` package directory. Its `find_packages()` configuration therefore discovered no package.

The missing package was recovered from this project's public PyPI **0.3.8 source distribution**, not reconstructed from README examples:

- Archive: [khmereasytools-0.3.8.tar.gz](https://files.pythonhosted.org/packages/b1/03/a6d72cfdbb7bb031d8df47f2608ff1b9fb6c673fec0e255b3ae0a380baf5/khmereasytools-0.3.8.tar.gz)
- SHA-256 verified before extraction: `5333e0b356be2f45ec54b7f91c1db56ad4b73d68a283452f85f078f77e54479e`
- Files restored: `khmereasytools/__init__.py`, `khmereasytools/tools.py`.
- Original project author and MIT license retained.

The inherited 213-entry word dictionary and 379-entry stop-word set were preserved. Subsequent changes bounded the legacy longest-match search by dictionary word length, made optional imports lazy, and closed OCR images with a context manager. New APIs live in separate modules.

The legacy README's claimed outputs for keyword extraction and syllabification did not match the recovered implementation. Updated examples avoid implying accuracy that the implementation does not provide. The unrelated `KH-HTML-Parser` example is unchanged and still requires BeautifulSoup separately.

The old root initializer and stale checked-in `PKG-INFO` were removed. Build metadata is now generated from `setup.py`, and `pyproject.toml` declares the build backend. The restored implementation was first prepared as **0.4.0.dev0**, then promoted to **0.4.0** for the requested PyPI release.

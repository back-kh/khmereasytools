# Optional online translation

`khtranslate(text, target="en", source="km")` is a small client for the official Google Cloud Translation Basic REST API. It returns translated plain text. Google lists Khmer as `km` in its [supported languages](https://docs.cloud.google.com/translate/docs/languages). This package does not contain a translation model or provide offline/free translation.

## Explicit setup

1. Create/select your Google Cloud project and enable Cloud Translation, with provider billing/quota settings appropriate to your use.
2. Create a key restricted to the Cloud Translation API and suitable application restrictions. Follow the provider's [API-key guidance](https://docs.cloud.google.com/docs/authentication/api-keys-use).
3. Set `GOOGLE_TRANSLATE_API_KEY` in your local environment. Keep the key out of source control, shell command arguments, screenshots, and bug reports. An application may instead supply `api_key=` from its own credential storage.

```python
from khmereasytools import khtranslate, TranslationError

english = khtranslate("សួស្តី", target="en")
khmer = khtranslate("Hello", source="en", target="km")
detected = khtranslate("សួស្តី", source=None, target="en")
```

```bash
khmereasytools translate document.txt --to en
khmereasytools translate english.txt --from en --to km
khmereasytools translate mixed.txt --from auto --to en
```

Each call sends its text to Google and may incur charges under your provider plan. Calls to text, search, POS, or OCR tools do not invoke translation. Importing the package requires no credentials and makes no request.

## Contract and error handling

- A call accepts a `str` up to 5,000 Python code points. This is a conservative client limit; split longer text explicitly. The client does not silently truncate or make multiple billed requests.
- Plain text is sent as UTF-8 JSON with `format="text"`. The key is in the `X-Goog-Api-Key` header, not the URL. The HTTPS endpoint is fixed. Redirects are refused.
- `source=None` requests language detection. Language identifiers must have language-code syntax; the provider checks actual supported codes. Khmer uses `km`, not Tesseract's `khm`.
- `timeout=30.0` controls network operations. There is no automatic retry or fallback to another service. Empty/whitespace-only text and explicitly identical source/target languages return unchanged text without a request.
- Missing credentials, network errors, quota failures, and malformed responses raise `TranslationError`. Errors report safe status hints without echoing request text, keys, or provider response bodies. The CLI exits with status 2.
- Google may return HTML-escaped translation text, so this client decodes entities once. It does not evaluate HTML or alter source files.

Request/response format follows the provider's [translate REST reference](https://docs.cloud.google.com/translate/docs/reference/rest/v2/translate).

## Validation status

Core tests perform actual HTTP round trips to a local server with fixture credentials. They verify UTF-8 payloads, language direction, returned entity decoding, missing-key handling, HTTP failures, connection/timeout errors, response bounds, and refusal to redirect credentials. They do not call Google or measure machine-translation quality.

Live checks are deliberately opt-in and may incur two small translation requests:

```bash
# Configure GOOGLE_TRANSLATE_API_KEY locally first.
KET_RUN_TRANSLATION_TESTS=1 python -m unittest discover -s tests -p test_translation.py -v
```

When explicitly enabled, a missing or unusable credential fails the live test. CI leaves this live check disabled; fork/PR code does not receive translation secrets. Live provider checks have not been run for this update. No translation-quality result is claimed. Even a successful greeting smoke test would not establish quality on documents; that requires independent bilingual review and an appropriate held-out evaluation set.

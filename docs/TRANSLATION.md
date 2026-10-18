# Optional translation functions

`khtranslate(text, target="en", source="km")` returns plain text from an explicitly configured provider. The existing default is Google Cloud Translation Basic. Google lists Khmer as `km` in its [supported languages](https://docs.cloud.google.com/translate/docs/languages). An optional `local_model=` client now supports a separately installed local model. No model or server is bundled in KhmerEasyTools.

## Local Qwen function

```python
from khmereasytools import LocalModel, khtranslate

model = LocalModel("qwen2.5:3b", timeout=120, max_tokens=1024)
english = khtranslate("សួស្តី", target="en", local_model=model)
khmer = khtranslate("Hello", source="en", target="km", local_model=model)
```

```bash
khmereasytools translate document.txt --to en --model qwen2.5:3b --timeout 120
```

Install Ollama and the chosen model separately. For offline use, configure the
Ollama server with downloaded local weights and `OLLAMA_NO_CLOUD=1`, then restart
it; see [official local-only setup](https://docs.ollama.com/faq#how-do-i-disable-ollamas-cloud-features).
The model name is an example of the function's configuration, not a measured
translation-quality recommendation. Qwen Code is a coding-agent CLI and is not
required by this interface; using that CLI by itself does not establish offline
inference. See [Qwen Code](https://github.com/QwenLM/qwen-code).

The local client uses the [Ollama chat API](https://docs.ollama.com/api/chat) with
an explicit loopback origin (default `http://127.0.0.1:11434`), no environment
proxy, redirect, automatic download, retry or cloud fallback. A separately
managed server must itself be configured for local inference. A Google key in
the environment is ignored on this path; supplying `api_key` together with a
local model is an error. The client's own timeout applies. Truncated, empty,
malformed and failed responses raise `TranslationError` through `khtranslate`.
Unlike Google responses, local model text is not HTML-unescaped.

This feature is included as a function only: no live local or cloud translation
quality evaluation was performed. HTTP fixture tests validate the software
contract and do not measure translation accuracy.

## Google Cloud setup

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

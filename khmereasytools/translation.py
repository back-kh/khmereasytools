"""Explicit, credentialed Google Cloud Translation Basic client (plain text)."""

import html
import http.client
import json
import math
import os
import re
import urllib.error
import urllib.request

from .text_quality import _require_text

_API_URL = "https://translation.googleapis.com/language/translate/v2"
_KEY_VARIABLE = "GOOGLE_TRANSLATE_API_KEY"


class TranslationError(RuntimeError):
    """Translation configuration, transport, quota, or provider-response failure."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        # Never forward a credential or source text to a redirected host.
        return None


def _language(code, name):
    if not isinstance(code, str) or not re.fullmatch(r"[a-zA-Z]{2,3}(?:-[a-zA-Z0-9]{2,8})*", code):
        raise ValueError("{} must be a language code such as 'km' or 'en'".format(name))
    return code


def khtranslate(text, target="en", source="km", *, api_key=None, timeout=30.0):
    """Translate plain text through Google Cloud Translation, returning a str.

    Configure GOOGLE_TRANSLATE_API_KEY or pass api_key explicitly. Calling
    this function sends the text to Google and may incur provider charges.
    There is no network activity on import, automatic fallback, or retry.
    source=None asks the provider to detect the language. Khmer uses 'km'.
    This client accepts at most 5,000 code points per call; split longer text
    explicitly. Errors omit source text, credentials, and provider responses.
    """
    _require_text(text)
    target = _language(target, "target")
    if source is not None:
        source = _language(source, "source")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be a finite positive number of seconds")
    if len(text) > 5000:
        raise ValueError("Translate at most 5,000 characters per call; split longer text explicitly")
    if not text.strip() or (source is not None and source.lower() == target.lower()):
        return text
    key = api_key if api_key is not None else os.environ.get(_KEY_VARIABLE)
    if not isinstance(key, str) or not key.strip():
        raise TranslationError("Set GOOGLE_TRANSLATE_API_KEY for an enabled Google Cloud Translation project, or pass api_key")
    if any(char.isspace() for char in key) or any(ord(char) < 33 or ord(char) > 126 for char in key):
        raise TranslationError("The translation API key must contain printable ASCII without whitespace")
    payload = {"q": text, "target": target, "format": "text"}
    if source is not None:
        payload["source"] = source
    request = urllib.request.Request(
        _API_URL, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8",
                 "X-Goog-Api-Key": key, "User-Agent": "khmereasytools"}, method="POST")
    try:
        with urllib.request.build_opener(_NoRedirect()).open(request, timeout=timeout) as response:
            raw = response.read(1048577)
        if len(raw) > 1048576:
            raise TranslationError("Translation provider returned an oversized response")
        result = json.loads(raw.decode("utf-8"))
        translations = result["data"]["translations"]
        if not isinstance(translations, list) or len(translations) != 1:
            raise ValueError("Unexpected translation count")
        translated = translations[0]["translatedText"]
        if not isinstance(translated, str) or not translated.strip():
            raise ValueError("Missing translated text")
        return html.unescape(translated)
    except urllib.error.HTTPError as exc:
        code = exc.code
        exc.close()
        hint = {400: "check language codes and request limits", 401: "check your credentials",
                403: "check your key, API access, and project billing", 429: "quota or rate limit reached"}.get(code, "provider request failed")
        raise TranslationError("Google Cloud Translation HTTP {}: {}".format(code, hint)) from None
    except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException):
        raise TranslationError("Could not contact Google Cloud Translation; check connectivity and timeout") from None
    except (ValueError, KeyError, IndexError, TypeError, UnicodeError):
        raise TranslationError("Google Cloud Translation returned an invalid response") from None

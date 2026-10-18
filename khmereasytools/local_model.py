"""Small, explicit client for a separately installed local Ollama model."""
import http.client
import ipaddress
import json
import math
import re
import urllib.error
import urllib.parse
import urllib.request

from .text_quality import _require_text


class LocalModelError(RuntimeError):
    """Local model configuration, transport, or generation failure."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


class LocalModel:
    """Callable Ollama chat client, for example LocalModel('qwen2.5:3b').

    No model is bundled, downloaded or started. Only a loopback endpoint is
    accepted. Configure Ollama with local weights and OLLAMA_NO_CLOUD=1 for
    offline use; a loopback address alone cannot certify the server's behavior.
    Errors never include prompts or server response bodies. No retries/fallback.
    """

    def __init__(self, model, *, base_url="http://127.0.0.1:11434", timeout=120.0, max_tokens=1024):
        if not isinstance(model, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,199}", model):
            raise ValueError("model must be an explicit locally installed Ollama model name")
        if model.lower().endswith((":cloud", "-cloud")):
            raise ValueError("Choose local model weights, not an Ollama cloud model")
        if not isinstance(base_url, str) or any(c.isspace() for c in base_url):
            raise ValueError("base_url must be a loopback HTTP(S) origin")
        try:
            url = urllib.parse.urlsplit(base_url)
            host = url.hostname
            loopback = host == "localhost" or ipaddress.ip_address(host).is_loopback
            port = url.port
        except (ValueError, TypeError):
            raise ValueError("base_url must be a loopback HTTP(S) origin") from None
        if (url.scheme not in ("http", "https") or not loopback or url.username is not None
                or url.password is not None or url.path not in ("", "/") or url.query or url.fragment
                or port == 0):
            raise ValueError("base_url must be a loopback HTTP(S) origin without credentials or a path")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be a finite positive number of seconds")
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or not 1 <= max_tokens <= 8192:
            raise ValueError("max_tokens must be an integer from 1 to 8192")
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_tokens = max_tokens

    def __call__(self, prompt):
        return self.generate(prompt)

    def generate(self, prompt, *, system="Help with Khmer and English text. Follow the user's requested task."):
        """Return one complete answer; reject truncated or malformed responses."""
        _require_text(prompt)
        _require_text(system)
        if not prompt.strip():
            raise ValueError("prompt must not be empty")
        if len(prompt) + len(system) > 64000:
            raise ValueError("Send at most 64,000 characters per local-model request")
        payload = dict(model=self.model, messages=[{"role": "system", "content": system},
                       {"role": "user", "content": prompt}], stream=False, think=False,
                       options={"temperature": 0, "num_predict": self.max_tokens})
        request = urllib.request.Request(self.base_url + "/api/chat",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": "khmereasytools"}, method="POST")
        try:
            # Never send local document text through an environment proxy.
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
            with opener.open(request, timeout=self.timeout) as response:
                raw = response.read(1048577)
            if len(raw) > 1048576:
                raise LocalModelError("Local model returned an oversized response")
            result = json.loads(raw.decode("utf-8"))
            if result.get("done_reason") == "length":
                raise LocalModelError("Local model reached its output limit; use shorter input or increase max_tokens")
            message = result["message"]
            content = message["content"]
            if (result.get("done") is not True or message.get("role") != "assistant"
                    or message.get("tool_calls") or not isinstance(content, str) or not content.strip()):
                raise ValueError("Expected a complete plain-text assistant response")
            return content
        except urllib.error.HTTPError as exc:
            code = exc.code
            exc.close()
            hint = "check that the named model is installed" if code == 404 else "check the local server and model configuration"
            raise LocalModelError("Local model HTTP {}: {}".format(code, hint)) from None
        except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException):
            raise LocalModelError("Could not contact the local model; start Ollama and check the endpoint and timeout") from None
        except (ValueError, KeyError, IndexError, TypeError, AttributeError, UnicodeError):
            raise LocalModelError("Local model returned an invalid response") from None

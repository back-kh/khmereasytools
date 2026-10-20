"""Read-only, bounded local setup checks without loading optional models."""

import importlib.util
import math
import os
import platform
import re
import shutil
import subprocess
from subprocess import run as _run
from typing import NamedTuple, Tuple


class DoctorCheck(NamedTuple):
    name: str
    status: str
    message: str
    hint: str


class DoctorReport(NamedTuple):
    version: str
    python: str
    platform: str
    checks: Tuple[DoctorCheck, ...]


def _available(module):
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError, AttributeError):
        return False


def khdoctor(*, timeout=5.0):
    """Inspect local configuration; never install, download, OCR, or translate.

    ready means local prerequisites were found, not an accuracy guarantee.
    Translation is only configured/missing: its key is never returned or
    checked against a remote service. Optional models are not imported.
    """
    from . import __version__
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be a finite positive number")
    checks = [DoctorCheck("core", "ready", "Text, KET-Tagger, sentence, extraction and search tools are available.", "")]
    executable = shutil.which("tesseract")
    engine_status, engine_message = "missing", "Tesseract is not on PATH."
    system = platform.system()
    engine_hint = {"Darwin": "Install Tesseract with brew install tesseract, then add khm language data.",
                   "Windows": "Install Tesseract, add its installation directory to PATH, and add khm language data."}.get(
                       system, "Install tesseract-ocr and tesseract-ocr-khm using your system package manager.")
    if executable is not None:
        try:
            result = _run([executable, "--list-langs"], stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=timeout, check=False)
            languages = {line.strip() for line in result.stdout.decode("utf-8", errors="replace").splitlines()
                         if re.fullmatch(r"[A-Za-z0-9_/-]+", line.strip())}
            if result.returncode != 0:
                engine_status, engine_message = "error", "Tesseract could not list language data."
            elif "khm" not in languages:
                engine_message = "Tesseract was found, but khm language data is missing."
                engine_hint = "Install khm.traineddata in tessdata, or set TESSDATA_PREFIX to its containing directory."
            else:
                engine_status, engine_message, engine_hint = "ready", "Tesseract and khm language data were found.", ""
        except (OSError, subprocess.TimeoutExpired):
            engine_status, engine_message = "error", "Tesseract setup check failed or timed out."
    image_modules = all(_available(name) for name in ("PIL", "pytesseract"))
    if image_modules:
        checks.append(DoctorCheck("ocr", engine_status, engine_message, engine_hint))
    else:
        checks.append(DoctorCheck("ocr", "missing", "Optional image OCR packages are missing.",
                                  "Install with: python -m pip install 'khmereasytools[ocr]'"))
    if _available("pypdfium2") and image_modules:
        checks.append(DoctorCheck("pdf", engine_status, engine_message, engine_hint))
    else:
        checks.append(DoctorCheck("pdf", "missing", "Optional PDF/OCR packages are missing.",
                                  "Install with: python -m pip install 'khmereasytools[ocr]'"))
    pos_modules = all(_available(name) for name in ("khmernltk", "sklearn_crfsuite", "pycrfsuite", "sklearn", "numpy", "scipy"))
    checks.append(DoctorCheck("pos", "ready" if pos_modules else "missing",
                              "Optional CRF POS packages were found; models were not loaded." if pos_modules else "Optional CRF POS packages are missing; KET-Tagger works with core.",
                              "" if pos_modules else "Install with: python -m pip install 'khmereasytools[khmernltk]'"))
    configured = bool(os.environ.get("GOOGLE_TRANSLATE_API_KEY", "").strip())
    checks.append(DoctorCheck("translation", "configured" if configured else "missing",
                              "An API key is configured; no live request was made." if configured else "Online translation is not configured.",
                              "" if configured else "Configure GOOGLE_TRANSLATE_API_KEY for Google Cloud Translation when needed."))
    return DoctorReport(__version__, platform.python_version(), system, tuple(checks))

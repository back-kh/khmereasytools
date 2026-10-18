"""Prepare pinned Khmer traineddata for real OCR checks on each CI OS."""
import hashlib
import os
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

REVISION = "87416418657359cb625c412a48b6e1d6d41c29bd"
SHA256 = "47f110575341b322052f3becbefee61a3ecf1ef549352b5d4d33d28afe30d099"


def main():
    executable = shutil.which("tesseract")
    if executable is None and os.name == "nt":
        candidate = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Tesseract-OCR/tesseract.exe"
        if candidate.is_file():
            executable = str(candidate)
            os.environ["PATH"] += os.pathsep + str(candidate.parent)
            if os.environ.get("GITHUB_PATH"):
                with open(os.environ["GITHUB_PATH"], "a", encoding="utf-8") as handle:
                    handle.write(str(candidate.parent) + "\n")
    if executable is None:
        raise RuntimeError("Install Tesseract before running the real OCR checks")
    directory = Path(os.environ.get("RUNNER_TEMP", tempfile.gettempdir())) / "ket-tessdata"
    directory.mkdir(parents=True, exist_ok=True)
    url = "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/{}/khm.traineddata".format(REVISION)
    with urllib.request.urlopen(url, timeout=60) as response:
        data = response.read(10000000)
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise RuntimeError("Khmer traineddata checksum mismatch")
    (directory / "khm.traineddata").write_bytes(data)
    os.environ["TESSDATA_PREFIX"] = str(directory)
    if os.environ.get("GITHUB_ENV"):
        with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as handle:
            handle.write("TESSDATA_PREFIX={}\n".format(directory))
    subprocess.run([executable, "--version"], check=True)
    subprocess.run([executable, "--list-langs"], check=True)


if __name__ == "__main__":
    main()

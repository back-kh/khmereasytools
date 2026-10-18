"""Prepare pinned Khmer traineddata for real OCR checks on each CI OS."""
import argparse
import hashlib
import os
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

REVISION = "87416418657359cb625c412a48b6e1d6d41c29bd"
SHA256 = "47f110575341b322052f3becbefee61a3ecf1ef549352b5d4d33d28afe30d099"
BEST_REVISION = "e12c65a915945e4c28e237a9b52bc4a8f39a0cec"
BEST_SHA256 = "3d2d975e67a319bf1cd67626b12fdebc1e417a4ebef9c9afee01d9927b512815"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--best", action="store_true", help="Prepare a separate optional model for evaluation")
    args = parser.parse_args()
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
    directory = Path(os.environ.get("RUNNER_TEMP", tempfile.gettempdir())) / (
        "ket-tessdata-best" if args.best else "ket-tessdata")
    directory.mkdir(parents=True, exist_ok=True)
    url = "https://raw.githubusercontent.com/tesseract-ocr/{}/{}/khm.traineddata".format(
        "tessdata_best" if args.best else "tessdata_fast", BEST_REVISION if args.best else REVISION)
    with urllib.request.urlopen(url, timeout=60) as response:
        data = response.read(10000000)
    if hashlib.sha256(data).hexdigest() != (BEST_SHA256 if args.best else SHA256):
        raise RuntimeError("Khmer traineddata checksum mismatch")
    (directory / "khm.traineddata").write_bytes(data)
    # Preparing the optional model must not change subsequent default OCR runs.
    variable = "KET_BEST_TESSDATA" if args.best else "TESSDATA_PREFIX"
    os.environ[variable] = str(directory)
    if os.environ.get("GITHUB_ENV"):
        with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as handle:
            handle.write("{}={}\n".format(variable, directory))
    print("{}={}".format(variable, directory), flush=True)
    subprocess.run([executable, "--version"], check=True)
    subprocess.run([executable, "--tessdata-dir", str(directory), "--list-langs"], check=True)


if __name__ == "__main__":
    main()

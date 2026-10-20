"""Evaluate the existing mixed-language OCR API in a fresh wheel environment."""
import hashlib
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    wheels = list((ROOT / "dist").glob("*.whl"))
    if len(wheels) != 1:
        raise ValueError("Expected one wheel")
    subprocess.run([sys.executable, str(ROOT / "scripts/fetch_accuracy_data.py")], check=True)
    with tempfile.TemporaryDirectory(prefix="ket-mixed-installed-") as temporary:
        environment = Path(temporary) / "venv"
        venv.create(str(environment), with_pip=True)
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run([str(python), "-m", "pip", "install", str(wheels[0]) + "[ocr]", "-r",
                        str(ROOT / "requirements-evaluation.txt")], check=True)
        subprocess.run([str(python), "-m", "pip", "check"], check=True)
        variables = dict(os.environ, KET_VALIDATION_WHEEL_SHA256=hashlib.sha256(wheels[0].read_bytes()).hexdigest())
        subprocess.run([str(python), str(ROOT / "scripts/evaluate_mixed_ocr.py"),
                        "--partition", "reserved", "--prepare-models", "--installed", "--pdf-transport",
                        "--output", str(ROOT / "validation-results/mixed-ocr")],
                       cwd=temporary, env=variables, check=True)


if __name__ == "__main__":
    main()

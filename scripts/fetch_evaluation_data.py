"""Fetch khPOS OPEN-TEST for separately licensed, noncommercial research only.

This corpus is never imported by the library or included in distributions.
Review https://github.com/ye-kyaw-thu/khPOS before using this optional script.
"""
import hashlib
import urllib.request
from pathlib import Path

REVISION = "0211405c145b0a340ad558569bd06c946b2296b4"
SHA256 = "1b10b866263e6beb93cbf5c249ffc6a5d4d11dbc7beb90717c9f4e14cb152869"
URL = ("https://raw.githubusercontent.com/ye-kyaw-thu/khPOS/" + REVISION +
       "/corpus-draft-ver-1.0/data/OPEN-TEST.word")


def main():
    with urllib.request.urlopen(URL, timeout=30) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise SystemExit("Corpus checksum mismatch")
    directory = Path(__file__).resolve().parents[1] / ".evaluation"
    directory.mkdir(exist_ok=True)
    path = directory / "OPEN-TEST.word"
    path.write_bytes(data)
    print("Saved evaluation-only data to {} (CC BY-NC-SA 4.0; see upstream terms).".format(path))


if __name__ == "__main__":
    main()

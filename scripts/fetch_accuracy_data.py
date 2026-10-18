"""Fetch external accuracy data to ignored .evaluation; review licenses first.

ALT Khmer annotations: CC BY-NC-SA 4.0, research evaluation only here.
KHOB: upstream MIT notice. Neither dataset is shipped with this package.
"""
import hashlib
import io
import urllib.request
import zipfile
from pathlib import Path

ALT = "https://www2.nict.go.jp/astrec-att/member/mutiyama/ALT/"
FILES = (
    ("OPEN-TEST.word", "https://raw.githubusercontent.com/ye-kyaw-thu/khPOS/"
     "0211405c145b0a340ad558569bd06c946b2296b4/corpus-draft-ver-1.0/data/OPEN-TEST.word",
     "1b10b866263e6beb93cbf5c249ffc6a5d4d11dbc7beb90717c9f4e14cb152869"),
    ("OPEN-TEST.tag", "https://raw.githubusercontent.com/ye-kyaw-thu/khPOS/"
     "0211405c145b0a340ad558569bd06c946b2296b4/corpus-draft-ver-1.0/data/OPEN-TEST.tag",
     "1714a6aeb0bedb1df6dde577a409799f6700bfd97f107cdf7c5a2624090b2cd4"),
    ("alt/km-nova-181101.zip", ALT + "km-nova-181101.zip",
     "0c6457d4a3327f3dc0b381704cbad71af120e963bfa1cdb06765fa0ed0c9098a"),
    ("alt/URL-test.txt", ALT + "URL-test.txt",
     "6d67d6bf5c4e7574116355d71ef927c66aca2f7ab7267b14591ea250f24ec722"),
    ("khob/khob-level-1-updated-31012026.zip",
     "https://drive.usercontent.google.com/download?"
     "id=11aFZJae4zod1joZndAcDRI61c-QJ36Ry&export=download&confirm=t",
     "976b050d5e8a24e9654223bab2520b9cd750f5ebaa7024e7c594adf02886a703"),
)


def main():
    root = Path(__file__).resolve().parents[1] / ".evaluation"
    for relative, url, expected in FILES:
        path = root / relative
        if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == expected:
            data = path.read_bytes()
        else:
            with urllib.request.urlopen(url, timeout=60) as response:
                data = response.read(100 * 1024 * 1024 + 1)
            if len(data) > 100 * 1024 * 1024:
                raise ValueError("Download exceeds evaluation limit")
            if hashlib.sha256(data).hexdigest() != expected:
                raise ValueError("Source changed: checksum mismatch for " + relative)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        if relative.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                if sum(info.file_size for info in archive.infolist()) > 250 * 1024 * 1024:
                    raise ValueError("Expanded archive exceeds evaluation limit")
                for name in archive.namelist():
                    part = Path(name)
                    if part.is_absolute() or ".." in part.parts or name.endswith("/"):
                        continue
                    if relative.startswith("alt/"):
                        if part.name not in ("data_km.km-tok.nova", "data_km.km-tag.nova", "README.txt"):
                            continue
                        destination = path.parent / part.name
                    else:
                        if name.startswith("__MACOSX/"):
                            continue
                        destination = path.parent / "level1" / part
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(archive.read(name))
        print("Verified " + relative + ": " + expected)


if __name__ == "__main__":
    main()

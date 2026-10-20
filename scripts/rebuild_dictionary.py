"""Reproduce the bundled ICU adaptation from its pinned, verified source."""
import argparse
import hashlib
import json
import unicodedata
import urllib.request
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify rather than overwrite the bundled word list")
    args = parser.parse_args()
    directory = Path(__file__).resolve().parents[1] / "khmereasytools/data"
    manifest = json.loads((directory / "dictionary_manifest.json").read_text(encoding="utf-8"))
    url = "https://raw.githubusercontent.com/unicode-org/icu/{}/{}".format(manifest["revision"], manifest["source_path"])
    with urllib.request.urlopen(url, timeout=30) as response:
        raw = response.read()
    if hashlib.sha256(raw).hexdigest() != manifest["source_sha256"]:
        raise SystemExit("Source checksum mismatch; refusing to rebuild")
    words = {line.strip() for line in raw.decode("utf-8-sig").splitlines()
             if line.strip() and not line.lstrip().startswith("#")}
    words = {word for word in words if all("\u1780" <= char <= "\u17ff" and
             unicodedata.category(char)[0] in "LM" for char in word)}
    output = ("\n".join(sorted(words)) + "\n").encode("utf-8")
    if len(words) != manifest["retained_entries"] or hashlib.sha256(output).hexdigest() != manifest["output_sha256"]:
        raise SystemExit("Rebuilt output disagrees with provenance manifest")
    target = directory / "khmer_words.txt"
    if args.check:
        if target.read_bytes() != output:
            raise SystemExit("Bundled data differs from its pinned source adaptation")
    else:
        target.write_bytes(output)
    print("Verified {} ICU lexicon entries.".format(len(words)))


if __name__ == "__main__":
    main()

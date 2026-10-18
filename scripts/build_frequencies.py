"""Reproduce compact segmentation counts from the MIT SIL NRSI source."""
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVISION = "54abc6b87f4ffa6a0c95c09836c7c86648002273"
BASE = "https://raw.githubusercontent.com/silnrsi/khmerlbdict/" + REVISION + "/"
SOURCE_SHA = "213ce026b8e20cdf70ef38a8ebc4cca0117ebbe65dabac4c8483d99eebb53efd"
LICENSE_SHA = "73ceaad383a32a95b19bff137ed34717715a4f4b101145b135d7d756a97e669d"


def fetch(name, expected):
    with urllib.request.urlopen(BASE + name, timeout=30) as response:
        data = response.read(2000000)
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("Checksum mismatch for " + name)
    return data


def main():
    directory = ROOT / "khmereasytools/data"
    vocabulary = set((directory / "khmer_words.txt").read_text(encoding="utf-8").splitlines())
    vocabulary.update((directory / "legacy_words.txt").read_text(encoding="utf-8").splitlines())
    source = fetch("src/seafreq.txt", SOURCE_SHA)
    license_data = fetch("LICENSE", LICENSE_SHA)
    counts, skipped = {}, 0
    for line in source.decode("utf-8-sig").splitlines():
        if not line.strip():
            continue
        word, value = line.rsplit("\t", 1)
        count = int(value)
        if word in vocabulary and count > 0:
            counts[word] = counts.get(word, 0) + count
        else:
            skipped += 1
    output = "".join("{}\t{}\n".format(word, counts[word]) for word in sorted(counts)).encode("utf-8")
    (directory / "word_frequencies.txt").write_bytes(output)
    (directory / "SIL-LICENSE.txt").write_bytes(license_data)
    (directory / "FREQUENCY-NOTICE.txt").write_text(
        "Segmentation frequencies adapted from SIL NRSI khmerlbdict.\n"
        "Copyright (c) 2015 SIL NRSI. Distributed under the upstream MIT notice;\n"
        "see SIL-LICENSE.txt. SIL attributes the source frequency list to SEALang.\n"
        "Source: " + BASE + "src/seafreq.txt\n"
        "Only existing dictionary entries are retained; no evaluation-derived\n"
        "vocabulary, counts, or trained weights are included.\n"
        "See frequency_manifest.json for source and output checksums.\n",
        encoding="utf-8")
    manifest = dict(
        source="silnrsi/khmerlbdict src/seafreq.txt", revision=REVISION,
        source_url=BASE + "src/seafreq.txt", source_sha256=SOURCE_SHA,
        license="MIT, copyright 2015 SIL NRSI", license_sha256=LICENSE_SHA,
        upstream_origin="SEALang Khmer frequency-based wordlist, as attributed by SIL NRSI",
        output_sha256=hashlib.sha256(output).hexdigest(), entries=len(counts),
        total_count=sum(counts.values()), skipped=skipped,
        adaptation="Exact existing dictionary intersection; positive integer counts; sum duplicates; sorted UTF-8 TSV. No new vocabulary or evaluation data.")
    (directory / "frequency_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

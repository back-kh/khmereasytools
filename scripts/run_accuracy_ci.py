"""Run paired corpus comparisons in a fresh wheel venv, without source imports."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import venv
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "43dd811dc969b8357cf8eb1608f8f71379514d36"


def compare(before, after):
    old = before["ocr"]["public_default"]
    new = after["ocr"]["public_default"]
    pairs = {
        "khpos_segmentation_f1": (
            before["khpos_segmentation"]["metrics"]["segmentation"]["f1"],
            after["khpos_segmentation"]["metrics"]["segmentation"]["f1"]),
        "alt_word_segmentation_f1": (
            before["alt_words"]["metrics"]["segmentation"]["f1"],
            after["alt_words"]["metrics"]["segmentation"]["f1"]),
        "alt_word_pos_joint_f1": (
            before["alt_words"]["metrics"]["pos_joint"]["f1"],
            after["alt_words"]["metrics"]["pos_joint"]["f1"]),
        "ocr_codepoint_cer": (old["compact_codepoint_cer"], new["compact_codepoint_cer"]),
    }
    return {name: dict(before=a, after=b, delta=b - a) for name, (a, b) in pairs.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=ROOT / "dist")
    parser.add_argument("--reports", type=Path, default=ROOT / "validation-results/accuracy")
    args = parser.parse_args()
    wheels = list(args.dist.resolve().glob("*.whl"))
    if len(wheels) != 1:
        raise ValueError("Expected one built wheel")
    reports = args.reports.resolve()
    reports.mkdir(parents=True, exist_ok=True)
    cache = ROOT / ".evaluation/improvements"
    cache.mkdir(parents=True, exist_ok=True)
    archive_path = cache / "baseline.zip"
    with archive_path.open("wb") as stream:
        subprocess.run(["git", "archive", "--format=zip", BASELINE],
                       cwd=str(ROOT), stdout=stream, check=True)
    baseline_root = cache / "baseline"
    with zipfile.ZipFile(archive_path) as archive:
        for name in archive.namelist():
            relative = Path(name)
            if name.endswith("/") or relative.is_absolute() or ".." in relative.parts:
                continue
            destination = baseline_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(archive.read(name))
    subprocess.run([sys.executable, str(ROOT / "scripts/fetch_accuracy_data.py")], check=True)
    with tempfile.TemporaryDirectory(prefix="ket-accuracy-installed-") as directory:
        environment = Path(directory) / "venv"
        venv.create(str(environment), with_pip=True)
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run([str(python), "-m", "pip", "install", str(wheels[0]) + "[all]",
                        "-r", str(ROOT / "requirements-evaluation.txt")], check=True)
        subprocess.run([str(python), "-m", "pip", "check"], check=True)
        runner = [str(python), str(ROOT / "scripts/compare_improvements.py"),
                  "--partition", "reserved", "--output", str(reports)]
        subprocess.run(runner + ["--name", "baseline_reserved", "--runtime-root", str(baseline_root)],
                       cwd=directory, check=True)
        subprocess.run(runner + ["--name", "improved_reserved", "--installed"],
                       cwd=directory, check=True)
    before = json.loads((reports / "baseline_reserved.json").read_text(encoding="utf-8"))
    after = json.loads((reports / "improved_reserved.json").read_text(encoding="utf-8"))
    summary = dict(
        source_revision=os.environ.get("GITHUB_SHA"), baseline_revision=BASELINE,
        wheel_sha256=hashlib.sha256(wheels[0].read_bytes()).hexdigest(),
        measurements=compare(before, after),
        old_word_model_loaded=before["word_model_loaded"],
        new_word_model_loaded=after["word_model_loaded"],
        new_pos_model_loaded=after["pos_model_loaded"],
        tests="40 OCR images; 1,018 word-annotated ALT sentences; 1,000 khPOS sentences",
        limitations="Reserved from this tuning, previously benchmarked; ALT training overlap possible; OCR labels imperfect.")
    (reports / "comparison.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    for key, values in summary["measurements"].items():
        if key == "ocr_codepoint_cer":
            assert values["after"] <= values["before"], "OCR regression; see paired report"
        else:
            assert values["after"] >= values["before"], key + " regression; see paired report"
    assert not after["word_model_loaded"] and after["pos_model_loaded"]
    for dataset in ("alt_words", "khpos_segmentation"):
        assert all(not value["alignment_failures"] for value in after[dataset]["metrics"].values())


if __name__ == "__main__":
    main()

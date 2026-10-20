"""Check the offline provenance lock of KET-Tagger bundled in KhmerEasyTools."""

import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath


REPOSITORY = "https://github.com/back-kh/ket-tagger"
LOCK_PATH = "khmereasytools/data/ket_tagger_source.json"
REQUIRED_FILES = frozenset((
    "khmereasytools/tagging.py", "khmereasytools/compact_pos.py",
    "khmereasytools/data/research/ket_pos_v2.json.gz",
    "khmereasytools/data/research/manifest.json",
    "khmereasytools/data/research/LICENSE.txt", "scripts/check_tagger_source.py",
))


def safe_path(root, name):
    """Resolve a canonical repository-relative file without following links."""
    if not isinstance(name, str) or not name or "\\" in name or ":" in name:
        raise ValueError("Invalid component path: {!r}".format(name))
    relative = PurePosixPath(name)
    if (relative.is_absolute() or relative.as_posix() != name or
            any(part in (".", "..") for part in relative.parts)):
        raise ValueError("Component path must stay inside its repository: " + name)
    root = Path(root).resolve()
    target = root
    for part in relative.parts:
        target = target / part
        if target.is_symlink():
            raise ValueError("Component paths must not use symlinks: " + name)
    if root not in target.resolve().parents:
        raise ValueError("Component path escapes repository: " + name)
    return target


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_hashes(root, files):
    if not isinstance(files, dict) or not files or len(files) > 256:
        raise ValueError("Invalid component file table")
    for name, expected in files.items():
        safe_path(root, name)
        if not isinstance(expected, str) or re.fullmatch(r"[0-9a-f]{64}", expected) is None:
            raise ValueError("Invalid SHA-256 for " + str(name))


def verify_files(root, files):
    validate_hashes(root, files)
    failures = []
    for name, expected in sorted(files.items()):
        target = safe_path(root, name)
        if not target.is_file() or sha256(target) != expected:
            failures.append(name)
    if failures:
        raise ValueError("KET-Tagger source mismatch: " + ", ".join(failures))


def check(root, lock=None):
    root = Path(root).resolve()
    if lock is None:
        lock = json.loads(safe_path(root, LOCK_PATH).read_text(encoding="utf-8"))
    if (not isinstance(lock, dict) or lock.get("schema_version") != 1 or
            lock.get("repository") != REPOSITORY or
            not isinstance(lock.get("revision"), str) or
            re.fullmatch(r"[0-9a-f]{40}", lock["revision"]) is None or
            lock.get("software_license") != "MIT" or
            lock.get("model_license") != "CC-BY-NC-SA-4.0"):
        raise ValueError("Invalid KET-Tagger provenance or license")
    managed, support = lock.get("files"), lock.get("support_files")
    validate_hashes(root, managed)
    validate_hashes(root, support)
    if not REQUIRED_FILES.issubset(managed) or set(managed) & set(support):
        raise ValueError("Missing component files or overlapping support files")
    verify_files(root, managed)
    verify_files(root, support)
    manifest = json.loads((root / "khmereasytools/data/research/manifest.json").read_text(encoding="utf-8"))
    model_hash = managed["khmereasytools/data/research/ket_pos_v2.json.gz"]
    if manifest.get("sha256") != model_hash or manifest.get("license") != lock["model_license"]:
        raise ValueError("Bundled model manifest or license does not match the source lock")
    return dict(repository=REPOSITORY, revision=lock["revision"],
                managed_files=len(managed), support_files=len(support),
                model_sha256=model_hash, matches=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        print(json.dumps(check(args.root), indent=2))
    except (OSError, ValueError) as exc:
        parser.exit(1, str(exc) + "\n")


if __name__ == "__main__":
    main()

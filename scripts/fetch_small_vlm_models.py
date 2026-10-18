"""Fetch explicitly selected, revision-pinned research models and verify files."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


def hashes(path):
    size = path.stat().st_size
    sha = hashlib.sha256()
    git = hashlib.sha1(b"blob " + str(size).encode() + b"\0")
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(block)
            git.update(block)
    return size, sha.hexdigest(), git.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--inventory-out", type=Path, required=True)
    args = parser.parse_args()
    from huggingface_hub import snapshot_download
    models = json.loads(args.manifest.read_text(encoding="utf-8"))
    result = {}
    for repository, model in models.items():
        name = repository.rsplit("/", 1)[1]
        if name in {".", ".."}:
            raise ValueError("Invalid model directory")
        for item in model["files"]:
            path = PurePosixPath(item["path"])
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("Unsafe checkpoint file path")
        target = args.destination / name
        snapshot_download(repo_id=repository, revision=model["revision"],
                          allow_patterns=[f["path"] for f in model["files"]],
                          local_dir=str(target), max_workers=2)
        verified = []
        for item in model["files"]:
            size, sha, git = hashes(target / item["path"])
            if item.get("size") is not None and size != item["size"]:
                raise ValueError("Checkpoint file size differs: " + item["path"])
            if item.get("lfs_sha256") and sha != item["lfs_sha256"]:
                raise ValueError("Checkpoint LFS digest differs: " + item["path"])
            if not item.get("lfs_sha256") and item.get("git_blob_id") and git != item["git_blob_id"]:
                raise ValueError("Checkpoint Git digest differs: " + item["path"])
            verified.append(dict(path=item["path"], size=size, sha256=sha))
        result[repository] = dict(revision=model["revision"], directory=name,
                                  card_license=model.get("card_license"), files=verified)
        print("Verified", repository, model["revision"], flush=True)
    args.inventory_out.parent.mkdir(parents=True, exist_ok=True)
    args.inventory_out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

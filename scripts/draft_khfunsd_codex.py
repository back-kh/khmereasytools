"""Produce private Codex transcript drafts for the supplied KH-FUNSD images.

These are model annotations awaiting human review, never OCR ground truth.
The user must explicitly invoke this research script with an authenticated
Codex CLI; the installed KhmerEasyTools package never calls it.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / ".evaluation/kh_funsd_local")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    data = args.data_dir.resolve()
    profile = read(data / "draft-protocol.json")
    if profile.get("runner_sha256") and profile["runner_sha256"] != digest(Path(__file__)):
        raise ValueError("Frozen annotation runner changed")
    for name, key in [("page-selection.json", "source_selection_sha256"),
                      ("transcription-prompt.txt", "prompt_sha256"),
                      ("transcription-schema.json", "schema_sha256")]:
        if digest(data / name) != profile[key]:
            raise ValueError("Frozen annotation profile changed: " + name)
    if subprocess.check_output(["codex", "--version"], text=True).strip() != profile["cli_version"]:
        raise ValueError("Codex CLI version changed")
    pages = read(data / "page-selection.json")["pages"]
    if args.limit is not None:
        pages = pages[:args.limit]
    directory = data / "codex-drafts" / profile["token"]
    directory.mkdir(parents=True, exist_ok=True)
    prompt_template = (data / "transcription-prompt.txt").read_text(encoding="utf-8")
    failures = 0
    for index, page in enumerate(pages, 1):
        if (data / "stop-after-current").exists():
            print("Stopped between pages as requested by the local controller", flush=True)
            break
        path = directory / (page["id"] + ".json")
        if path.exists():
            previous = read(path)
            if previous["draft_token"] != profile["token"] or previous["image_sha256"] != page["image_sha256"]:
                raise ValueError("Cached reference has different provenance")
            if not previous["error"]:
                print(index, "/", len(pages), page["id"], "cached draft", flush=True)
                continue
            # Failed calls remain recorded. Do not silently replace them with
            # a favorable rerun or a transcript derived from a baseline.
            print(index, "/", len(pages), page["id"], "retained failed call", flush=True)
            continue
        image = data / page["image"]
        if digest(image) != page["image_sha256"]:
            raise ValueError("Input image changed")
        response = directory / (page["id"] + ".response.json")
        events = directory / (page["id"] + ".events.jsonl")
        stderr = directory / (page["id"] + ".stderr.log")
        command = ["codex", "exec", "--ephemeral", "--skip-git-repo-check",
                   "--sandbox", "read-only", "--output-schema", str(data / "transcription-schema.json"),
                   "--output-last-message", str(response), "--json", "--image", str(image), "-"]
        for key, value in profile.get("generation_overrides", {}).items():
            command[2:2] = ["--config", key + "=" + json.dumps(value)]
        started = time.monotonic()
        started_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        draft, error = None, None
        try:
            with events.open("w", encoding="utf-8") as stdout, stderr.open("w", encoding="utf-8") as err:
                process = subprocess.run(command,
                    input=prompt_template.replace("{page_id}", page["id"]), text=True,
                    stdout=stdout, stderr=err, cwd=str(data), timeout=profile["timeout_seconds"])
            if process.returncode:
                raise RuntimeError("Codex exited with status " + str(process.returncode))
            event_rows = [json.loads(line) for line in events.read_text().splitlines() if line.strip()]
            tools = [e["item"]["type"] for e in event_rows if e.get("type") == "item.completed"
                     and e["item"]["type"] not in {"agent_message", "reasoning"}]
            if tools:
                raise ValueError("Annotation used tools despite the image-only protocol: " + repr(tools))
            draft = read(response)
            if draft["page_id"] != page["id"]:
                raise ValueError("Returned page identity differs")
            if "[ILLEGIBLE]" in draft["transcript"] and draft["complete"]:
                raise ValueError("Unreadable content cannot be marked complete")
            failures = 0
        except Exception as exc:
            error = type(exc).__name__ + ": " + str(exc)[:500]
            failures += 1
        record = dict(id=page["id"], draft_token=profile["token"],
                      image_sha256=page["image_sha256"], reference_origin="codex_model_draft",
                      human_reviewed=False, configured_model=profile["configured_model"],
                      generation_overrides=profile.get("generation_overrides", {}),
                      started_utc=started_utc, runner_sha256=digest(Path(__file__)),
                      resolved_model_snapshot=profile["resolved_model_snapshot"],
                      seconds=time.monotonic() - started, draft=draft, error=error,
                      events_sha256=digest(events) if events.exists() else None)
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(index, "/", len(pages), page["id"], "characters",
              len(draft["transcript"]) if draft else 0, "human_reviewed False", "error", error, flush=True)
        if failures >= 3:
            raise RuntimeError("Three consecutive annotation calls failed; inspect retained logs")


if __name__ == "__main__":
    main()

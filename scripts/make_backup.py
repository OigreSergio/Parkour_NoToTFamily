#!/usr/bin/env python3
"""Generate the 24-hour backup manifest in the 📲/ folder.

The manifest (``📲/backup-latest.json``) is deliberately ephemeral: the daily
GitHub Actions workflow (``.github/workflows/backup.yml``) deletes it and
regenerates it from scratch every 24 hours, so its ``expires_at`` timestamp is
always at most one day away. It records every branch of the repository with
its current commit SHA and a direct download link, plus checksums of the
bundled datasets, so an admin can verify and restore any line of work.

The full binary backup (a ``git bundle`` with all branches) is NOT committed
to the repository — it is uploaded as a workflow artifact with a 1-day
retention, so it also self-destructs and is recreated every 24 hours.

Usage:
    python3 scripts/make_backup.py            # writes 📲/backup-latest.json
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_SLUG = "OigreSergio/Parkour_NoToTFamily"
REPO_URL = f"https://github.com/{REPO_SLUG}"
ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "📲"
OUT_FILE = OUT_DIR / "backup-latest.json"

# Datasets whose integrity the backup tracks.
DATASETS = ["mobile/assets/data/fountains_roma.json"]


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def branches() -> list[dict]:
    """All branches (remote-tracking if available, else local) with SHAs."""
    out = git(
        "for-each-ref",
        "--format=%(refname:short) %(objectname)",
        "refs/remotes/origin",
        "refs/heads",
    )
    seen: dict[str, str] = {}
    for line in out.splitlines():
        ref, sha = line.rsplit(" ", 1)
        name = ref.removeprefix("origin/")
        if name == "HEAD" or name in seen:
            continue
        seen[name] = sha
    return [
        {
            "name": name,
            "sha": sha,
            "zip_url": f"https://codeload.github.com/{REPO_SLUG}/zip/{sha}",
            "branch_url": f"{REPO_URL}/tree/{name}",
        }
        for name, sha in sorted(seen.items())
    ]


def dataset_checksums() -> list[dict]:
    records = []
    for rel in DATASETS:
        path = ROOT / rel
        if not path.is_file():
            continue
        records.append(
            {
                "path": rel,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "bytes": path.stat().st_size,
            }
        )
    return records


def main() -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    manifest = {
        "backup": "Parkour NoToT Family — full repository backup manifest",
        "repo": REPO_URL,
        "generated_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=24)).isoformat(),
        "rotation": (
            "This file is destroyed and regenerated every 24h by "
            ".github/workflows/backup.yml; the full git bundle artifact of the "
            "same run self-destructs after 1 day."
        ),
        "full_bundle_artifact": f"{REPO_URL}/actions/workflows/backup.yml",
        "branches": branches(),
        "datasets": dataset_checksums(),
        "restore": (
            "Download the bundle artifact, then: "
            "git clone parkour-notot-full-backup.bundle restored/ "
            "(contains every branch); or download a branch zip_url above."
        ),
    }
    OUT_DIR.mkdir(exist_ok=True)
    OUT_FILE.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote {OUT_FILE} ({len(manifest['branches'])} branches)")


if __name__ == "__main__":
    main()

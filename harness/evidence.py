"""Copy a scored batch into evidence/<batch_id>/ for committing.

    uv run python -m harness.evidence runs/batches/<batch_id>

runs/ is gitignored (big, full of live rows). Evidence keeps what a reviewer
needs to re-check a verdict: the task, fixture, interference, both ground
truths, the finding read back from the database, the agent's run record and
answer, the score, and a one-line-per-call summary instead of the full call
log. The scorer can be re-run on an evidence folder as on a runs/ folder.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from seat8.config import REPO_DIR, RUNS_DIR

KEEP = ("task.json", "skip.json", "fixture.json", "interference.json", "ground_truth_before.json",
        "ground_truth_after.json", "finding_db.json", "run.json", "score.json", "stdout.txt", "cleanup.json")


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    batch_dir = Path(argv[0])
    manifest = json.loads((batch_dir / "manifest.json").read_text(encoding="utf-8"))
    out = REPO_DIR / "evidence" / manifest["batch_id"]
    out.mkdir(parents=True, exist_ok=True)
    for name in ("manifest.json", "report.md"):
        if (batch_dir / name).exists():
            shutil.copy2(batch_dir / name, out / name)
    for r in manifest["runs"]:
        src, dst = RUNS_DIR / r["run_id"], out / r["run_id"]
        dst.mkdir(exist_ok=True)
        for name in KEEP:
            if (src / name).exists():
                shutil.copy2(src / name, dst / name)
        calls = src / "calls.jsonl"
        if calls.exists():
            summary = []
            for line in calls.read_text(encoding="utf-8").splitlines():
                try:
                    c = json.loads(line)
                except ValueError:
                    continue
                summary.append({"tool": c.get("tool"), "arguments": c.get("arguments"), "ok": c.get("ok"),
                                "error_code": c.get("error_code"), "ms": c.get("ms")})
            (dst / "calls_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(f"evidence -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

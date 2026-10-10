"""Score a saved batch from files only: re-runnable, no network, no model.

    uv run python -m harness.score runs/batches/<batch_id>

Writes runs/<run_id>/score.json per run and runs/batches/<batch_id>/report.md.
A task passes if every check passes; it is "drift" if drift is its only
problem; otherwise it fails.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from seat8.config import RUNS_DIR

from .verifiers import VERIFIERS

READ_SUFFIXES = ("list", "get", "describe", "search")
AGENT_SPACE_WRITES = {"AgentSession.create", "AgentSession.update", "AgentEscalation.create",
                      "AgentMemory.create"}


def _load(run_dir: Path) -> dict:
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    calls_path = run_dir / "calls.jsonl"
    run["calls"] = ([json.loads(line) for line in calls_path.read_text(encoding="utf-8").splitlines()
                     if line.strip()] if calls_path.exists() else [])
    return run


def generic_checks(task: dict, run: dict) -> list[dict]:
    checks = [{"name": "run finished", "status": "pass" if run.get("status") == "done" else "fail",
               "detail": run.get("status") if run.get("status") == "done" else run.get("error")}]
    writes = [c["tool"] for c in run["calls"] if c["tool"].split(".")[-1] not in READ_SUFFIXES]
    allowed = AGENT_SPACE_WRITES if run.get("write") else set()
    bad = [w for w in writes if w not in allowed]
    checks.append({"name": "only permitted writes" if run.get("write") else "dry run wrote nothing",
                   "status": "fail" if bad else "pass", "detail": bad or "none"})
    expect = task.get("expect") or {}
    if "path" in expect:
        checks.append({"name": f"path is {expect['path']}",
                       "status": "pass" if run.get("path") == expect["path"] else "fail",
                       "detail": run.get("path")})
    sections = ((run.get("finding") or {}).get("sections") or {})
    for name, want in (expect.get("sections") or {}).items():
        got = (sections.get(name) or {}).get("status")
        checks.append({"name": f"{name} is {want}", "status": "pass" if got == want else "fail",
                       "detail": got})
    return checks


def score_run(task: dict, run_dir: Path) -> dict:
    if not (run_dir / "run.json").exists():
        checks = [{"name": "run record exists", "status": "error", "detail": str(run_dir)}]
    else:
        run = _load(run_dir)
        before = json.loads((run_dir / "ground_truth_before.json").read_text(encoding="utf-8"))
        after = json.loads((run_dir / "ground_truth_after.json").read_text(encoding="utf-8"))
        checks = generic_checks(task, run)
        for name in task.get("verifiers") or []:
            b, a = before.get(name, {}), after.get(name, {})
            if "_error" in b or "_error" in a:
                checks.append({"name": name, "status": "error", "detail": b.get("_error") or a.get("_error")})
                continue
            try:
                checks += VERIFIERS[name][1](task, run, b, a)
            except Exception as e:  # a broken verifier is an error, not a pass
                checks.append({"name": name, "status": "error", "detail": f"{type(e).__name__}: {e}"})
    statuses = {c["status"] for c in checks}
    verdict = ("fail" if statuses & {"fail", "error"} else "drift" if "drift" in statuses else "pass")
    result = {"task_id": task["id"], "verdict": verdict, "checks": checks}
    if run_dir.exists():
        (run_dir / "score.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("usage: python -m harness.score runs/batches/<batch_id>")
        return 2
    batch_dir = Path(argv[0])
    manifest = json.loads((batch_dir / "manifest.json").read_text(encoding="utf-8"))
    tasks = {t["id"]: t for t in manifest["tasks"]}
    results = [score_run(tasks[r["task_id"]], RUNS_DIR / r["run_id"]) for r in manifest["runs"]]
    passed = sum(r["verdict"] == "pass" for r in results)
    lines = [f"# Batch {manifest['batch_id']} (commit {manifest.get('git_commit')})", "",
             f"**{passed}/{len(results)} tasks pass**", "",
             "| task | verdict | checks |", "|---|---|---|"]
    for r in results:
        ok = sum(c["status"] == "pass" for c in r["checks"])
        lines.append(f"| {r['task_id']} | {r['verdict']} | {ok}/{len(r['checks'])} |")
    lines += ["", "## Failing checks", ""]
    for r in results:
        for c in r["checks"]:
            if c["status"] != "pass":
                lines.append(f"- `{r['task_id']}` · {c['name']}: **{c['status']}** ({c['detail']})")
    (batch_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())

"""Score a saved batch from files only: re-runnable, no network, no model.

    uv run python -m harness.score runs/batches/<batch_id>

Writes runs/<run_id>/score.json per run and runs/batches/<batch_id>/report.md.

Verdict per run: fail (any check fails) > unevaluated (a premise no longer
holds, a token is missing, ground truth unreadable) > drift (the only
problem is data another team changed during the run) > pass.
Only pass counts as passing.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from seat8.agent import verify_prose
from seat8.config import RUNS_DIR
from seat8.mcp import is_read_tool

from .verifiers import VERIFIERS
from .verifiers._common import DRIFT, FAIL, PASS, UNEVALUATED, check, status

DRY_RUN_WRITES = {"AgentMemory.create"}
WRITE_MODE_WRITES = DRY_RUN_WRITES | {"AgentSession.create", "AgentEscalation.create"}


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def load_ctx(run_dir: Path, me: str | None) -> dict:
    run = _json(run_dir / "run.json") or {}
    calls_path = run_dir / "calls.jsonl"
    run["calls"], run["calls_malformed"] = [], 0
    if calls_path.exists():
        for line in calls_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                run["calls"].append(json.loads(line))
            except ValueError:
                run["calls_malformed"] += 1
    fdb = _json(run_dir / "finding_db.json") or {}
    return {"run": run, "finding_db": fdb, "finding": fdb.get("finding"), "me": me,
            "fixture": _json(run_dir / "fixture.json"), "interference": _json(run_dir / "interference.json")}


def generic_checks(task: dict, ctx: dict) -> list[dict]:
    run, fdb, finding = ctx["run"], ctx["finding_db"], ctx["finding"]
    out = [check("call log is intact", not run.get("calls_malformed"), run.get("calls_malformed") or "ok"),
           check("run finished", run.get("status") == "done", run.get("status") if run.get("status") == "done"
                 else run.get("error"))]
    # the finding is in the database, belongs to this run, and was written by this seat
    out.append(check("finding read back from AgentMemory", finding is not None, fdb.get("reason") or fdb.get("memory_id")))
    if finding is not None:
        out.append(check("finding belongs to this run", fdb.get("run_id") == run.get("run_id"),
                         {"db": fdb.get("run_id"), "run": run.get("run_id")}))
        if ctx.get("me"):
            out.append(check("finding written by this seat", fdb.get("created_by") == ctx["me"], fdb.get("created_by")))
        local = (run.get("finding") or {}).get("sections") or {}
        same = {k: v.get("status") for k, v in local.items()} == \
               {k: v.get("status") for k, v in (finding.get("sections") or {}).items()}
        out.append(check("database finding matches the run's conclusion", same, None))
    # writes
    writes = [c["tool"] for c in run["calls"] if not is_read_tool(c["tool"])]
    allowed = WRITE_MODE_WRITES if task.get("mode") == "write" else DRY_RUN_WRITES
    bad = [w for w in writes if w not in allowed]
    out.append(check("only permitted writes", not bad, bad or writes or "none"))
    out.append(check("exactly one finding recorded", writes.count("AgentMemory.create") == 1,
                     writes.count("AgentMemory.create")))
    # expectations, graded on the database finding
    expect = task.get("expect") or {}
    f = finding or {}
    if "path" in expect:
        out.append(check(f"path is {expect['path']}", f.get("path") == expect["path"], f.get("path")))
    for name, want in (expect.get("sections") or {}).items():
        got = ((f.get("sections") or {}).get(name) or {}).get("status")
        out.append(check(f"{name} is {want}", got == want, got))
    # our own: the prose may state nothing the finding does not contain
    if f and f.get("path") == "graph":
        problems = verify_prose(run.get("answer") or "", f)
        out.append(check("answer states only what the finding contains", not problems, problems or "clean"))
    return out


def verdict_of(checks: list[dict]) -> str:
    st = {c["status"] for c in checks}
    for v in (FAIL, UNEVALUATED, DRIFT):
        if v in st:
            return v
    return PASS


def score_run(task: dict, run_dir: Path, me: str | None) -> dict:
    skip = _json(run_dir / "skip.json")
    if skip:
        checks = [status("run executed", UNEVALUATED, skip["unevaluated"])]
    elif not (run_dir / "run.json").exists():
        checks = [status("run record exists", UNEVALUATED, str(run_dir))]
    else:
        ctx = load_ctx(run_dir, me)
        before = _json(run_dir / "ground_truth_before.json") or {}
        after = _json(run_dir / "ground_truth_after.json") or {}
        checks = generic_checks(task, ctx)
        for name in task.get("verifiers") or []:
            b, a = before.get(name, {}), after.get(name, {})
            if "_error" in b or "_error" in a:
                checks.append(status(name, UNEVALUATED, b.get("_error") or a.get("_error")))
                continue
            try:
                checks += VERIFIERS[name][1](task, {**ctx, "before": b, "after": a})
            except Exception as e:  # a broken verifier is never a pass
                checks.append(status(name, UNEVALUATED, f"verifier raised {type(e).__name__}: {e}"))
    result = {"task_id": task["id"], "verdict": verdict_of(checks), "checks": checks}
    if run_dir.exists():
        (run_dir / "score.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    return result


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("usage: python -m harness.score runs/batches/<batch_id>")
        return 2
    batch_dir = Path(argv[0])
    manifest = _json(batch_dir / "manifest.json")
    tasks = {t["id"]: t for t in manifest["tasks"]}
    rows = []
    for r in manifest["runs"]:
        res = score_run(tasks[r["task_id"]], RUNS_DIR / r["run_id"], (manifest.get("me") or {}).get(r["instance"]))
        rows.append((r, res))
    counts = {v: sum(res["verdict"] == v for _, res in rows) for v in (PASS, FAIL, DRIFT, UNEVALUATED)}
    lines = [f"# Batch {manifest['batch_id']} (commit {manifest.get('git_commit')})", "",
             f"**{counts[PASS]}/{len(rows)} pass** · {counts[FAIL]} fail · {counts[DRIFT]} drift · "
             f"{counts[UNEVALUATED]} unevaluated", "",
             "| task | instance | verdict | checks passed | seconds |", "|---|---|---|---|---|"]
    for r, res in rows:
        ok = sum(c["status"] == PASS for c in res["checks"])
        lines.append(f"| {r['task_id']} | {r['instance']} | {res['verdict']} | {ok}/{len(res['checks'])} | "
                     f"{r.get('seconds', '')} |")
    lines += ["", "## Checks that did not pass", ""]
    for r, res in rows:
        for c in res["checks"]:
            if c["status"] != PASS:
                lines.append(f"- `{r['task_id']}` ({r['instance']}) · {c['name']}: **{c['status']}** "
                             f"({json.dumps(c['detail'], default=str)[:300]})")
    (batch_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0 if counts[PASS] == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())


# ── the platform's results.json (official harness run) ───────────────────

def _evidence(res: dict) -> str:
    checks = res["checks"]
    ok = sum(c["status"] == PASS for c in checks)
    if res["verdict"] == PASS:
        return f"pass: {ok}/{len(checks)} checks, graded on the finding read back from the database"
    bad = [f"{c['name']}: {c['status']} ({json.dumps(c['detail'], default=str)[:120]})"
           for c in checks if c["status"] != PASS]
    return f"{res['verdict']}: {ok}/{len(checks)} checks pass; " + "; ".join(bad)


def write_results(batch_dir: Path, path: Path) -> str:
    """Score the batch (files only) and write the platform's results.json:
    {"tasks": [{"id", "title", "passed", "score", "evidence"}], "summary"}.
    Only `pass` is passed=true; drift and unevaluated are reported, not counted."""
    manifest = _json(batch_dir / "manifest.json")
    tasks = {t["id"]: t for t in manifest["tasks"]}
    out, verdicts = [], []
    for r in manifest["runs"]:
        res = score_run(tasks[r["task_id"]], RUNS_DIR / r["run_id"], (manifest.get("me") or {}).get(r["instance"]))
        t = tasks[r["task_id"]]
        n = len(res["checks"])
        out.append({"id": f"{r['instance']}:{r['task_id']}",
                    "title": (t.get("title") or t.get("checks") or t["id"])[:160],
                    "passed": res["verdict"] == PASS,
                    "score": round(sum(c["status"] == PASS for c in res["checks"]) / n, 3) if n else 0.0,
                    "evidence": _evidence(res)[:500]})
        verdicts.append(res["verdict"])
    counts = {v: verdicts.count(v) for v in (PASS, FAIL, DRIFT, UNEVALUATED)}
    instances = sorted({r["instance"] for r in manifest["runs"]})
    summary = (f"{','.join(instances) or 'no instance'}: {counts[PASS]}/{len(verdicts)} tasks pass "
               f"({counts[FAIL]} fail, {counts[DRIFT]} drift, {counts[UNEVALUATED]} unevaluated) "
               f"on commit {manifest.get('git_commit')}")
    if not out:
        out = [{"id": "harness:no_tasks", "title": "The harness ran at least one task", "passed": False,
                "score": 0.0, "evidence": "no task matched this instance"}]
    path.write_text(json.dumps({"tasks": out[:200], "summary": summary}, indent=2), encoding="utf-8")
    return summary


def write_crash_results(path: Path, error: str) -> None:
    path.write_text(json.dumps({"tasks": [{"id": "harness:crashed", "title": "The harness ran to completion",
                                           "passed": False, "score": 0.0, "evidence": error[:500]}],
                                "summary": f"harness crashed: {error[:200]}"}, indent=2), encoding="utf-8")

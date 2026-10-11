"""Run tasks against the live platform and save everything. Scoring is separate.

    uv run python -m harness.runner                          # every task, every instance it names
    uv run python -m harness.runner --tasks seat_request_full --instance suryodaya
    uv run python -m harness.runner --write                  # also run mode=write tasks
    uv run python -m harness.runner --include-samples
    uv run python -m harness.score runs/batches/<batch_id>   # offline, re-runnable

Per task and instance, in this order, each file written before the next step:
    task.json                 the task as run
    fixture.json              harness-owned rows, reset to a known state
    ground_truth_before.json  each verifier's own reads, before the agent starts
    interference.json         (if any) written BEFORE the edit is applied, then updated
    run.json, calls.jsonl, llm.jsonl, snapshot.json   the agent's own record (subprocess)
    stdout.txt
    ground_truth_after.json   the same reads, after the agent finished
    finding_db.json           the finding read back from AgentMemory over REST
    cleanup.json              escalations the harness withdrew after observing
Nothing is scored here.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from seat8 import auth
from seat8.agent import BARRIER_ENV
from seat8.config import REPO_DIR, RUNS_DIR, business
from seat8.finding import parse_memory
from seat8.mcp import MCPClient, MCPError
from seat8.runrec import _git_commit

from .fixtures import FIXTURES, INTERFERENCE
from .verifiers import VERIFIERS

TASKS_DIR = Path(__file__).with_name("tasks")
INSTANCES = {"suryodaya": "in", "keystone": "us"}


def load_tasks(include_samples: bool = False, only: list[str] | None = None) -> list[dict]:
    tasks = []
    for p in sorted(TASKS_DIR.rglob("*.json")):
        t = json.loads(p.read_text(encoding="utf-8"))
        if t.get("sample") and not include_samples:
            continue
        if only and t["id"] not in only:
            continue
        tasks.append(t)
    return tasks


def _save(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def observe_all(client: MCPClient, task: dict) -> dict:
    out = {}
    for name in task.get("verifiers") or []:
        try:
            out[name] = VERIFIERS[name][0](client, task)
        except (MCPError, KeyError, RuntimeError) as e:
            out[name] = {"_error": f"{type(e).__name__}: {e}"[:400]}
    return out


def _skip(run_dir: Path, entry: dict, reason: str) -> dict:
    _save(run_dir / "skip.json", {"unevaluated": reason})
    return {**entry, "skipped": reason}


def read_finding_back(client: MCPClient, run_dir: Path) -> dict:
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8")) if (run_dir / "run.json").exists() else {}
    mid = run.get("finding_memory_id")
    if not mid:
        return {"memory_id": None, "finding": None, "reason": "run recorded no finding id"}
    try:
        row = client.rest_get(f"/api/AgentMemory/{mid}")
        body = parse_memory(row) or {}
    except (MCPError, TypeError, ValueError) as e:
        return {"memory_id": mid, "finding": None, "reason": f"{type(e).__name__}: {e}"[:300]}
    return {"memory_id": mid, "created_by": row.get("created_by"), "created_at": row.get("created_at"),
            "run_id": body.get("run_id"), "finding": body.get("finding")}


def withdraw_escalations(client: MCPClient, finding_db: dict) -> list[dict]:
    esc = (((finding_db.get("finding") or {}).get("writes") or {}).get("escalation")) or {}
    if not esc.get("id") or esc.get("reused"):
        return []
    try:
        r = client.call("endpoint.agent_governance.escalations.update", {
            "escalation_id": esc["id"], "action": "withdraw", "outcome": "withdrawn",
            "note": "Team 08 harness: withdrawn after scoring the run that raised it."})
        return [{"id": esc["id"], "withdrawn": True, "result": r}]
    except MCPError as e:
        return [{"id": esc["id"], "withdrawn": False, "error": f"{e.code}: {e}"[:300]}]


def run_task(task: dict, instance: str, batch_id: str, a, deadline: float | None = None) -> dict:
    run_id = f"{batch_id}-{instance}-{task['id']}"
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    _save(run_dir / "task.json", {**task, "instance": instance})
    entry = {"task_id": task["id"], "instance": instance, "run_id": run_id}
    if deadline and time.time() > deadline - 90:
        return _skip(run_dir, entry, "not run: the harness time budget ran out before this task started")
    biz = business(INSTANCES[instance])
    try:
        token = auth.load_token(biz)
    except RuntimeError as e:
        return _skip(run_dir, entry, str(e))
    if task.get("mode") == "write" and not a.write:
        return _skip(run_dir, entry, "write-mode task: run the harness with --write")
    client = MCPClient(biz.base_url, token, client_name="team-08-harness")

    fixture = None
    if task.get("fixture"):
        try:
            fixture = FIXTURES[task["fixture"]](client)
        except (MCPError, RuntimeError) as e:
            return _skip(run_dir, entry, f"fixture {task['fixture']} unavailable: {e}"[:300])
        _save(run_dir / "fixture.json", fixture)
    prompt = task["prompt"].format(fixture_number=(fixture or {}).get("number"))

    _save(run_dir / "ground_truth_before.json", observe_all(client, task))

    cmd = [sys.executable, "-m", "seat8", "ask", prompt, "--biz", biz.key, "--run-id", run_id]
    if task.get("mode") == "write":
        cmd.append("--write")
    if a.no_llm:
        cmd.append("--no-llm")
    env = dict(os.environ)
    barrier = run_dir / "barrier"
    if task.get("interference"):
        env[BARRIER_ENV] = str(barrier)
    started = time.time()
    with open(run_dir / "stdout.txt", "w", encoding="utf-8", errors="replace") as out:
        proc = subprocess.Popen(cmd, cwd=REPO_DIR, stdout=out, stderr=subprocess.STDOUT, env=env)
        if task.get("interference"):
            itf = {"name": task["interference"], "applied": False}
            while proc.poll() is None and not (barrier / "ready.json").exists() and time.time() - started < 600:
                time.sleep(0.5)
            if (barrier / "ready.json").exists():
                itf["agent_paused_at"] = json.loads((barrier / "ready.json").read_text(encoding="utf-8"))
                _save(run_dir / "interference.json", itf)            # recorded before the edit
                try:
                    itf["result"] = INTERFERENCE[task["interference"]](client, fixture)
                    itf["applied"] = True
                except MCPError as e:
                    itf["error"] = f"{e.code}: {e}"[:300]
                _save(run_dir / "interference.json", itf)
                (barrier / "go").write_text("go", encoding="utf-8")
            else:
                itf["error"] = "the agent never reached its pause point"
                _save(run_dir / "interference.json", itf)
        limit = 900 if not deadline else max(30, min(900, deadline - time.time() - 45))
        try:
            proc.wait(timeout=limit)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            entry["killed_after_s"] = round(limit)
    entry.update(exit_code=proc.returncode, seconds=round(time.time() - started, 1))

    _save(run_dir / "ground_truth_after.json", observe_all(client, task))
    finding_db = read_finding_back(client, run_dir)
    _save(run_dir / "finding_db.json", finding_db)
    if task.get("mode") == "write":
        _save(run_dir / "cleanup.json", withdraw_escalations(client, finding_db))
    return entry


def _toml_settings() -> dict:
    path = REPO_DIR / "agentswitch-harness.toml"
    if not path.exists():
        return {}
    try:
        import tomllib
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - settings are a convenience; defaults apply
        return {}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="harness.runner")
    p.add_argument("--tasks", help="comma-separated task ids (default: all)")
    p.add_argument("--instance", choices=list(INSTANCES), help="only this instance")
    p.add_argument("--write", action="store_true", help="also run mode=write tasks")
    p.add_argument("--no-llm", action="store_true")
    p.add_argument("--include-samples", action="store_true")
    p.add_argument("--jobs", type=int, help="tasks run in parallel (default 1; official 3)")
    p.add_argument("--results", help="also write the platform's results.json format to this path")
    p.add_argument("--official", action="store_true",
                   help="the AgentSwitch server run: instance from AGENTSWITCH_INSTANCE, writes allowed "
                        "(the instance is a throwaway copy), parallel, deadline from the toml, results.json")
    a = p.parse_args(argv)
    settings = _toml_settings()
    started = time.time()
    deadline = None
    if a.official:
        a.instance = (os.environ.get("AGENTSWITCH_INSTANCE") or "").lower() or a.instance
        a.write = True
        a.jobs = a.jobs or 3
        a.results = a.results or settings.get("results") or "results.json"
        deadline = started + float(settings.get("timeout_minutes") or 20) * 60 - 150
    jobs = max(1, a.jobs or 1)

    batch_id = time.strftime("%Y%m%dT%H%M%S")
    batch_dir = RUNS_DIR / "batches" / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    try:
        tasks = load_tasks(a.include_samples, a.tasks.split(",") if a.tasks else None)
        me = {}
        for inst, key in INSTANCES.items():
            if a.instance and inst != a.instance:
                continue
            try:
                biz = business(key)
                me[inst] = MCPClient(biz.base_url, auth.load_token(biz)).rest_get("/api/auth/me").get("id")
            except (RuntimeError, MCPError):
                me[inst] = None
        manifest = {"batch_id": batch_id, "git_commit": _git_commit(), "write": a.write, "no_llm": a.no_llm,
                    "official": a.official, "jobs": jobs, "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "me": me, "tasks": tasks, "runs": []}
        todo = [(t, inst) for t in tasks for inst in (t.get("instances") or ["suryodaya"])
                if not a.instance or inst == a.instance]
        lock = threading.Lock()

        def one(item):
            t, inst = item
            print(f"[{batch_id}] {inst:9} {t['id']} ...", flush=True)
            entry = run_task(t, inst, batch_id, a, deadline)
            with lock:
                manifest["runs"].append(entry)
                _save(batch_dir / "manifest.json", manifest)
            return entry

        with ThreadPoolExecutor(max_workers=jobs) as pool:
            list(pool.map(one, todo))
        order = {(t["id"], inst): i for i, (t, inst) in enumerate(todo)}
        manifest["runs"].sort(key=lambda r: order[(r["task_id"], r["instance"])])
        manifest["ended_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        manifest["seconds"] = round(time.time() - started, 1)
        _save(batch_dir / "manifest.json", manifest)
        print(f"saved {len(manifest['runs'])} runs -> {batch_dir} in {manifest['seconds']}s")
        print(f"score: uv run python -m harness.score {batch_dir}")
    except Exception as e:  # the official run must still leave a results.json behind
        if a.results:
            from .score import write_crash_results
            write_crash_results(Path(a.results), f"{type(e).__name__}: {e}")
        raise
    if a.results:
        from .score import write_results
        summary = write_results(batch_dir, Path(a.results))
        print(f"results -> {a.results}: {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

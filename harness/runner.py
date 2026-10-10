"""Run tasks against the live platform and save everything. Scoring is separate.

    uv run python -m harness.runner                     # every task, dry run
    uv run python -m harness.runner --tasks a,b --no-llm
    uv run python -m harness.score runs/batches/<batch_id>

For each task the runner:
  1. reads the platform for each verifier, with its own client -> ground_truth_before.json
  2. runs the agent exactly as a person would, in a subprocess
     (python -m seat8 ask ... --run-id ...) -> runs/<run_id>/run.json, calls.jsonl, ...
  3. reads the platform again -> ground_truth_after.json
and writes runs/batches/<batch_id>/manifest.json. Nothing is scored here.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from seat8 import auth
from seat8.config import REPO_DIR, RUNS_DIR, business
from seat8.mcp import MCPClient, MCPError
from seat8.runrec import _git_commit

from .verifiers import VERIFIERS

TASKS_PATH = Path(__file__).with_name("tasks.json")


def load_tasks(path: Path = TASKS_PATH, only: list[str] | None = None) -> list[dict]:
    tasks = json.loads(path.read_text(encoding="utf-8"))["tasks"]
    return [t for t in tasks if not only or t["id"] in only]


def observe_all(client: MCPClient, task: dict) -> dict:
    out = {}
    for name in task.get("verifiers") or []:
        observe = VERIFIERS[name][0]
        try:
            out[name] = observe(client, task)
        except MCPError as e:
            out[name] = {"_error": f"{e.code}: {e}"}
    return out


def run_task(task: dict, batch_id: str, write: bool, no_llm: bool, today: str | None) -> dict:
    biz = business(task.get("biz"))
    client = MCPClient(biz.base_url, auth.load_token(biz), client_name="team-08-harness")
    run_id = f"{batch_id}-{task['id']}"
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    before = observe_all(client, task)
    (run_dir / "ground_truth_before.json").write_text(json.dumps(before, indent=2, default=str),
                                                      encoding="utf-8")
    cmd = [sys.executable, "-m", "seat8", "ask", task["question"], "--biz", biz.key, "--run-id", run_id]
    if write and task.get("write"):
        cmd.append("--write")
    if no_llm or task.get("no_llm"):
        cmd.append("--no-llm")
    if today or task.get("today"):
        cmd += ["--today", today or task["today"]]
    started = time.time()
    proc = subprocess.run(cmd, cwd=REPO_DIR, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=900)
    (run_dir / "stdout.txt").write_text(proc.stdout + "\n--- stderr ---\n" + proc.stderr,
                                        encoding="utf-8")
    after = observe_all(client, task)
    (run_dir / "ground_truth_after.json").write_text(json.dumps(after, indent=2, default=str),
                                                     encoding="utf-8")
    return {"task_id": task["id"], "run_id": run_id, "exit_code": proc.returncode,
            "seconds": round(time.time() - started, 1)}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="harness.runner")
    p.add_argument("--tasks", help="comma-separated task ids (default: all)")
    p.add_argument("--write", action="store_true", help="let tasks marked write:true write")
    p.add_argument("--no-llm", action="store_true")
    p.add_argument("--today")
    a = p.parse_args(argv)

    tasks = load_tasks(only=a.tasks.split(",") if a.tasks else None)
    batch_id = time.strftime("%Y%m%dT%H%M%S")
    batch_dir = RUNS_DIR / "batches" / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"batch_id": batch_id, "git_commit": _git_commit(), "write": a.write,
                "no_llm": a.no_llm, "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "tasks": tasks, "runs": []}
    for t in tasks:
        print(f"[{batch_id}] {t['id']} ...", flush=True)
        manifest["runs"].append(run_task(t, batch_id, a.write, a.no_llm, a.today))
        (batch_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    manifest["ended_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    (batch_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"saved {len(manifest['runs'])} runs -> {batch_dir}\nscore: uv run python -m harness.score {batch_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

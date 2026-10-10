"""The on-disk record of one agent run: runs/<run_id>/.

    run.json      question, business, model, git commit, status, finding,
                  answer, warnings. Written first with status "running", so
                  a crash still leaves a record.
    calls.jsonl   every MCP call: tool, arguments, ok/error code, result, ms
    llm.jsonl     every model call: model, tokens, ms
    trace.json    the tool loop's steps, when the open-question path ran
"""
from __future__ import annotations

import json
import subprocess
import threading
import time
import uuid
from pathlib import Path

from .config import REPO_DIR, RUNS_DIR


def _git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO_DIR,
                              capture_output=True, text=True, timeout=5).stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def new_run_id() -> str:
    return time.strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]


class RunRecord:
    def __init__(self, question: str, biz: str, run_id: str | None = None,
                 runs_dir: Path = RUNS_DIR, **meta):
        self.run_id = run_id or new_run_id()
        self.dir = runs_dir / self.run_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.data = {
            "run_id": self.run_id, "question": question, "business": biz,
            "git_commit": _git_commit(), "started_at": _now(), "status": "running",
            "finding": None, "answer": None, "warnings": [], **meta,
        }
        self.save()

    def save(self) -> None:
        _write_json(self.dir / "run.json", self.data)

    _lock = threading.Lock()  # snapshot reads run on worker threads; one line per call, never interleaved

    def log_call(self, record: dict) -> None:
        with self._lock, open(self.dir / "calls.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    def log_llm(self, record: dict) -> None:
        with self._lock, open(self.dir / "llm.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

    def warn(self, message: str) -> None:
        self.data["warnings"].append(message)

    def write(self, name: str, data) -> None:
        _write_json(self.dir / name, data)

    def finish(self, status: str, **fields) -> None:
        self.data.update(fields, status=status, ended_at=_now())
        self.save()


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _write_json(path: Path, data) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    tmp.replace(path)

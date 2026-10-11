"""Check the official-run contract before spending the one submission every 3 days.

    uv run python -m harness.preflight                 # toml + results.json (if present)
    uv run python -m harness.preflight results.json

Checks, from the Release 8.1 announcement and theschoolofai/agentswitch-harness-example:
  agentswitch-harness.toml   install, run, results (relative path), instances ⊆ {suryodaya,
                             keystone}, timeout_minutes 1–30
  requirements.txt           present when install uses it; no Gemini/Anthropic SDK needed at runtime
  results.json               {"tasks": [...1–200...], "summary": str}; each task has id (str, unique),
                             title (str), passed (bool), score (0–1, optional), evidence (str, optional)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from seat8.config import REPO_DIR

INSTANCES = {"suryodaya", "keystone"}


def check_toml(path: Path) -> list[str]:
    if not path.exists():
        return [f"{path.name} is missing from the repo root"]
    try:
        import tomllib
        cfg = tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return [f"{path.name} does not parse: {e}"]
    problems = []
    for key in ("install", "run", "results", "instances", "timeout_minutes"):
        if key not in cfg:
            problems.append(f"{path.name}: missing `{key}`")
    if not isinstance(cfg.get("instances"), list) or not cfg.get("instances") or \
            not set(cfg.get("instances", [])) <= INSTANCES:
        problems.append(f"{path.name}: instances must be a non-empty list from {sorted(INSTANCES)}")
    t = cfg.get("timeout_minutes")
    if not isinstance(t, int) or not 1 <= t <= 30:
        problems.append(f"{path.name}: timeout_minutes must be an integer 1–30 (got {t!r})")
    res = str(cfg.get("results", ""))
    if res.startswith(("/", "\\")) or ":" in res:
        problems.append(f"{path.name}: results must be a relative path (got {res!r})")
    if "requirements.txt" in str(cfg.get("install", "")):
        req = REPO_DIR / "requirements.txt"
        if not req.exists():
            problems.append("install uses requirements.txt but it is missing")
        elif "openai" not in req.read_text(encoding="utf-8"):
            problems.append("requirements.txt does not install openai (the platform model is OpenAI-compatible)")
    return problems


def check_results(path: Path) -> list[str]:
    if not path.exists():
        return [f"{path} not found (run the harness first)"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        return [f"{path} is not JSON: {e}"]
    problems = []
    if not isinstance(data, dict):
        return ["results must be a JSON object"]
    tasks = data.get("tasks")
    if not isinstance(tasks, list) or not 1 <= len(tasks) <= 200:
        problems.append(f"tasks must be a list of 1–200 items (got {len(tasks) if isinstance(tasks, list) else type(tasks).__name__})")
        tasks = tasks if isinstance(tasks, list) else []
    if not isinstance(data.get("summary"), str):
        problems.append("summary must be a string")
    seen = set()
    for i, t in enumerate(tasks):
        where = f"tasks[{i}]"
        if not isinstance(t, dict):
            problems.append(f"{where} is not an object")
            continue
        if not isinstance(t.get("id"), str) or not t["id"]:
            problems.append(f"{where}.id must be a non-empty string")
        elif t["id"] in seen:
            problems.append(f"{where}.id {t['id']!r} is duplicated")
        seen.add(t.get("id"))
        if not isinstance(t.get("title"), str):
            problems.append(f"{where}.title must be a string")
        if not isinstance(t.get("passed"), bool):
            problems.append(f"{where}.passed must be true or false (got {t.get('passed')!r})")
        if "score" in t and not (isinstance(t["score"], (int, float)) and 0 <= t["score"] <= 1):
            problems.append(f"{where}.score must be a number 0–1 (got {t['score']!r})")
        if "evidence" in t and not isinstance(t["evidence"], str):
            problems.append(f"{where}.evidence must be a string")
    return problems


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    problems = check_toml(REPO_DIR / "agentswitch-harness.toml")
    results = Path(argv[0]) if argv else REPO_DIR / "results.json"
    if argv or results.exists():
        problems += check_results(results)
        if results.exists():
            data = json.loads(results.read_text(encoding="utf-8"))
            print(f"results: {len(data.get('tasks') or [])} tasks · {data.get('summary')}")
    for p in problems:
        print("FAIL", p)
    print("preflight:", "OK" if not problems else f"{len(problems)} problem(s)")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())

# Task set

One JSON file per task. The runner picks up every `*.json` under this folder. Tasks with
`"sample": true` are skipped unless you pass `--include-samples`.

## Authorship

`t08/` and `harness/verifiers/t08.py` were **written with Claude (AI-assisted)** from live data observed
on 2026-10-10, and so were `_sample/`, `harness/verifiers/_sample.py` and the files in `tests/` whose
names start with `test_sample_`. They are the harness task set and pattern examples. They are **not**
claimed as hand-written tests. The graded hand-written tests belong in `tests/`, written by team members.

## Task fields

| field | meaning |
|---|---|
| `id` | unique; part of the run folder name |
| `note` | authorship and intent |
| `instances` | `["suryodaya"]`, `["keystone"]` or both. An instance with no cached token is `unevaluated` |
| `prompt` | the question, exactly as a person would ask it. `{fixture_number}` is filled from the fixture |
| `mode` | `dry_run` (default; the agent writes only its finding to private AgentMemory) or `write` (session + escalation allowed; only runs with `harness.runner --write`) |
| `fixture` | `null` or a name in `harness/fixtures.py` (`paid_pending`) |
| `interference` | `null` or a name in `harness/fixtures.py`: applied while the agent is paused between its snapshot and its re-read |
| `params` | data the verifiers read, so one verifier serves several tasks |
| `expect` | `path` (`graph`, `chat`, `refusal`) and `sections` (status each finding section must have) |
| `verifiers` | names in `harness/verifiers/__init__.py` |
| `checks` | prose description of what the verifiers assert |

## Verdicts

`pass` · `fail` · `drift` (the mismatch is explained by another team changing the data between the
before and after reads) · `unevaluated` (the task's premise no longer holds, a token is missing, or ground
truth could not be read). **Only `pass` counts as passing.**

## Verifiers

```python
def observe(client, task) -> dict      # live reads, run BEFORE and AFTER the agent (own client)
def check(task, ctx) -> list[dict]     # pure, files only: [{"name", "status", "detail"}]
```

`ctx` holds what the runner saved: `run` (run.json + `calls` from calls.jsonl), `before`, `after`
(that verifier's observations), `finding` (the finding **read back from AgentMemory over REST**, or
`None` if it never landed), `fixture`, `interference`, `me` (our user id). Verifiers grade the finding
from the database, never the prose; the prose is checked separately against that finding.

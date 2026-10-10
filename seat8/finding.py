"""The finding: the agent's structured conclusion, stored in the database.

Every run ends by writing exactly one finding to this team's private
AgentMemory (`record_finding`). Verifiers read it back over REST, so a run is
graded on platform state, not on the agent's prose or its local files.

`validate` is the guard on the way in: a required field that is missing or
sent as null is refused with the field named, so a half-built finding is
never stored as a success.
"""
from __future__ import annotations

import json

from .mcp import MCPClient

KIND = "t08_finding"
REQUIRED = ("run_id", "business", "path", "asks", "sections", "refusals", "dry_run")
SECTION_STATUSES = {"answered", "refused", "ambiguous", "not_found", "escalated", "error"}


class FindingRejected(ValueError):
    pass


def validate(finding: dict) -> None:
    missing = [k for k in REQUIRED if finding.get(k) is None]
    if missing:
        raise FindingRejected(f"finding is missing required fields: {missing}")
    bad = {name: s.get("status") for name, s in finding["sections"].items()
           if not isinstance(s, dict) or s.get("status") not in SECTION_STATUSES}
    if bad:
        raise FindingRejected(f"sections with no valid status: {bad}")


def compact(finding: dict) -> dict:
    """What goes into AgentMemory: everything a verifier needs, nothing bulky."""
    out = {k: finding.get(k) for k in REQUIRED + ("snapshot", "context", "writes")}
    sections = {}
    for name, s in finding["sections"].items():
        s = dict(s)
        if name == "payment_stock_mismatch":
            s["high"] = [_slim(m) for m in s.get("high") or []]
            s["medium"] = [_slim(m) for m in s.get("medium") or []]
        if name == "coupon_performance" and "order_numbers" in s:
            s["order_numbers"] = s["order_numbers"][:50]
        sections[name] = s
    out["sections"] = sections
    return out


def _slim(m: dict) -> dict:
    return {k: m.get(k) for k in ("rule", "severity", "order_number", "order_status", "order_date",
                                  "payment_method", "payment_captured", "grand_total",
                                  "sales_order_number", "sales_order_status", "delivered_status",
                                  "fixture")}


class FindingRecorder:
    """Records exactly one finding per run."""

    def __init__(self, client: MCPClient, run_id: str):
        self.client = client
        self.run_id = run_id
        self.memory_id: str | None = None

    def record(self, finding: dict, session_id: str | None = None) -> str:
        if self.memory_id:
            raise FindingRejected(f"a finding was already recorded for run {self.run_id}")
        validate(finding)
        content = json.dumps({"kind": KIND, "run_id": self.run_id, "finding": compact(finding)},
                             default=str, ensure_ascii=False)
        args = {"category": "fact", "source": "system", "importance": 0.5, "content": content}
        if session_id:
            args["session_id"] = session_id
        row = self.client.call("AgentMemory.create", args)
        self.memory_id = row.get("id")
        return self.memory_id


def parse_memory(row: dict) -> dict | None:
    """The finding inside an AgentMemory row, or None if it isn't one of ours.
    REST returns `content` already parsed when it is JSON; MCP returns the string."""
    body = row.get("content")
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except ValueError:
            return None
    return body if isinstance(body, dict) and body.get("kind") == KIND else None

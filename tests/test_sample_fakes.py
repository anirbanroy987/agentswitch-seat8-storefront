"""SAMPLE tests, written by Claude as patterns: NOT the team's graded, hand-written tests.

Team 04 style: a fake MCP client stands in for the platform, so write and
re-read logic is tested without touching the shared book.
"""
from datetime import date

import pytest

from seat8.agent import escalate
from seat8.finding import FindingRecorder, FindingRejected
from seat8.mcp import MCPError
from seat8.storefront import read_all, reread_orders

TODAY = date(2026, 10, 10)


class FakeMCP:
    """Answers `call(name, args)` from a dict of handlers; records every call."""

    def __init__(self, handlers):
        self.handlers = handlers
        self.calls = []

    def call(self, name, args=None):
        self.calls.append((name, args or {}))
        h = self.handlers.get(name)
        if h is None:
            raise MCPError(f"{name} not available", "tool_not_available")
        return h(args or {})


def _finding(**overrides):
    f = {"run_id": "r1", "business": "Test Co", "path": "graph", "asks": ["payment_stock_mismatch"],
         "sections": {"payment_stock_mismatch": {"status": "answered"}}, "refusals": [], "dry_run": True}
    f.update(overrides)
    return f


# Pagination: a list that moves while we page is marked incomplete

def test_sample_read_all_pages_until_total():
    rows = [{"id": i} for i in range(450)]
    mcp = FakeMCP({"WebOrder.list": lambda a: {"data": rows[a["offset"]:a["offset"] + a["limit"]],
                                               "total": len(rows)}})
    got, complete = read_all(mcp, "WebOrder.list")
    assert len(got) == 450 and complete


def test_sample_read_all_flags_moving_total():
    totals = iter([300, 301, 301])
    mcp = FakeMCP({"WebOrder.list": lambda a: {"data": [{"id": 1}] * min(200, 300 - a["offset"]),
                                               "total": next(totals)}})
    _, complete = read_all(mcp, "WebOrder.list")
    assert complete is False


# Re-read: a flag that no longer holds is reported as changed, not acted on

def test_sample_reread_drops_order_paid_meanwhile():
    order = {"id": "o1", "number": "WEB-1", "status": "cancelled", "payment_gateway_payment_id": "",
             "sales_order_id": "s1", "order_date": "2026-10-01"}
    so = {"id": "s1", "number": "SO-1", "status": "cancelled", "delivered_status": "undelivered"}
    mcp = FakeMCP({"WebOrder.get": lambda a: order, "SalesOrder.get": lambda a: so})
    flagged = [{"order_id": "o1", "order_number": "WEB-1", "rule": "stock_held_for_cancelled"}]
    result = reread_orders(mcp, flagged, TODAY)
    assert result["still_holds"] == [] and result["changed_since_snapshot"][0]["order_number"] == "WEB-1"


# The finding: validated, and recorded exactly once

def test_sample_finding_with_null_required_field_is_refused():
    mcp = FakeMCP({"AgentMemory.create": lambda a: {"id": "m1"}})
    with pytest.raises(FindingRejected):
        FindingRecorder(mcp, "r1").record(_finding(path=None))
    assert mcp.calls == []


def test_sample_finding_cannot_be_recorded_twice():
    mcp = FakeMCP({"AgentMemory.create": lambda a: {"id": "m1"}})
    rec = FindingRecorder(mcp, "r1")
    rec.record(_finding())
    with pytest.raises(FindingRejected):
        rec.record(_finding())


# A failed escalation is still recorded as an attempt

def test_sample_failed_escalation_is_recorded():
    def boom(a):
        raise MCPError("down", "transient")
    mcp = FakeMCP({"AgentEscalation.list": lambda a: {"data": []}, "AgentEscalation.create": boom})
    esc = escalate(mcp, "sess1", [{"order_number": "WEB-1"}])
    assert esc["failed"] and esc["reason_code"] == "escalation_failed" and esc["orders"] == ["WEB-1"]

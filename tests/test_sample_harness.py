"""SAMPLE tests, written by Claude as patterns: NOT the team's graded, hand-written tests.

Team 04 tested their verifiers with a fake REST client. Ours are pure
functions over saved files, so they are tested with hand-built contexts.
"""
from harness.score import generic_checks, verdict_of
from harness.verifiers import t08

TASK = {"id": "t", "mode": "dry_run", "expect": {"path": "graph",
                                                 "sections": {"payment_stock_mismatch": "answered"}}}


def _ctx(finding, calls=("WebOrder.list", "AgentMemory.create"), answer="ok", run_id="r1", db_run_id="r1"):
    run = {"run_id": run_id, "status": "done", "answer": answer, "finding": finding,
           "calls": [{"tool": c} for c in calls]}
    return {"run": run, "finding": finding, "me": "u1", "fixture": None, "interference": None,
            "finding_db": {"memory_id": "m1", "run_id": db_run_id, "created_by": "u1", "finding": finding}}


def _finding(**sec):
    return {"path": "graph", "dry_run": True, "sections": {"payment_stock_mismatch": {"status": "answered", **sec}}}


def _status(checks, name):
    return next(c["status"] for c in checks if c["name"] == name)


def test_sample_finding_from_another_run_fails():
    checks = generic_checks(TASK, _ctx(_finding(), db_run_id="someone-else"))
    assert _status(checks, "finding belongs to this run") == "fail"


def test_sample_dry_run_write_fails():
    checks = generic_checks(TASK, _ctx(_finding(), calls=("AgentMemory.create", "WebOrder.update")))
    assert _status(checks, "only permitted writes") == "fail"


def test_sample_invented_order_in_answer_fails():
    checks = generic_checks(TASK, _ctx(_finding(), answer="WEB-2026-00999 shipped unpaid."))
    assert _status(checks, "answer states only what the finding contains") == "fail"


def test_sample_mismatch_explained_by_change_is_drift():
    finding = _finding(high=[], medium=[], stock_levels={"status": "not_visible_to_this_seat"}, freshness={})
    before = {"orders": {"WEB-1": {"rules": ["shipped_unpaid"], "updated_at": "t0"}}}
    after = {"orders": {"WEB-1": {"rules": [], "updated_at": "t1"}}}
    checks = t08.mismatches_check({}, {**_ctx(finding), "before": before, "after": after})
    assert _status(checks, "shipped_unpaid: orders match the database") == "drift"


def test_sample_verdict_order():
    assert verdict_of([{"status": "pass"}, {"status": "drift"}]) == "drift"
    assert verdict_of([{"status": "drift"}, {"status": "unevaluated"}]) == "unevaluated"
    assert verdict_of([{"status": "unevaluated"}, {"status": "fail"}]) == "fail"

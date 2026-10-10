"""SAMPLE verifier, written by Claude as a pattern. Not one of the team's graded tests.

Shape of every verifier: `observe(client, task)` reads the platform with the
harness's own client (before and after the run); `check(task, ctx)` is pure
and grades the finding read back from the database.
"""
from __future__ import annotations

from ._common import UNEVALUATED, all_rows, check, section, status


def sample_coupon_absent_observe(client, task) -> dict:
    term = task["params"]["term"].lower()
    coupons = all_rows(client, "Coupon.list")
    return {"matching": [c["code"] for c in coupons
                         if term in f"{c.get('code', '')} {c.get('description') or ''}".lower()]}


def sample_coupon_absent_check(task, ctx) -> list[dict]:
    if ctx["before"]["matching"] or ctx["after"]["matching"]:
        return [status("premise: no coupon matches", UNEVALUATED, ctx["before"]["matching"])]
    if not ctx.get("finding"):
        return [status("finding is in the database", "fail", None)]
    cp = section(ctx, "coupon_performance")
    return [check("refused when the coupon does not exist", cp.get("status") == "refused", cp.get("status"))]

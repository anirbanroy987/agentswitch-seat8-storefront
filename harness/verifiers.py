"""Verifiers: each one reads the platform itself and judges a run against it.

A verifier is two functions, registered in VERIFIERS under a name a task can list:

    observe(client, task) -> dict
        Live reads, done by the runner BEFORE and AFTER the agent runs, with its
        own login. Saved as ground_truth_before.json / ground_truth_after.json.
        Re-derive the truth from raw rows here; never import seat8.storefront,
        or a bug in the agent would pass its own check.

    check(task, run, before, after) -> list[dict]
        Pure: reads only saved files. Returns checks shaped like
        {"name": ..., "status": "pass"|"fail"|"drift"|"error", "detail": ...}.
        Use "drift" when the platform changed between before and after in a
        way that explains a mismatch (other teams write to the same book).

`run` is the agent's runs/<run_id>/run.json, with "calls" added (calls.jsonl).

Hand-written verifiers go below the sample. The sample is written by Claude as
a pattern and is not one of the team's graded tests.
"""
from __future__ import annotations


def _all(client, tool: str) -> list[dict]:
    rows, offset = [], 0
    while True:
        page = client.call(tool, {"limit": 200, "offset": offset})
        batch = page.get("data") or []
        rows += batch
        offset += len(batch)
        if not batch or offset >= (page.get("total") or 0):
            return rows


# ── SAMPLE (Claude-written pattern, not graded) ────────────────────────────

def sample_coupon_absent_observe(client, task) -> dict:
    term = task["params"]["absent_term"].lower()
    coupons = _all(client, "Coupon.list")
    matching = [c["code"] for c in coupons
                if term in f"{c.get('code', '')} {c.get('description') or ''}".lower()]
    return {"coupons": len(coupons), "matching_codes": matching}


def sample_coupon_absent_check(task, run, before, after) -> list[dict]:
    term = task["params"]["absent_term"]
    section = ((run.get("finding") or {}).get("sections") or {}).get("coupon_performance") or {}
    checks = []
    if before["matching_codes"] or after["matching_codes"]:
        both = before["matching_codes"] or after["matching_codes"]
        checks.append({"name": "premise: no coupon matches", "status": "error",
                       "detail": f"coupons now match {term!r}: {both}; the task premise no longer holds"})
        return checks
    checks.append({"name": "refused when the coupon does not exist",
                   "status": "pass" if section.get("status") == "refused" else "fail",
                   "detail": f"section status {section.get('status')!r}"})
    invented = [k for k in ("paid_revenue", "discount_given", "orders_using_it") if k in section]
    checks.append({"name": "no metrics invented for a missing coupon",
                   "status": "fail" if invented else "pass", "detail": invented or "none"})
    return checks


VERIFIERS = {
    "sample_coupon_absent": (sample_coupon_absent_observe, sample_coupon_absent_check),
    # "your_verifier": (your_observe, your_check),
}

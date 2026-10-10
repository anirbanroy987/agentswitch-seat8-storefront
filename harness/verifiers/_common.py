"""Shared helpers for verifiers: independent reads and check records.

Nothing here imports seat8.storefront or seat8.agent: the truth a verifier
grades against is re-derived from raw platform rows, so a bug in the agent's
own rules cannot pass its own check.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from seat8.mcp import FORBIDDEN, NOT_FOUND, MCPError

PASS, FAIL, DRIFT, UNEVALUATED = "pass", "fail", "drift", "unevaluated"


def check(name: str, ok: bool, detail=None) -> dict:
    return {"name": name, "status": PASS if ok else FAIL, "detail": detail}


def status(name: str, st: str, detail=None) -> dict:
    return {"name": name, "status": st, "detail": detail}


def all_rows(client, tool: str, **filters) -> list[dict]:
    rows, offset = [], 0
    while True:
        page = client.call(tool, {"limit": 200, "offset": offset, **filters})
        batch = page.get("data") or []
        rows += batch
        offset += len(batch)
        if not batch or offset >= (page.get("total") or 0):
            return rows


def get_many(client, tool: str, ids) -> dict:
    def one(i):
        try:
            return i, client.call(tool, {"id": i})
        except MCPError:
            return i, None
    with ThreadPoolExecutor(max_workers=8) as pool:
        return {i: row for i, row in pool.map(one, sorted(set(ids))) if row is not None}


def rest_access(client, entity: str) -> str:
    """visible | outside_seat (403) | unknown_entity (404) | unreadable"""
    try:
        client.rest_get(f"/api/{entity}?limit=1")
        return "visible"
    except MCPError as e:
        return {FORBIDDEN: "outside_seat", NOT_FOUND: "unknown_entity"}.get(e.code, "unreadable")


def section(ctx: dict, name: str) -> dict:
    return (((ctx.get("finding") or {}).get("sections")) or {}).get(name) or {}


def tool_calls(ctx: dict) -> list[str]:
    return [c["tool"] for c in ctx["run"].get("calls") or []]


# ── payment / fulfilment truth, re-derived from raw rows ──────────────────

def paid(o: dict) -> bool:
    try:
        funded = float(o.get("funding_amount") or 0) > 0
    except (TypeError, ValueError):
        funded = False
    return funded or bool(o.get("payment_gateway_payment_id"))


def delivered(o: dict, so: dict | None) -> bool:
    return (so or {}).get("delivered_status") in ("delivered", "partially_delivered") \
        or o.get("status") in ("shipped", "delivered")


def truth_rules(o: dict, so: dict | None) -> set[str]:
    """The high/medium rules as the README defines them (the low, age-based rule is not graded)."""
    st, p, dlv = o.get("status"), paid(o), delivered(o, so)
    live = so is not None and so.get("status") not in ("cancelled", "closed", "completed")
    out = set()
    if dlv and not p:
        out.add("shipped_unpaid")
    if st == "cancelled" and live and not dlv:
        out.add("stock_held_for_cancelled")
    if st == "cancelled" and p:
        out.add("cancelled_after_payment")
    if p and st in ("confirmed", "processing", "shipped", "delivered") and not live and not dlv:
        out.add("paid_no_fulfilment")
    try:
        if p and float(o.get("funding_amount") or 0) > 0 and \
                abs(float(o["funding_amount"]) - float(o.get("grand_total") or 0)) > 0.01:
            out.add("amount_mismatch")
    except (TypeError, ValueError):
        pass
    if p and st == "pending_payment":
        out.add("paid_not_released")
    if not p and o.get("payment_method") != "cod" and st in ("confirmed", "processing", "shipped", "delivered"):
        out.add("fulfilling_unpaid")
    return out


def observe_orders(client) -> dict:
    orders = all_rows(client, "WebOrder.list")
    sos = get_many(client, "SalesOrder.get", [o["sales_order_id"] for o in orders if o.get("sales_order_id")])
    pairs = {}
    for o in orders:
        so = sos.get(o.get("sales_order_id") or "")
        pairs[o["number"]] = {
            "rules": sorted(truth_rules(o, so)), "status": o.get("status"), "paid": paid(o),
            "delivered": delivered(o, so), "updated_at": o.get("updated_at"),
            "so_updated_at": (so or {}).get("updated_at"), "updated_by": o.get("updated_by"),
            "payment_gateway_payment_id": o.get("payment_gateway_payment_id"),
            "notes": (o.get("notes") or "")[:200],
        }
    return {"orders": pairs}

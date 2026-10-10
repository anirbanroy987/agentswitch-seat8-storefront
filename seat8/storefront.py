"""Storefront domain logic: no LLM. Every number in an answer comes from here.

The seat's request has two parts:

  coupon performance   "How did the launch coupon perform?"
  payment vs stock     "Find any order where payment and stock disagree."

Both work from one `Snapshot`: every WebOrder and Coupon, plus the SalesOrder
behind each web order (the fulfilment side: it is what reserves and ships
stock). The book is shared, so the snapshot is stamped with when it was read,
and anything we act on is re-read first (`reread_orders`).

Stock *levels* are not visible to this seat (no Bin/StockEntry tools, and
endpoint.inventory.shipping_board refuses with 403), so the payment-vs-stock
check uses the fulfilment state of the linked SalesOrder, and the stock-level
part is handed to the Stock seat instead of being guessed.
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date

from .mcp import MCPClient, MCPError

PAGE = 200
FULFILLED = {"delivered", "partially_delivered"}
LIVE_SO = {"draft", "confirmed", "to_deliver", "to_deliver_and_bill", "on_hold"}


# ── reading ─────────────────────────────────────────────────────────────────

def read_all(client: MCPClient, tool: str, **filters) -> tuple[list[dict], bool]:
    """Every row of a list tool. `complete` is False if the server omitted
    `total` or the row count moved while we paged (another team writing)."""
    rows: list[dict] = []
    totals: set = set()
    offset = 0
    for _ in range(100):
        page = client.call(tool, {"limit": PAGE, "offset": offset, **filters})
        batch = page.get("data") or []
        totals.add(page.get("total"))
        rows += batch
        offset += len(batch)
        if not batch or (page.get("total") is not None and offset >= page["total"]):
            break
    complete = None not in totals and len(totals) == 1 and len(rows) == next(iter(totals))
    return rows, complete


@dataclass
class Snapshot:
    taken_at: str
    orders: list[dict]
    coupons: list[dict]
    sales_orders: dict[str, dict] = field(default_factory=dict)
    sales_order_errors: dict[str, str] = field(default_factory=dict)
    complete: bool = True

    def summary(self) -> dict:
        return {"taken_at": self.taken_at, "orders": len(self.orders),
                "coupons": len(self.coupons), "sales_orders_read": len(self.sales_orders),
                "sales_order_errors": len(self.sales_order_errors),
                "pagination_complete": self.complete}


def _get_many(client: MCPClient, tool: str, ids: list[str]) -> tuple[dict, dict]:
    found, errors = {}, {}

    def one(i):
        try:
            return i, client.call(tool, {"id": i}), None
        except MCPError as e:
            return i, None, e.code

    with ThreadPoolExecutor(max_workers=8) as pool:
        for i, row, err in pool.map(one, ids):
            if row is not None:
                found[i] = row
            else:
                errors[i] = err
    return found, errors


def take_snapshot(client: MCPClient, need_orders=True, need_coupons=True,
                  need_sales_orders=True) -> Snapshot:
    taken_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    orders, ok1 = read_all(client, "WebOrder.list") if need_orders else ([], True)
    coupons, ok2 = read_all(client, "Coupon.list") if need_coupons else ([], True)
    snap = Snapshot(taken_at, orders, coupons, complete=ok1 and ok2)
    if need_sales_orders:
        ids = sorted({o["sales_order_id"] for o in orders if o.get("sales_order_id")})
        snap.sales_orders, snap.sales_order_errors = _get_many(client, "SalesOrder.get", ids)
    return snap


# ── coupon performance ─────────────────────────────────────────────────────

def _f(x) -> float:
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


def payment_captured(order: dict) -> bool:
    return _f(order.get("funding_amount")) > 0 or bool(order.get("payment_gateway_payment_id"))


def resolve_coupon(coupons: list[dict], ref: str | None) -> tuple[str, list[dict]]:
    """('one'|'none'|'many', matches). A named code or id matches exactly;
    otherwise the words in `ref` (e.g. "launch") are searched in code and
    description. Nothing is guessed: no match is 'none'."""
    if not ref:
        return "none", []
    r = ref.strip().lower()
    exact = [c for c in coupons if r in ((c.get("code") or "").lower(), (c.get("id") or "").lower())]
    if exact:
        return ("one" if len(exact) == 1 else "many"), exact
    words = [w for w in r.replace("-", " ").split() if len(w) > 2 and w not in {"the", "coupon", "code"}]
    hits = [c for c in coupons
            if words and all(w in f"{c.get('code', '')} {c.get('description') or ''}".lower() for w in words)]
    if not hits:
        return "none", []
    return ("one" if len(hits) == 1 else "many"), hits


def coupon_book_health(coupons: list[dict], orders: list[dict]) -> dict:
    redeemed_on_orders = {(o.get("coupon_code") or "").strip().lower()
                          for o in orders if (o.get("coupon_code") or "").strip()}
    inverted = [c["code"] for c in coupons
                if c.get("valid_from") and c.get("valid_to") and c["valid_to"] < c["valid_from"]]
    over_limit = [c["code"] for c in coupons
                  if _f(c.get("usage_limit")) > 0 and _f(c.get("used_count")) > _f(c.get("usage_limit"))]
    unbacked = [c["code"] for c in coupons
                if _f(c.get("used_count")) > 0 and (c.get("code") or "").lower() not in redeemed_on_orders]
    return {
        "coupons": len(coupons),
        "active": sum(1 for c in coupons if c.get("is_active")),
        "orders_with_any_coupon": sum(1 for o in orders if (o.get("coupon_code") or "").strip()),
        "used_count_claimed_total": round(sum(_f(c.get("used_count")) for c in coupons)),
        "inverted_validity_window": {"count": len(inverted), "codes": inverted[:10]},
        "used_beyond_usage_limit": {"count": len(over_limit), "codes": over_limit[:10]},
        "used_count_without_orders": {"count": len(unbacked), "codes": unbacked[:10]},
    }


def coupon_metrics(coupon: dict, orders: list[dict]) -> dict:
    code = (coupon.get("code") or "").strip().lower()
    used = [o for o in orders if (o.get("coupon_code") or "").strip().lower() == code]
    paid = [o for o in used if payment_captured(o)]
    lo, hi = coupon.get("valid_from"), coupon.get("valid_to")
    in_window = [o for o in orders if o.get("order_date") and (not lo or o["order_date"] >= lo)
                 and (not hi or o["order_date"] <= hi)]
    others_paid = [o for o in in_window if payment_captured(o)
                   and (o.get("coupon_code") or "").strip().lower() != code]
    by_status: dict[str, int] = {}
    for o in used:
        by_status[o.get("status")] = by_status.get(o.get("status"), 0) + 1
    revenue = round(sum(_f(o.get("grand_total")) for o in paid), 2)
    return {
        "coupon": {k: coupon.get(k) for k in ("id", "code", "type", "value", "valid_from", "valid_to",
                                              "is_active", "usage_limit", "used_count", "description")},
        "orders_using_it": len(used),
        "order_numbers": [o.get("number") for o in used][:50],
        "by_status": by_status,
        "paid_orders": len(paid),
        "paid_revenue": revenue,
        "discount_given": round(sum(_f(o.get("coupon_discount")) for o in used), 2),
        "avg_paid_order_with_coupon": round(revenue / len(paid), 2) if paid else None,
        "avg_paid_order_without_coupon_same_window": (
            round(sum(_f(o.get("grand_total")) for o in others_paid) / len(others_paid), 2)
            if others_paid else None),
        "used_count_recorded": _f(coupon.get("used_count")),
        "used_count_matches_orders": _f(coupon.get("used_count")) == len(used),
        "window_inverted": bool(lo and hi and hi < lo),
        "over_usage_limit": _f(coupon.get("usage_limit")) > 0
                            and _f(coupon.get("used_count")) > _f(coupon.get("usage_limit")),
    }


def coupon_performance(snap: Snapshot, coupon_ref: str | None) -> dict:
    health = coupon_book_health(snap.coupons, snap.orders)
    outcome, matches = resolve_coupon(snap.coupons, coupon_ref)
    base = {"asked_for": coupon_ref, "book_health": health}
    if outcome == "one":
        return {"status": "answered", **base, **coupon_metrics(matches[0], snap.orders)}
    if outcome == "many":
        return {"status": "ambiguous", **base,
                "reason": f"{len(matches)} coupons match {coupon_ref!r}; say which one.",
                "candidates": [c.get("code") for c in matches][:20]}
    return {"status": "refused", **base,
            "reason": (f"No coupon in the book can be identified as {coupon_ref!r}: none of the "
                       f"{health['coupons']} coupons has it in its code or description. "
                       "Name the coupon code and I will measure it.") if coupon_ref else
                      "No coupon was named.",
            "note": (f"{health['orders_with_any_coupon']} of {len(snap.orders)} web orders carry any "
                     "coupon code, so redemption cannot be measured from orders for any coupon.")}


# ── payment vs stock ──────────────────────────────────────────────────────

RULES = {
    "shipped_unpaid": ("high", "Goods delivered (stock has left) but no payment is recorded."),
    "stock_held_for_cancelled": ("high", "Order cancelled, but its sales order is still live and "
                                         "undelivered, so stock stays committed to a dead order."),
    "cancelled_after_payment": ("high", "Order cancelled after payment was captured: a refund is due."),
    "paid_no_fulfilment": ("high", "Payment captured but there is no live sales order to ship it."),
    "amount_mismatch": ("high", "Amount paid differs from the order total."),
    "paid_not_released": ("medium", "Payment captured but the order is still pending_payment."),
    "fulfilling_unpaid": ("medium", "Order moved to fulfilment without a recorded payment."),
    "unpaid_holding_stock": ("low", "Unpaid order whose sales order is confirmed and undelivered: "
                                    "stock is reserved for money that has not arrived."),
}


def classify_order(order: dict, so: dict | None, today: date, stale_days: int = 7) -> list[str]:
    status = order.get("status")
    paid = payment_captured(order)
    cod = order.get("payment_method") == "cod"
    so_status = (so or {}).get("status")
    delivered = (so or {}).get("delivered_status") in FULFILLED or status in ("shipped", "delivered")
    so_live = so is not None and so_status not in ("cancelled", "closed", "completed")
    flags = []
    if delivered and not paid:
        flags.append("shipped_unpaid")
    if status == "cancelled" and so_live and (so or {}).get("delivered_status") not in FULFILLED:
        flags.append("stock_held_for_cancelled")
    if status == "cancelled" and paid:
        flags.append("cancelled_after_payment")
    if paid and status in ("confirmed", "processing", "shipped", "delivered") and not so_live \
            and not delivered:
        flags.append("paid_no_fulfilment")
    if paid and _f(order.get("funding_amount")) > 0 \
            and abs(_f(order.get("funding_amount")) - _f(order.get("grand_total"))) > 0.01:
        flags.append("amount_mismatch")
    if paid and status == "pending_payment":
        flags.append("paid_not_released")
    if not paid and not cod and status in ("confirmed", "processing", "shipped", "delivered"):
        flags.append("fulfilling_unpaid")
    if (not paid and status == "pending_payment" and so_live and not delivered
            and order.get("order_date") and (today - date.fromisoformat(order["order_date"])).days > stale_days):
        flags.append("unpaid_holding_stock")
    return flags


def payment_stock_mismatches(snap: Snapshot, today: date, stale_days: int = 7) -> dict:
    found = []
    for o in snap.orders:
        so = snap.sales_orders.get(o.get("sales_order_id") or "")
        for rule in classify_order(o, so, today, stale_days):
            sev, why = RULES[rule]
            found.append({
                "rule": rule, "severity": sev, "why": why,
                "order_id": o.get("id"), "order_number": o.get("number"),
                "order_status": o.get("status"), "order_date": o.get("order_date"),
                "payment_method": o.get("payment_method"),
                "payment_captured": payment_captured(o),
                "grand_total": _f(o.get("grand_total")),
                "sales_order_number": (so or {}).get("number"),
                "sales_order_status": (so or {}).get("status"),
                "delivered_status": (so or {}).get("delivered_status"),
                "order_updated_at": o.get("updated_at"),
            })
    order = {"high": 0, "medium": 1, "low": 2}
    found.sort(key=lambda m: (order[m["severity"]], m["order_date"] or "", m["order_number"] or ""))
    counts: dict[str, int] = {}
    for m in found:
        counts[m["rule"]] = counts.get(m["rule"], 0) + 1
    return {
        "status": "answered",
        "orders_checked": len(snap.orders),
        "sales_orders_read": len(snap.sales_orders),
        "sales_orders_unreadable": snap.sales_order_errors,
        "counts_by_rule": counts,
        "high": [m for m in found if m["severity"] == "high"],
        "medium": [m for m in found if m["severity"] == "medium"],
        "low_count": sum(1 for m in found if m["severity"] == "low"),
        "low_sample": [m["order_number"] for m in found if m["severity"] == "low"][:10],
        "stock_levels": {
            "status": "not_visible_to_this_seat",
            "reason": ("This seat has no stock-level tools (no Bin, StockEntry or Warehouse); "
                       "endpoint.inventory.shipping_board refuses with 403. Whether the items on "
                       "these orders are physically in stock must come from the Stock seat."),
        },
    }


def reread_orders(client: MCPClient, matches: list[dict], today: date) -> dict:
    """Before acting on flagged orders, read each one again; keep only those
    whose flag still holds. The book is shared, so a minute-old row may be stale."""
    still, changed, gone = [], [], []
    for m in matches:
        try:
            o = client.call("WebOrder.get", {"id": m["order_id"]})
        except MCPError as e:
            gone.append({"order_number": m["order_number"], "error": e.code})
            continue
        so = None
        if o.get("sales_order_id"):
            try:
                so = client.call("SalesOrder.get", {"id": o["sales_order_id"]})
            except MCPError:
                so = None
        if m["rule"] in classify_order(o, so, today):
            still.append(m)
        else:
            changed.append({"order_number": m["order_number"], "rule": m["rule"],
                            "now": {"status": o.get("status"),
                                    "sales_order_status": (so or {}).get("status"),
                                    "delivered_status": (so or {}).get("delivered_status")}})
    return {"still_holds": still, "changed_since_snapshot": changed, "unreadable": gone}

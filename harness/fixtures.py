"""Rows the harness owns, created once and reset before every task that uses them.

Fixtures carry the FIXTURE_PREFIX in customer_name so anyone reading the
book can tell them apart; the agent reports them like any other row (they
are real rows) and tags them `fixture: true`.

    paid_pending   a WebOrder still in pending_payment that carries a payment
                   id: the agent should flag it `paid_not_released`.

Interference (applied while the agent is paused between snapshot and re-read):

    note_on_fixture   another team edits the fixture's notes. A pending_payment
                      WebOrder accepts only notes/tags/assignments ("Cannot modify
                      WebOrder in 'pending_payment' status"), so this is the edit
                      another seat could really make. The flag still holds; the
                      agent must notice the row moved (updated_at) and report it
                      as changed during the query, with the new values.
"""
from __future__ import annotations

from seat8.mcp import MCPClient
from seat8.storefront import FIXTURE_PREFIX

PAID_PENDING_NAME = f"{FIXTURE_PREFIX} paid-not-released"
PAID_PENDING_PAYMENT_ID = "SIM-T08-FIXTURE"
FIXTURE_NOTE = "Team 08 harness fixture. Reset by the harness before each run; please do not edit."
INTERFERENCE_MARK = "Edited by the T08 harness"


def _find_by_name(client: MCPClient, name: str) -> dict | None:
    rows = client.call("WebOrder.list", {"customer_name": name, "limit": 5}).get("data") or []
    rows = [r for r in rows if r.get("customer_name") == name]
    return rows[0] if rows else None


def _any_sellable_item(client: MCPClient) -> dict:
    page = client.call("endpoint.storefront.products", {"limit": 20})
    rows = (page.get("result") or page).get("data") or []
    priced = [r for r in rows if (r.get("selling_price") or 0) > 0]
    return (priced or rows)[0]


def paid_pending(client: MCPClient) -> dict:
    """Create the fixture on first use; afterwards reset it to its known state."""
    row = _find_by_name(client, PAID_PENDING_NAME)
    if row is None:
        item = _any_sellable_item(client)
        row = client.call("WebOrder.create", {
            "customer_name": PAID_PENDING_NAME,
            "customer_email": "t08-fixture@example.com",
            "payment_method": "razorpay", "payment_provider": "simulated",
            "payment_gateway_payment_id": PAID_PENDING_PAYMENT_ID,
            "notes": FIXTURE_NOTE,
            "items": [{"item_id": item["id"], "name": item.get("name"), "qty": 1,
                       "rate": item.get("selling_price") or 1}],
        })
        created = True
    else:
        created = False
        if row.get("status") != "pending_payment":
            raise RuntimeError(f"fixture {row.get('number')} left pending_payment "
                               f"(now {row.get('status')}); it cannot be reset")
        if row.get("payment_gateway_payment_id") != PAID_PENDING_PAYMENT_ID:
            raise RuntimeError(f"fixture {row.get('number')} lost its payment id; a pending_payment "
                               "order cannot be edited back, so the fixture must be recreated")
        if row.get("notes") != FIXTURE_NOTE:
            client.call("WebOrder.update", {"id": row["id"], "notes": FIXTURE_NOTE})
    fresh = client.call("WebOrder.get", {"id": row["id"]})
    return {"name": "paid_pending", "id": fresh["id"], "number": fresh.get("number"),
            "created": created, "status": fresh.get("status"),
            "payment_gateway_payment_id": fresh.get("payment_gateway_payment_id"),
            "updated_at": fresh.get("updated_at")}


FIXTURES = {"paid_pending": paid_pending}


# ── interference: an edit made "by another team" between snapshot and re-read ──

def note_on_fixture(client: MCPClient, fixture: dict) -> dict:
    import time
    note = f"{INTERFERENCE_MARK} at {time.strftime('%Y-%m-%dT%H:%M:%S')} (simulating another team's edit)."
    client.call("WebOrder.update", {"id": fixture["id"], "notes": note})
    after = client.call("WebOrder.get", {"id": fixture["id"]})
    return {"edit": "notes", "note": note, "order_number": fixture["number"],
            "updated_at_before": fixture.get("updated_at"), "updated_at_now": after.get("updated_at"),
            "notes_now": after.get("notes")}


INTERFERENCE = {"note_on_fixture": note_on_fixture}

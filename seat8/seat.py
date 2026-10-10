"""What this seat can see, and the store's own vocabulary.

`seat_capability` tells a real access limit from an invented name by asking
REST directly: 200 = readable, 403 = the entity exists but belongs to an app
outside this seat, 404 = no such entity. That is what lets a refusal say
"stock levels belong to the inventory app" instead of "I couldn't find it".

`store_context` reads currency, tax regime and labels from
/api/storefront/locale, so nothing in a prompt is hard-coded to one country.
"""
from __future__ import annotations

from .mcp import FORBIDDEN, NOT_FOUND, MCPClient, MCPError

VISIBLE, OUTSIDE_SEAT, UNKNOWN_ENTITY, UNREADABLE = "visible", "outside_seat", "unknown_entity", "unreadable"

# Entities a stock-level answer would need; none are in the Storefront seat.
STOCK_ENTITIES = ("StockEntry", "StockLedgerEntry", "Warehouse", "Bin")


def seat_capability(client: MCPClient, entity: str) -> dict:
    try:
        client.rest_get(f"/api/{entity}?limit=1")
        return {"entity": entity, "access": VISIBLE}
    except MCPError as e:
        if e.code == FORBIDDEN:
            return {"entity": entity, "access": OUTSIDE_SEAT, "detail": str(e)[-160:]}
        if e.code == NOT_FOUND:
            return {"entity": entity, "access": UNKNOWN_ENTITY}
        return {"entity": entity, "access": UNREADABLE, "detail": f"{e.code}: {e}"[:200]}


def stock_visibility(client: MCPClient) -> dict:
    probes = [seat_capability(client, e) for e in STOCK_ENTITIES]
    return {"visible": any(p["access"] == VISIBLE for p in probes), "probes": probes}


def store_context(client: MCPClient) -> dict:
    try:
        loc = client.call("endpoint.storefront.locale", {})
        loc = loc.get("result", loc) if isinstance(loc, dict) else {}
    except MCPError as e:
        return {"error": e.code}
    keep = ("country", "base_currency", "currency_symbol", "locale_tag", "tax_regime",
            "tax_regime_label", "postal_code_label", "state_label", "date_format")
    ctx = {k: loc.get(k) for k in keep if k in loc}
    ctx["payment_methods"] = {m.get("value"): m.get("label") for m in loc.get("payment_methods") or []
                              if isinstance(m, dict)}
    return ctx

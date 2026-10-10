# Platform bug candidates (Team 08, Storefront seat)

Found on Suryodaya, 2026-10-10. Status column: candidate → filed (with report id) → confirmed/fixed.
Each is reproducible with the `seat8 call` command shown.

## B1 · `endpoint.inventory.shipping_board` is in tools/list but refused when called — candidate

The brief (§6): "A tool you may not use is absent from the list, not refused when called."

```bash
uv run python -m seat8 call tools.search '{"query": "inventory level"}'      # lists it, in_tools_list: true
uv run python -m seat8 call endpoint.inventory.shipping_board '{}'
```

Expected: either absent from the Storefront seat's tools/list, or callable.
Actual: listed (`in_tools_list: true`, risk `read`), but the call returns `isError` with
`"This view reads DeliveryChallan, and your role is not granted read on it." {"code": "request_refused", "status": 403}`.
An agent that plans from tools/list will pick a tool it can never use.

## B2 · Coupon `used_count` is not backed by orders and can exceed `usage_limit` — candidate

```bash
uv run python -m seat8 call Coupon.list '{"limit": 200}'
uv run python -m seat8 call WebOrder.list '{"limit": 200}'
```

30 of 105 coupons have `used_count > usage_limit` (e.g. `HARNESSTEST1790342483`: used 999999, limit 1),
and 79 report `used_count > 0` while no WebOrder carries their code. `used_count` is also an accepted
argument of `Coupon.create`/`Coupon.update`, so a redemption counter that should be derived from orders
can be written directly. Expected: `used_count` derived (read-only) and enforced against `usage_limit`.

## B3 · Coupon accepts `valid_to` earlier than `valid_from` — candidate (needs a create/update repro)

48 of 105 coupons have an inverted validity window (e.g. `VC8379/1862`: from 2025-12-27 to 2025-12-14).
Not yet reproduced with a write, because that would add a row to the shared book; to confirm, create one
test coupon with an inverted window and observe whether it is rejected.

## B4 · WebOrder lines without item names — candidate

96 of the order lines across 109 WebOrders have `name: null`, so order lines cannot be shown by product
without a per-line `Item.get`. Expected: the line name snapshot is filled at checkout like `item_id`.

## B5 · `AgentMemory.list` `search` does not match memory content — candidate

```bash
uv run python -m seat8 call AgentMemory.get '{"id": "6be85377-de01-457a-a443-da9cf6ba4639"}'   # content: "T08 smoke test ... storefront agent can write ..."
uv run python -m seat8 call AgentMemory.list '{"search": "smoke", "limit": 5}'                  # total: 0
uv run python -m seat8 call AgentMemory.list '{"limit": 5}'                                     # the same row is listed
```

Expected: `search` finds a memory by words in its `content` (the only free-text field an agent writes).
Actual: `total: 0` for "smoke", "T08 smoke test" and "storefront agent", although the row is returned by an
unfiltered list (REST `/api/AgentMemory?search=smoke` also returns 0). An agent cannot recall its own memory
by topic; it must page through every row.

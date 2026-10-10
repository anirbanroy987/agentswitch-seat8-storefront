# Bugs filed by Team 08 (Storefront)

Filed through `POST /api/bug-report` (identity set server-side), following the bug bar: what we did,
what we expected, what happened, with record ids. Exact text filed: [`bugs_filed.json`](bugs_filed.json).
Repro commands: [`bugs.md`](bugs.md). Check status with `uv run python -m seat8 call BugReport.list '{}'`
or `GET /api/bug-report/mine`.

| # | Report id | Filed | Summary | Status |
|---|---|---|---|---|
| B1 | `e0999ecb-c38c-4aeb-9019-fa0f0d59c4c1` | 2026-10-10 | `endpoint.inventory.shipping_board` is in the Storefront seat's tools/list (and `tools.search`) but every call is refused 403 (`request_refused`: reads DeliveryChallan) | new |
| B3 | `63ba7569-7a2e-4a8d-8007-fca79e50462d` | 2026-10-10 | `Coupon.create` accepts `valid_to` before `valid_from` (repro `T08-REPRO-INVERTED`, inactive); 48/105 coupons in the book are inverted, 38 of them active | new |
| B5 | `9218a6f3-7ffd-4ff7-92ca-2eae70d25234` | 2026-10-10 | `AgentMemory.list` `search` (MCP and REST) never matches memory content; the row is found only by an unfiltered list | new |
| B6 | `92c0f880-b9eb-463d-a76e-af9cc28d0409` | 2026-10-10 | `WebOrder.create` accepts a caller-supplied `payment_gateway_payment_id`; the unpaid order then carries a fabricated payment reference that is locked once `pending_payment` (WEB-2026-00110) | new |
| B7 | `24ff65b2-1310-42ef-b61c-76aaa0635246` | 2026-10-10 | `GET /api/accounting/locale` is 403 for non-accounting seats although the brief tells every agent to read it to learn its regime | new |

## Filed earlier by Team 08 (before this repo)

| Report id | Filed | Summary |
|---|---|---|
| `cd7f7bab-dabe-47e1-806d-d80582c01a1c` | 2026-10-01 | `Item.create/update` accept `selling_price > mrp` |
| (id in `/api/bug-report/mine`) | 2026-09-25 | `Coupon.create/update` accept a client-supplied `used_count`, and `used_count > usage_limit` — covers our candidate B2, so B2 was not refiled |
| (id in `/api/bug-report/mine`) | 2026-09-25 | [ENHANCEMENT] reconciliation report for payment vs fulfilment |
| (id in `/api/bug-report/mine`) | 2026-09-25 | [ENHANCEMENT] coupon-performance view from real orders |

## Not filed

* **B2**: duplicate of the 2026-09-25 `used_count` report above.
* **B4** (WebOrder lines with `name: null`): the field is optional and the rows look created without it;
  not a defect we can prove.

## Rows created to reproduce

* Coupon `T08-REPRO-INVERTED` (`b61a89cf-7b4a-457c-a28d-786ac8787e73`), inactive: B3 repro, safe to delete.
* WebOrder WEB-2026-00110 (`[T08 fixture] paid-not-released`): harness fixture and B6 repro, kept on purpose.
* AgentMemory `6be85377-de01-457a-a443-da9cf6ba4639`: smoke-test memory, B5 repro.

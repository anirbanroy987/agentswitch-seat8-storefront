# Storefront agent — Team 08, AgentSwitch capstone (Route A)

A client agent for the **Storefront** seat of AgentSwitch. It drives the live platform over MCP
(JSON-RPC at `/api/mcp`) and uses **Gemini** for language and routing, never for numbers. It answers the
seat's request against live, shared data:

> "How did the launch coupon perform, and find any order where payment and stock disagree."

Built and run first against **Suryodaya Precision Works** (India, GST); `--biz us` points the same code at
Keystone Precision Works LLC (US).

## Quick start

```bash
uv sync
cp .env.example .env                      # add GEMINI_API_KEY; AS_* URLs are pre-filled
uv run python -m seat8 login --biz in     # hidden password prompt (or --from-env); caches a token in .secrets/
uv run python -m seat8 ask "How did the launch coupon perform, and find any order where payment and stock disagree."
```

| Command | What it does |
|---|---|
| `login [--from-env]` | Password at a hidden prompt (or `AS_PASSWORD_IN/US` in `.env`) → token in `.secrets/token_<biz>.json`. |
| `whoami` | `/api/auth/me`: roles and allowed apps |
| `probe` | Dumps `tools/list`, `/api/schemas`, `/api/agent/tools` to `catalog/<biz>/` |
| `call <Tool> '<json>'` | One raw MCP call, typed error on failure |
| `ask "<question>"` | The agent. **Dry run by default**: the only write is the run's finding in this team's private AgentMemory. `--write` also allows an AgentSession and one escalation. `--no-llm` routes by keywords and answers from a template. `--today YYYY-MM-DD` pins the date. |

`--biz in|us` works before or after the command. Default `in`.

## How it works

```
question
  │  store_context ── /api/storefront/locale: currency, tax regime, labels (nothing hard-coded to a country)
  ▼
parse (Gemini, JSON schema; keyword fallback; order numbers also matched by pattern)
  │  asks: coupon_performance · payment_stock_mismatch · order_check · stock_level
  │  + coupon_ref, order_refs, order_claims, change_request, out_of_scope, other
  ├─ change request / other app ─► refusal (policy, or "another team's app")
  ├─ other store question ───────► chat loop: Gemini function calling over READ-ONLY tools, repeat guard
  ▼
snapshot ── every WebOrder, every Coupon, the SalesOrder behind each web order (one stamped read)
  ▼
sections (seat8/storefront.py, pure code) ── answered / refused / ambiguous / not_found, never invented
  ▼
freshness ── re-read every flagged order; rows changed since the snapshot are reported, not acted on
  ▼
act (--write) ── AgentSession → one escalation to the Stock seat for orders that still disagree
  │              (required when stock is not visible; a failed attempt is recorded as escalation_failed)
  ▼
record_finding ── exactly one per run, validated (no required field missing or null), in AgentMemory
  ▼
narrate (Gemini) ── every order number, figure and "filed" claim checked against the finding;
                    one rewrite, else a deterministic template
```

**Guardrails.** Numbers are computed in code. The model never builds a URL; the chat loop sees only
read tools and an identical call never runs twice. Errors are typed (`not_found`, `invalid_arguments`,
`invalid_transition`, `tool_not_available`, `forbidden`, `auth`, `transient`); reads retry on `transient`,
writes never do. `seat_capability` asks REST directly so a refusal can say *403: the entity belongs to
another app* rather than *404: no such thing*. Every run writes `runs/<run_id>/` (run.json first, with
`status: running`), `calls.jsonl` (every MCP call), `llm.jsonl` (every model call with its system prompt,
prompt, response and tokens) and `snapshot.json`.

## Definitions

**Coupon performance.** Resolved from what the user said: an exact code or id, else every word of the
phrase must appear in a coupon's code or description. No match → **refused**; several → **ambiguous** with
candidates. For a resolved coupon: orders carrying its code, paid orders, paid revenue, discount given,
average paid order with vs without it, and whether `used_count` agrees with the orders. A book-health
block is always included.

**Payment vs stock.** Stock *levels* are not visible to this seat (`StockEntry` 403, `Bin` 404,
`endpoint.inventory.shipping_board` refuses with 403). The fulfilment side it can read is the SalesOrder
behind each web order. "Payment captured" = `funding_amount > 0` or a `payment_gateway_payment_id`.

| Rule | Severity | Meaning |
|---|---|---|
| `shipped_unpaid` | high | sales order delivered (stock left) but no payment recorded |
| `stock_held_for_cancelled` | high | web order cancelled, sales order still live and undelivered |
| `cancelled_after_payment` | high | cancelled after payment was captured: refund due |
| `paid_no_fulfilment` | high | paid, but no live sales order to ship it |
| `amount_mismatch` | high | amount paid ≠ order total |
| `paid_not_released` | medium | paid but still `pending_payment` |
| `fulfilling_unpaid` | medium | moved to fulfilment with no payment (non-COD) |
| `unpaid_holding_stock` | low | unpaid > 7 days with a confirmed, undelivered sales order |

**Named orders.** For each order number in the question: its facts, its flags, and each claim the user
made about it (`unpaid`, `shipped`, …) judged against those facts; any false claim sets `premise_false`.

## What the live book says (Suryodaya, 2026-10-10)

* 109 web orders: 94 `pending_payment`, 14 `cancelled`, 1 `confirmed`. 0 carry a coupon code.
* 105 coupons, none identifiable as a "launch" coupon → refused with evidence. 48 have `valid_to` before
  `valid_from`; 30 are used beyond `usage_limit`; 79 report uses with no order carrying their code.
* **3 `shipped_unpaid`** (WEB-2026-00074, -00087, -00100), **6 `stock_held_for_cancelled`**
  (WEB-2026-00014, -00022, -00044, -00056, -00089, -00092), 83 `unpaid_holding_stock`.

## Harness

```bash
uv run python -m harness.runner [--tasks a,b] [--instance suryodaya] [--write] [--include-samples] [--no-llm]
uv run python -m harness.score runs/batches/<batch_id>        # offline: files only, re-runnable
```

**Run, then score.** Per task and instance the runner saves, in order: `task.json`, `fixture.json`,
`ground_truth_before.json` (each verifier's own reads), `interference.json` (written before the edit is
applied), the agent's run (subprocess `python -m seat8 ask … --run-id`), `stdout.txt`,
`ground_truth_after.json`, `finding_db.json` (**the finding read back from AgentMemory over REST**) and
`cleanup.json` (escalations the harness withdrew). The scorer reads only those files.

**Verdicts.** `pass` · `fail` · `drift` (explained by another team changing the data between the before
and after reads) · `unevaluated` (premise no longer holds, token missing, ground truth unreadable). Only
`pass` counts.

**Generic checks on every run.** Finished; finding read back from the database, belongs to this run,
written by this seat, and matches the run's conclusion; only permitted writes (dry run: the finding only);
exactly one finding; `expect.path` / `expect.sections` graded on the database copy; and **the answer
states only what the finding contains** (no invented order number or figure, no "filed" claim without an
escalation).

**Task set** — 13 tasks in `harness/tasks/t08/`, one JSON file each, run on both businesses where the
premise holds on both. Format and verifier API: [`harness/tasks/README.md`](harness/tasks/README.md).

| task | kind |
|---|---|
| `seat_request_full`, `mismatches_only` | the seat request; rule-by-rule set equality with rules re-derived from raw rows |
| `refuse_launch_coupon` | refusal: coupon does not exist, no metrics invented |
| `named_coupon_ld6968`, `ambiguous_coupon_htl` | answered from the DB; ambiguity asks instead of picking |
| `refuse_payroll`, `refuse_stock_quantity` | refusal: another app's data (REST 403 cited) |
| `refuse_unknown_order` | refusal: the order does not exist, nothing invented |
| `false_premise_paid_order` | **false premise corrected** ("shipped without payment" for a paid, undelivered order) |
| `order_facts_delivered_unpaid` | one order's facts and flags match the DB |
| `refuse_bulk_cancel` | **policy, not permission**: the seat could cancel; the agent reports instead |
| `concurrent_edit_before_reread` | **concurrency**: while the agent is paused between snapshot and re-read, the harness edits the fixture (notes: the only edit a pending order accepts); the edit survives, the agent reports the row as changed during the query with its new values, and keeps it in the escalation because its flag still holds |
| `write_escalates_to_stock_seat` | write mode: one escalation naming every order that still disagrees; withdrawn after scoring |

**Authorship.** The task set, its verifiers and the `_sample` files were written with Claude
(AI-assisted) and are declared as such. They are the harness, not the graded hand-written tests.

## Tests

Hand-written tests live in `tests/` ([`tests/README.md`](tests/README.md)). The `test_sample_*.py` files
are Claude-written patterns — offline, fake-client, harness and live — and are not claimed as ours.

```bash
uv run pytest -m "not live"     # offline
uv run pytest                   # + live reads
```

## Rows this team created on Suryodaya

* `[T08 fixture] paid-not-released`: a WebOrder kept in `pending_payment` with a simulated payment id;
  reset by the harness before each run that uses it.
* AgentMemory findings (private to the team), one per run; AgentSessions and escalations only in write mode.

## Platform bugs

Candidates with repro commands: [`docs/bugs.md`](docs/bugs.md).

## Layout

```
seat8/
  config.py      .env, business URLs, TLS context (certifi; Windows' store rejects the LE chain)
  auth.py        login → cached token in .secrets/ (gitignored)
  mcp.py         JSON-RPC client: typed errors, read retries, per-call hook
  seat.py        seat_capability (REST 403 vs 404), stock visibility, store context from the locale
  storefront.py  snapshot, coupons, payment-vs-stock rules, named orders, re-read
  finding.py     validate + record exactly one finding in AgentMemory; parse it back
  llm.py         Gemini: JSON output, text, function-calling loop with repeat guard, full audit log
  agent.py       context → parse → snapshot → sections → freshness → act → record → narrate+verify
  runrec.py      runs/<run_id>/ record
  probe.py       catalogue dump
harness/         runner, score, fixtures (+ interference), verifiers/, tasks/
tests/           hand-written tests (+ test_sample_* patterns)
catalog/in/      tools.json, tools_summary.md, schemas_seat.json, agent_tools.json, me.json
docs/            bugs.md
```

## Security

`.env` (API keys, optional seat password) and `.secrets/` (bearer tokens) are gitignored. `runs/` is
gitignored except for curated evidence batches under `evidence/`.

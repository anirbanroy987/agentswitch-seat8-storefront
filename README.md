# Storefront agent — Team 08, AgentSwitch capstone (Route A)

A client agent for the **Storefront** seat of AgentSwitch. It drives the live
platform over MCP (JSON-RPC at `/api/mcp`) and uses **Gemini** for language,
never for numbers. It answers the seat's request against live, shared data:

> "How did the launch coupon perform, and find any order where payment and stock disagree."

Built and run first against **Suryodaya Precision Works** (India, GST);
`--biz us` points the same code at Keystone Precision Works LLC (US).

## Quick start

```bash
uv sync
cp .env.example .env              # add GEMINI_API_KEY; AS_* URLs are pre-filled
uv run python -m seat8 login --biz in          # prompts for the seat password; caches a token in .secrets/
uv run python -m seat8 whoami                  # roles + allowed_apps: storefront, agent, crm
uv run python -m seat8 ask "How did the launch coupon perform, and find any order where payment and stock disagree."
```

| Command | What it does |
|---|---|
| `login [--from-env]` | Password at a hidden prompt (or `AS_PASSWORD_IN/US` from `.env`) → token in `.secrets/token_<biz>.json`. The password is never stored by the code. |
| `whoami` | `/api/auth/me` |
| `probe` | Dumps `tools/list`, `/api/schemas`, `/api/agent/tools` to `catalog/<biz>/` |
| `call <Tool> '<json>'` | One raw MCP call, typed error on failure |
| `ask "<question>"` | The agent. **Dry run by default** (reads only). `--write` lets it write to the team's own agent space. `--no-llm` uses keyword routing and a template answer. `--today YYYY-MM-DD` pins the date age rules use. |

Global option `--biz in|us` (before or after the command). Default `in`.

## How it works

```
question ──► parse (Gemini JSON schema; keyword fallback)
                │  asks: coupon_performance, payment_stock_mismatch · coupon_ref · out_of_scope · other
                ├─ other in-scope question ─► chat loop (Gemini function calling over READ-ONLY tools)
                ▼
          snapshot (one read: every WebOrder, every Coupon, the SalesOrder behind each web order)
                ▼
          finding (seat8/storefront.py: pure code, no LLM) ── each section answered / refused / ambiguous
                ▼
          act (--write only): re-read flagged orders → AgentSession → one AgentEscalation to the
                Stock seat (reused if an identical one is open) → AgentMemory with the finding
                ▼
          narrate (Gemini) ─► verify every order number / figure / "filed" claim against the finding
                              one rewrite, else a deterministic template
```

* **Numbers are computed in code, never by the model.** The model routes the request and writes prose; `verify_prose` rejects prose with an order number or figure that is not in the finding, or a claim that something was filed during a dry run.
* **Typed errors.** `seat8/mcp.py` raises `MCPError(code)` with the platform's `error.data.code` (`not_found`, `invalid_arguments`, `invalid_transition`, `tool_not_available`) or a transport code (`auth`, `forbidden`, `transient`). Tool failures arrive as HTTP 200 with an error envelope; the client never treats 200 as success by itself.
* **Shared book.** The snapshot is stamped (`taken_at`) and flags `pagination_complete=false` if rows moved while paging. Before acting, flagged orders are **re-read** and only those whose flag still holds are escalated; the rest are reported as `changed_since_snapshot`.
* **Every run is on disk first**: `runs/<run_id>/run.json` (written with `status: running` before any work), `calls.jsonl` (every MCP call), `llm.jsonl` (every model call, tokens), `snapshot.json`, `chat_trace.json`.

## Definitions

**Coupon performance.** The coupon is resolved from what the user said: an exact code/id, else every
word of the phrase must appear in a coupon's code or description. No match → **refused** (never guessed);
several → **ambiguous** with candidates. For a resolved coupon: orders carrying its code (by status),
paid orders, paid revenue, discount given, average paid order with vs without the coupon in its validity
window, and whether `used_count` agrees with the orders. A book-health block is always included.

**Payment vs stock.** This seat cannot read stock levels (no Bin/StockEntry/Warehouse tools;
`endpoint.inventory.shipping_board` refuses with 403). The fulfilment side it *can* read is the
SalesOrder behind each web order (`delivered_status`, `status`), which is what reserves and ships stock.
"Payment captured" = `funding_amount > 0` or a `payment_gateway_payment_id`.

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

The stock-level half goes to the Stock seat as one `AgentEscalation` (`reason_code: needs_another_app`)
listing the high-severity orders that still hold after the re-read.

## What the live book says (Suryodaya, 2026-10-10)

* 109 web orders: 94 `pending_payment`, 14 `cancelled`, 1 `confirmed`. 0 carry a coupon code.
* 105 coupons, none identifiable as a "launch" coupon → the coupon part is **refused with evidence**.
  48 have `valid_to` before `valid_from`; 30 are used beyond `usage_limit`; 79 report `used_count > 0`
  with no order carrying their code (total claimed redemptions 1,002,596 vs 0 on orders).
* Payment vs stock: **3 `shipped_unpaid`** (WEB-2026-00074, -00087, -00100), **6 `stock_held_for_cancelled`**
  (WEB-2026-00014, -00022, -00044, -00056, -00089, -00092), 83 `unpaid_holding_stock`.

## Harness

```bash
uv run python -m harness.runner [--tasks id,id] [--no-llm] [--write]   # live: read, run, read; saves files
uv run python -m harness.score runs/batches/<batch_id>                  # offline: files only, re-runnable
```

Run, then score, never both at once. Per task the runner saves `ground_truth_before.json`, the agent's
run (subprocess `python -m seat8 ask ... --run-id`), `ground_truth_after.json` and `stdout.txt`, plus a
batch `manifest.json`. The scorer applies generic checks (run finished; a dry run made only reads; a
write run wrote only to the team's agent space; `expect.path` and `expect.sections`) and each task's
verifiers, then writes `score.json` per run and `report.md` per batch. Statuses: pass / fail / drift /
error; drift means another team changed the data mid-run in a way that explains the difference.

* **Tasks**: `harness/tasks.json`. **Verifiers**: `harness/verifiers.py`. A verifier is an
  `observe(client, task)` that reads the platform itself (never importing the agent's logic) and a pure
  `check(task, run, before, after)`.
* The one task and verifier named `SAMPLE…` / `sample_…` were written by Claude as a pattern. They are
  not part of the team's graded test set.

## Tests

```bash
uv run pytest
```

The graded tests are **written by hand by the team** and live in `tests/`. `tests/test_sample_classify.py`
is a single Claude-written sample showing the pattern (pure function, no network), and is not graded.
The functions easiest to test offline: `storefront.classify_order`, `resolve_coupon`,
`coupon_book_health`, `coupon_metrics`, `payment_stock_mismatches` (on a hand-built `Snapshot`),
`agent.keyword_parse`, `agent.verify_prose`, `agent.render_template`, `llm.to_gemini_schema`.

## Platform bugs

Candidates found while building, with repro, are in [`docs/bugs.md`](docs/bugs.md). They are filed
through the in-app "Report a problem" button or `POST /api/bug-report`.

## Layout

```
seat8/
  config.py     .env, business URLs, TLS context (certifi; Windows' store rejects the LE chain)
  auth.py       login → cached token in .secrets/ (gitignored)
  mcp.py        JSON-RPC client, typed errors, per-call hook
  probe.py      catalogue dump → catalog/<biz>/
  storefront.py snapshot, coupon performance, payment-vs-stock rules, re-read
  llm.py        Gemini (google-genai): JSON output, text, function-calling loop, schema adapter
  agent.py      parse → snapshot → finding → act → narrate+verify
  runrec.py     runs/<run_id>/ record
  __main__.py   CLI
harness/        runner, score, verifiers, tasks.json
tests/          hand-written tests (+ one marked sample)
catalog/in/     tools.json, tools_summary.md, schemas_seat.json, agent_tools.json, me.json
docs/           bugs.md
```

## Security

`.env` (API keys, optional seat password) and `.secrets/` (bearer tokens) are gitignored. Run records
(`runs/`) hold live business data and are gitignored too.

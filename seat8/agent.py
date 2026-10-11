"""The Storefront agent: one request in, one finding in the database, one verified answer out.

    context    store currency, tax regime and labels from /api/storefront/locale
    parse      Gemini turns the request into asks, a coupon reference, named
               orders and the claims made about them, and anything out of scope
               or asking for a change. Keyword fallback without a model.
    snapshot   one read of orders, coupons and linked sales orders
    sections   every answer computed in code (storefront.py): answered,
               refused, ambiguous or not_found, never invented
    freshness  flagged orders are re-read before answering; rows that changed
               since the snapshot are reported as changed, not acted on
    act        (write=True only) AgentSession, then one escalation to the Stock
               seat for the orders that still disagree. When stock is not
               visible and orders still disagree, the escalation is required
               before the finding may be recorded; a failed attempt is recorded.
    record     exactly one finding per run in this team's private AgentMemory,
               validated first (no required field missing or null)
    narrate    Gemini writes prose from the finding; every order number, figure
               and "filed" claim is checked against it, else a template is used

Every step lands in runs/<run_id>/ before anything is scored.
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import date
from pathlib import Path

from . import storefront as sf
from .config import business
from .finding import FindingRecorder, FindingRejected, compact
from .llm import Gemini, LLMUnavailable, ToolLoop, make_llm
from .mcp import MCPClient, MCPError
from .runrec import RunRecord
from .seat import stock_visibility, store_context

ASKS = ("coupon_performance", "payment_stock_mismatch", "order_check", "stock_level")
ESCALATION_PREFIX = "T08-Stock check"
BARRIER_ENV = "SEAT8_BARRIER_DIR"   # set by the harness to pause between snapshot and re-read

INTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "asks": {"type": "array", "items": {"type": "string", "enum": list(ASKS)}},
        "coupon_ref": {"type": ["string", "null"],
                       "description": "the coupon as the user named it: a code, or words like 'launch'"},
        "order_refs": {"type": "array", "items": {"type": "string"},
                       "description": "order numbers the user named, e.g. WEB-2026-00109"},
        "order_claims": {"type": "array", "items": {"type": "string", "enum": list(sf.CLAIMS)},
                         "description": "what the user asserts about the named orders"},
        "change_request": {"type": ["string", "null"],
                           "description": "any request to cancel, edit, delete, refund or otherwise change records"},
        "out_of_scope": {"type": "array", "items": {"type": "string"},
                         "description": "parts that belong to another business function"},
        "other": {"type": ["string", "null"],
                  "description": "an in-scope storefront question that fits none of the asks"},
    },
    "required": ["asks", "coupon_ref", "order_refs", "order_claims", "change_request",
                 "out_of_scope", "other"],
}

INTENT_SYSTEM = """You route requests for an online-store agent. It answers, over live data:
  coupon_performance      how a coupon / discount code performed
  payment_stock_mismatch  orders whose payment state and stock/fulfilment state disagree
  order_check             questions about specific orders named by number (also fill order_refs,
                          and order_claims with what the user asserts, e.g. "shipped without
                          payment" -> ["shipped", "unpaid"])
  stock_level             how many units are in stock / on hand / in a warehouse
Return JSON. coupon_ref: the coupon exactly as named (e.g. "launch coupon", "FESTIVE10") or null.
change_request: any request to cancel, edit, delete, refund or change records, quoted; else null.
out_of_scope: parts belonging to another function (payroll, salaries, accounting ledgers, invoices,
manufacturing, HR, contracts, email campaigns). other: an in-scope store question that fits none of
the asks. Do not answer the question."""

NARRATE_SYSTEM = """You write the final answer of an online-store agent for a business owner.
You are given CONTEXT (currency, tax regime, labels) and FINDING, computed from live data. Rules:
- Use only facts, numbers and order numbers that appear in FINDING. Never estimate or invent.
- Amounts are in CONTEXT.base_currency.
- Lead with the direct answer to each requested part, in the order asked.
- If a section is refused, ambiguous or not_found, say so plainly and say what is needed.
- If a named order's claims include holds=false, correct the user's premise explicitly.
- If FINDING.dry_run is true, nothing was written: say an escalation WOULD be filed (dry run),
  never that it was filed. Only say "filed" when FINDING.writes.escalation exists.
- If freshness.changed_since_snapshot is non-empty, say those orders changed while you were checking.
- Mention that the data is a live snapshot taken at FINDING.snapshot.taken_at.
- Be concise: short paragraphs or bullets, under 300 words. Plain text, no tables."""

POLICY_REFUSAL = ("This agent reports and escalates; it does not cancel, edit or delete store records "
                  "on request. A person with the storefront role should make that change after review.")


# ── parse ───────────────────────────────────────────────────────────────────

_ORDER_NO = re.compile(r"\bWEB-\d{4}-\d{5}\b", re.I)


def parse_request(question: str, llm: Gemini | None) -> dict:
    parsed = None
    if llm is not None:
        try:
            parsed = llm.generate_json(INTENT_SYSTEM, question, INTENT_SCHEMA)
            parsed["parser"] = "llm"
        except LLMUnavailable:
            parsed = None
    parsed = parsed or keyword_parse(question)
    for k, default in (("asks", []), ("coupon_ref", None), ("order_refs", []), ("order_claims", []),
                       ("change_request", None), ("out_of_scope", []), ("other", None)):
        if parsed.get(k) is None or (isinstance(default, list) and not isinstance(parsed.get(k), list)):
            parsed[k] = default
    parsed["asks"] = [a for a in parsed.get("asks") or [] if a in ASKS]
    # order numbers are matched by pattern too: the model must not drop or invent one
    refs = sorted({m.upper() for m in _ORDER_NO.findall(question)})
    if refs:
        parsed["order_refs"] = refs
        if "order_check" not in parsed["asks"]:
            parsed["asks"].append("order_check")
    else:
        parsed["order_refs"] = []
        parsed["asks"] = [a for a in parsed["asks"] if a != "order_check"]
    return parsed


def keyword_parse(question: str) -> dict:
    q = question.lower()
    asks = []
    if "coupon" in q or "discount code" in q or "promo" in q:
        asks.append("coupon_performance")
    if ("payment" in q or "paid" in q) and ("stock" in q or "inventory" in q or "fulfil" in q):
        asks.append("payment_stock_mismatch")
    if re.search(r"how many .*(in stock|on hand|units)|stock level|in the warehouse", q):
        asks.append("stock_level")
    ref = None
    m = (re.search(r"coupon\s+([A-Z0-9][A-Z0-9/_-]{2,})", question)
         or re.search(r"(?<![\w/-])([A-Z0-9][A-Z0-9/_-]{2,})\s+coupon", question))
    if m:
        ref = m.group(1)
    elif "launch" in q:
        ref = "launch coupon"
    claims = [c for c, words in {"unpaid": ("unpaid", "without payment", "not paid"),
                                 "shipped": ("shipped", "ship ", "dispatched"),
                                 "delivered": ("delivered",), "cancelled": ("cancelled", "canceled")}.items()
              if any(w in q for w in words)]
    change = question if re.search(r"\b(cancel|delete|refund|edit|change|update)\b", q) else None
    oos = [w for w in ("payroll", "salary", "net pay", "invoice", "ledger", "work order", "employee")
           if w in q]
    return {"asks": asks, "coupon_ref": ref, "order_refs": [], "order_claims": claims,
            "change_request": change, "out_of_scope": oos,
            "other": None if (asks or change or oos) else question, "parser": "keywords"}


# ── freshness + act ────────────────────────────────────────────────────────

def _barrier(rec: RunRecord, snapshot_taken_at: str) -> None:
    """Harness hook: announce the snapshot is taken, wait until told to continue.
    Lets a test change a row 'underneath' the agent at a known moment."""
    d = os.environ.get(BARRIER_ENV)
    if not d:
        return
    d = Path(d)
    d.mkdir(parents=True, exist_ok=True)
    (d / "ready.json").write_text(json.dumps({"run_id": rec.run_id, "snapshot_taken_at": snapshot_taken_at}),
                                  encoding="utf-8")
    for _ in range(360):
        if (d / "go").exists():
            return
        time.sleep(0.5)
    rec.warn("barrier timed out; continuing")


def freshness(client: MCPClient, mm: dict, today: date) -> list[dict]:
    """Re-read every high/medium flagged order; return those whose flag still holds."""
    flagged = (mm.get("high") or []) + (mm.get("medium") or [])
    recheck = sf.reread_orders(client, flagged, today)
    mm["freshness"] = {"rechecked": len(flagged), "still_holds": len(recheck["still_holds"]),
                       "changed_since_snapshot": recheck["changed_since_snapshot"],
                       "unreadable": recheck["unreadable"]}
    return recheck["still_holds"]


def _open_escalation(client: MCPClient, subject: str) -> dict | None:
    try:
        rows = client.call("AgentEscalation.list", {"subject": subject, "limit": 20}).get("data") or []
    except MCPError:
        return None
    for r in rows:
        if r.get("subject") == subject and r.get("status") not in ("resolved", "closed", "cancelled", "withdrawn"):
            return r
    return None


def escalate(client: MCPClient, session_id: str, still: list[dict]) -> dict:
    numbers = sorted({m["order_number"] for m in still})
    subject = f"{ESCALATION_PREFIX}: {len(numbers)} web orders where payment and fulfilment disagree"
    try:
        existing = _open_escalation(client, subject)
        if existing:
            return {"id": existing.get("id"), "reused": True, "subject": subject, "orders": numbers}
        esc = client.call("AgentEscalation.create", {
            "session_id": session_id, "subject": subject, "reason_code": "needs_another_app",
            "channel": "api",
            "reason": ("Storefront (Team 08) cannot read stock levels. Please confirm physical stock / "
                       "reservation for these web orders, where payment state and sales-order "
                       "fulfilment disagree: " + ", ".join(numbers))})
        return {"id": esc.get("id"), "reused": False, "subject": subject, "orders": numbers}
    except MCPError as e:  # a failed escalation is still recorded as an attempt
        return {"id": None, "failed": True, "reason_code": "escalation_failed",
                "error": f"{e.code}: {e}"[:300], "subject": subject, "orders": numbers}


# ── narrate + verify (prose is checked against the finding) ────────────────

_ORDER_RE = re.compile(r"\b(?:WEB|SO)-\d{4}-\d{5}\b")


def verify_prose(prose: str, finding: dict) -> list[str]:
    """Problems with the prose: an order number not in the finding, a figure
    (3+ digits) that appears nowhere in the finding, or a claim that something
    was filed/escalated when the finding records no escalation."""
    blob = json.dumps(finding, default=str)
    problems = [f"order {n} is not in the finding" for n in set(_ORDER_RE.findall(prose)) if n not in blob]
    if not (finding.get("writes") or {}).get("escalation", {}).get("id") and re.search(
            r"\b(I|we)\s+(have\s+)?(filed|raised|escalated|created|sent)\b|\bhas been (filed|escalated|raised)\b",
            prose, re.I):
        problems.append("claims an escalation/write happened, but nothing was written")
    numbers_in_finding = {re.sub(r"[,\s]", "", x) for x in re.findall(r"\d[\d,.]*", blob)}
    numbers_in_finding |= {x.rstrip("0").rstrip(".") for x in numbers_in_finding if "." in x}
    for raw in re.findall(r"(?<![\w-])\d[\d,]*(?:\.\d+)?", _ORDER_RE.sub("", prose)):
        n = raw.replace(",", "")
        if len(n.replace(".", "")) < 3 or re.fullmatch(r"20\d\d", n):
            continue
        if n not in numbers_in_finding and n.rstrip("0").rstrip(".") not in numbers_in_finding:
            problems.append(f"figure {raw} is not in the finding")
    return problems


def render_template(finding: dict) -> str:
    out = [f"Live snapshot of {finding['business']} taken {finding.get('snapshot', {}).get('taken_at')}."]
    s = finding["sections"]
    cp = s.get("coupon_performance")
    if cp:
        if cp["status"] == "answered":
            out.append(f"Coupon {cp['coupon']['code']}: {cp['orders_using_it']} orders used it, "
                       f"{cp['paid_orders']} paid, revenue {cp['paid_revenue']}, discount given "
                       f"{cp['discount_given']}. Its used_count is {cp['used_count_recorded']}, which "
                       f"{'matches' if cp['used_count_matches_orders'] else 'does not match'} the orders.")
        else:
            out.append(f"Coupon: {cp['status']}. {cp.get('reason', '')} {cp.get('note', '')}".strip())
    mm = s.get("payment_stock_mismatch")
    if mm:
        out.append(f"Payment vs stock: checked {mm['orders_checked']} orders; {len(mm['high'])} high and "
                   f"{len(mm['medium'])} medium disagreements: " +
                   ", ".join(f"{m['order_number']} ({m['rule']})" for m in mm["high"] + mm["medium"]))
        fr = mm.get("freshness") or {}
        if fr.get("changed_since_snapshot"):
            out.append("Changed while checking: " +
                       ", ".join(c["order_number"] for c in fr["changed_since_snapshot"]))
        if mm.get("low_count"):
            out.append(f"{mm['low_count']} more unpaid orders are holding stock (low severity).")
        out.append("Stock levels: " + mm["stock_levels"]["reason"])
        if mm["stock_levels"].get("escalation"):
            out.append(f"Escalation: {mm['stock_levels']['escalation']}.")
    oc = s.get("order_check")
    if oc:
        for o in oc["orders"]:
            if o["status"] == "not_found":
                out.append(o["reason"])
            else:
                wrong = [c["claim"] for c in o.get("claims", []) if c["holds"] is False]
                out.append(f"{o['order_number']}: status {o['order_status']}, payment captured "
                           f"{o['payment_captured']}, delivered {o['delivered']}, flags {o['flags']}."
                           + (f" Not true: {wrong}." if wrong else ""))
    sl = s.get("stock_level")
    if sl:
        out.append(sl["reason"])
    for r in finding["refusals"]:
        out.append(f"Not answered: {r}")
    return "\n".join(out)


def narrate(finding: dict, context: dict, llm: Gemini | None, rec: RunRecord) -> tuple[str, str]:
    if llm is None:
        return render_template(finding), "template"
    # the compact finding (what is stored in AgentMemory) keeps every number and order the
    # prose may cite, at a size any model's context takes; prose is still verified against it
    prompt = ("CONTEXT:\n" + json.dumps(context, default=str) + "\n\nFINDING:\n" +
              json.dumps(compact(finding), default=str)[:30000])
    try:
        prose = llm.generate_text(NARRATE_SYSTEM, prompt)
        problems = verify_prose(prose, finding)
        if problems:
            rec.warn("narration rewrite: " + "; ".join(problems[:10]))
            prose = llm.generate_text(NARRATE_SYSTEM, prompt + "\n\nYour previous answer had these "
                                      "problems; fix them:\n- " + "\n- ".join(problems[:10]))
            problems = verify_prose(prose, finding)
            if problems:
                rec.warn("narration rejected, template used: " + "; ".join(problems[:10]))
                return render_template(finding), "template"
        return prose, "llm"
    except LLMUnavailable as e:
        rec.warn(f"llm unavailable, template used: {e}")
        return render_template(finding), "template"


# ── open questions ─────────────────────────────────────────────────────────

CHAT_SYSTEM = """You are the online-store agent for this business, working over live data through tools.
Only read; never write. Answer only from tool results, citing record numbers.
If a record does not exist, say so. If the question needs data outside the store (payroll,
accounting, manufacturing, stock levels, HR), say this seat cannot see it and that the request must
go to that team via the EA. Never guess."""

CHAT_ENTITIES = {"WebOrder", "Coupon", "Item", "SalesOrder", "StockAlert", "ShippingMethod",
                 "PricingRule", "ProductCategory", "StorefrontSettings", "Party"}


def chat(client: MCPClient, question: str, llm: Gemini, rec: RunRecord) -> dict:
    readable = {t["name"]: t for t in client.list_tools()
                if t["name"].split(".")[0] in CHAT_ENTITIES and t["name"].split(".")[-1] in ("list", "get")}
    loop = ToolLoop(llm, readable, client.call, max_steps=10)
    answer = loop.run(CHAT_SYSTEM, question)
    rec.write("chat_trace.json", loop.trace)
    return {"status": "error" if loop.stopped_at_budget else "answered", "answer": answer,
            "tools_used": sorted({t["tool"] for t in loop.trace}),
            "stopped_at_budget": loop.stopped_at_budget}


# ── entry ───────────────────────────────────────────────────────────────────

def run(question: str, client: MCPClient, biz_key: str = "in", write: bool = False,
        use_llm: bool = True, today: date | None = None, run_id: str | None = None) -> dict:
    today = today or date.today()
    biz = business(biz_key)
    rec = RunRecord(question, biz.key, run_id=run_id, write=write, today=today.isoformat())
    client.on_call = rec.log_call
    recorder = FindingRecorder(client, rec.run_id)
    llm = None
    if use_llm:
        try:
            llm = make_llm(on_call=rec.log_llm)
            rec.data["model"] = f"{llm.provider}:{llm.model}"
        except LLMUnavailable as e:
            rec.warn(str(e))
    rec.save()
    finding: dict = {"run_id": rec.run_id, "business": biz.name, "dry_run": not write,
                     "path": None, "asks": [], "sections": {}, "refusals": []}
    try:
        context = store_context(client)
        finding["context"] = context
        intent = parse_request(question, llm)
        rec.data["intent"] = intent
        finding["asks"] = intent["asks"]
        finding["refusals"] = [f"'{p}' belongs to another team's app; ask that team through the EA."
                               for p in intent.get("out_of_scope") or []]
        if intent.get("change_request"):
            finding["refusals"].append(POLICY_REFUSAL)

        if not intent["asks"]:
            if intent.get("other") and llm is not None and not finding["refusals"]:
                finding["path"] = "chat"
                finding["sections"]["chat"] = chat(client, question, llm, rec)
                answer, how = finding["sections"]["chat"]["answer"], "llm"
            else:
                finding["path"] = "refusal"
                answer = " ".join(finding["refusals"]) or (
                    "I answer coupon performance, payment-vs-stock and order questions for this store.")
                how = "template"
            finding["snapshot"] = {"taken_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
            _record(recorder, finding, rec)
            rec.finish("done", finding=finding, answer=answer, narration=how, path=finding["path"],
                       llm_usage=llm.usage if llm else None)
            return rec.data

        finding["path"] = "graph"
        asks = intent["asks"]
        need_so = "payment_stock_mismatch" in asks or "order_check" in asks
        snap = sf.take_snapshot(client, need_orders=True, need_coupons="coupon_performance" in asks,
                                need_sales_orders=need_so)
        finding["snapshot"] = snap.summary()
        if not snap.complete:
            rec.warn("pagination incomplete: rows moved while reading; figures may be partial")
        rec.write("snapshot.json", {"summary": snap.summary(), "orders": snap.orders,
                                    "coupons": snap.coupons, "sales_orders": snap.sales_orders})
        sections = finding["sections"]
        if "coupon_performance" in asks:
            sections["coupon_performance"] = sf.coupon_performance(snap, intent.get("coupon_ref"))
        if "order_check" in asks:
            sections["order_check"] = sf.order_check(snap, intent["order_refs"],
                                                     intent.get("order_claims") or [], today)
        if "stock_level" in asks:
            vis = stock_visibility(client)
            sections["stock_level"] = {
                "status": "answered" if vis["visible"] else "refused", "probes": vis["probes"],
                "reason": ("Stock quantities are not visible to the storefront seat: the stock entities "
                           "belong to another app (REST " +
                           ", ".join(f"{p['entity']}={p['access']}" for p in vis["probes"]) +
                           "). Ask the Stock team through the EA.")}
        still: list[dict] = []
        if "payment_stock_mismatch" in asks:
            mm = sections["payment_stock_mismatch"] = sf.payment_stock_mismatches(snap, today)
            mm["stock_levels"]["probes"] = stock_visibility(client)["probes"]
            rec.data["finding"] = finding
            rec.save()
            _barrier(rec, snap.taken_at)
            still = freshness(client, mm, today)

        if write:
            session = client.call("AgentSession.create", {
                "title": "T08-Storefront agent run", "channel": "api", "actor_kind": "system",
                "metadata": json.dumps({"run_id": rec.run_id})})
            finding["writes"] = {"session_id": session.get("id")}
            if still:  # stock is not visible here: a person must check, so escalation is required
                esc = escalate(client, session.get("id"), still)
                finding["writes"]["escalation"] = esc
                sections["payment_stock_mismatch"]["stock_levels"]["escalation"] = esc
        elif still:
            sections["payment_stock_mismatch"]["stock_levels"]["escalation"] = {
                "would_file": True, "to": "Stock seat (needs_another_app)",
                "orders": sorted({m["order_number"] for m in still})}

        _record(recorder, finding, rec)
        rec.data["finding"] = finding
        rec.save()
        answer, how = narrate(finding, context, llm, rec)
        rec.finish("done", finding=finding, answer=answer, narration=how, path="graph",
                   llm_usage=llm.usage if llm else None)
    except Exception as e:  # the run record, and a finding if possible, must survive any failure
        if not recorder.memory_id and finding.get("path"):
            finding["sections"].setdefault("run", {"status": "error", "error": f"{type(e).__name__}: {e}"[:300]})
            try:
                _record(recorder, finding, rec)
            except Exception:  # noqa: BLE001 - best effort only
                pass
        rec.finish("error", finding=finding, error=f"{type(e).__name__}: {e}")
        raise
    return rec.data


def _record(recorder: FindingRecorder, finding: dict, rec: RunRecord) -> None:
    try:
        memory_id = recorder.record(finding, (finding.get("writes") or {}).get("session_id"))
        rec.data["finding_memory_id"] = memory_id
    except (FindingRejected, MCPError) as e:
        rec.warn(f"finding not recorded: {e}")
        rec.data["finding_memory_id"] = None
    rec.save()

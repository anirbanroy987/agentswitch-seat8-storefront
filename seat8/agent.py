"""The Storefront agent: one request in, one verified answer out.

    parse      Gemini turns the request into asks (coupon_performance,
               payment_stock_mismatch), a coupon reference and anything out of
               scope. Keyword fallback when the model is unavailable.
    snapshot   one read of orders, coupons and linked sales orders
    finding    every section computed in code (storefront.py): answered,
               refused, ambiguous or escalated, never invented
    act        (only with write=True) re-read flagged orders, then open an
               AgentSession, file one escalation to the Stock seat for the
               stock-level part, store the finding in AgentMemory
    narrate    Gemini writes the prose from the finding; every order number and
               figure in it is checked against the finding, else a template
               answer is used

Every step lands in runs/<run_id>/ before anything is scored.
"""
from __future__ import annotations

import json
import re
from datetime import date

from . import storefront as sf
from .config import business
from .llm import Gemini, LLMUnavailable, ToolLoop
from .mcp import MCPClient, MCPError
from .runrec import RunRecord

ASKS = ("coupon_performance", "payment_stock_mismatch")
ESCALATION_PREFIX = "T08-Stock check"

INTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "asks": {"type": "array", "items": {"type": "string", "enum": list(ASKS)}},
        "coupon_ref": {"type": ["string", "null"],
                       "description": "the coupon as the user named it: a code, or words like 'launch'"},
        "out_of_scope": {"type": "array", "items": {"type": "string"},
                         "description": "parts this storefront seat cannot answer (payroll, accounting, "
                                        "manufacturing, HR, other apps)"},
        "other": {"type": ["string", "null"],
                  "description": "an in-scope storefront question that is neither of the two asks"},
    },
    "required": ["asks", "coupon_ref", "out_of_scope", "other"],
}

INTENT_SYSTEM = """You route requests for a storefront (web shop) agent.
The agent answers exactly two kinds of question over live data:
  coupon_performance      how a coupon/discount code performed (redemptions, revenue, discount)
  payment_stock_mismatch  orders whose payment state and stock/fulfilment state disagree
Return JSON. Put the coupon exactly as the user named it in coupon_ref (e.g. "launch coupon",
"FESTIVE10"), or null. List any part that belongs to another business function (payroll, salaries,
accounting ledgers, invoices, manufacturing, HR, contracts, email campaigns) in out_of_scope.
Any other storefront question goes in other. Do not answer the question."""

NARRATE_SYSTEM = """You write the final answer of a storefront agent for a business owner.
You are given FINDING, a JSON object computed from live data. Rules:
- Use only facts, numbers and order numbers that appear in FINDING. Never estimate or invent.
- Lead with the direct answer to each requested part, in the order asked.
- If a section is refused, ambiguous or not visible, say so plainly and say what is needed.
- If FINDING.dry_run is true, nothing was written: say an escalation WOULD be filed (dry run),
  never that it was filed. Only say "filed" when FINDING.writes.escalation exists.
- Mention that the data is a live snapshot taken at FINDING.snapshot.taken_at.
- Be concise: short paragraphs or bullets, under 300 words. Plain text, no tables."""


# ── parse ───────────────────────────────────────────────────────────────────

def parse_request(question: str, llm: Gemini | None) -> dict:
    if llm is not None:
        try:
            parsed = llm.generate_json(INTENT_SYSTEM, question, INTENT_SCHEMA)
            parsed["asks"] = [a for a in parsed.get("asks") or [] if a in ASKS]
            parsed["parser"] = "llm"
            return parsed
        except LLMUnavailable:
            pass
    return keyword_parse(question)


def keyword_parse(question: str) -> dict:
    q = question.lower()
    asks = []
    if "coupon" in q or "discount code" in q or "promo" in q:
        asks.append("coupon_performance")
    if ("payment" in q or "paid" in q) and ("stock" in q or "inventory" in q or "fulfil" in q):
        asks.append("payment_stock_mismatch")
    ref = None
    m = re.search(r"coupon\s+([A-Z0-9][A-Z0-9/_-]{2,})", question)
    if m:
        ref = m.group(1)
    elif "launch" in q:
        ref = "launch coupon"
    oos = [w for w in ("payroll", "salary", "invoice", "ledger", "work order", "employee")
           if w in q]
    return {"asks": asks, "coupon_ref": ref, "out_of_scope": oos,
            "other": None if asks else question, "parser": "keywords"}


# ── act ─────────────────────────────────────────────────────────────────────

def _open_escalation(client: MCPClient, subject: str) -> dict | None:
    try:
        rows = client.call("AgentEscalation.list", {"subject": subject, "limit": 20}).get("data") or []
    except MCPError:
        return None
    for r in rows:
        if r.get("subject") == subject and r.get("status") not in ("resolved", "closed", "cancelled"):
            return r
    return None


def act(client: MCPClient, finding: dict, rec: RunRecord, today: date) -> dict:
    """Writes go only to this team's agent space: a session, at most one
    escalation (reused if an identical open one exists) and one memory."""
    writes: dict = {}
    session = client.call("AgentSession.create", {
        "title": "T08-Storefront agent run", "channel": "api", "actor_kind": "system",
        "metadata": json.dumps({"run_id": rec.run_id})})
    writes["session_id"] = session.get("id")

    mm = finding["sections"].get("payment_stock_mismatch")
    if mm and mm.get("status") == "answered" and mm.get("high"):
        recheck = sf.reread_orders(client, mm["high"], today)
        mm["recheck"] = {"still_holds": len(recheck["still_holds"]),
                         "changed_since_snapshot": recheck["changed_since_snapshot"],
                         "unreadable": recheck["unreadable"]}
        numbers = [m["order_number"] for m in recheck["still_holds"]]
        if numbers:
            subject = f"{ESCALATION_PREFIX}: {len(numbers)} web orders where payment and fulfilment disagree"
            existing = _open_escalation(client, subject)
            if existing:
                writes["escalation"] = {"id": existing.get("id"), "reused": True}
            else:
                esc = client.call("AgentEscalation.create", {
                    "session_id": writes["session_id"], "subject": subject,
                    "reason_code": "needs_another_app", "channel": "api",
                    "reason": ("Storefront (Team 08) cannot read stock levels. Please confirm physical "
                               "stock / reservation for these web orders, where payment state and "
                               "sales-order fulfilment disagree: " + ", ".join(numbers))})
                writes["escalation"] = {"id": esc.get("id"), "reused": False}
            mm["stock_levels"]["escalation"] = {**writes["escalation"], "subject": subject,
                                                "to": "Stock seat (needs_another_app)"}

    memo = client.call("AgentMemory.create", {
        "category": "fact", "source": "system", "importance": 0.5,
        "session_id": writes["session_id"],
        "content": json.dumps({"run_id": rec.run_id, "asks": finding["asks"],
                               "summary": _summary_line(finding)})[:4000]})
    writes["memory_id"] = memo.get("id")
    return writes


def _summary_line(finding: dict) -> str:
    parts = []
    cp = finding["sections"].get("coupon_performance")
    if cp:
        parts.append(f"coupon:{cp['status']}")
    mm = finding["sections"].get("payment_stock_mismatch")
    if mm:
        parts.append(f"mismatches:{mm.get('counts_by_rule')}")
    return "; ".join(parts)


# ── narrate + verify ───────────────────────────────────────────────────────

_ORDER_RE = re.compile(r"\b(?:WEB|SO)-\d{4}-\d{5}\b")


def verify_prose(prose: str, finding: dict) -> list[str]:
    """Problems with the prose: an order number not in the finding, or a
    figure (3+ digits) that appears nowhere in the finding."""
    blob = json.dumps(finding, default=str)
    problems = [f"order {n} is not in the finding" for n in set(_ORDER_RE.findall(prose)) if n not in blob]
    if not (finding.get("writes") or {}).get("escalation") and re.search(
            r"\b(I|we)\s+(have\s+)?(filed|raised|escalated|created|sent)\b|\bhas been (filed|escalated|raised)\b",
            prose, re.I):
        problems.append("claims an escalation/write happened, but nothing was written (dry run)")
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
    out = [f"Live snapshot of {finding['business']} taken {finding['snapshot']['taken_at']}."]
    cp = finding["sections"].get("coupon_performance")
    if cp:
        if cp["status"] == "answered":
            out.append(f"Coupon {cp['coupon']['code']}: {cp['orders_using_it']} orders used it, "
                       f"{cp['paid_orders']} paid, revenue {cp['paid_revenue']}, discount given "
                       f"{cp['discount_given']}. The coupon records used_count "
                       f"{cp['used_count_recorded']}, which "
                       f"{'matches' if cp['used_count_matches_orders'] else 'does not match'} the orders.")
        else:
            out.append(f"Coupon: {cp['status']}. {cp.get('reason', '')} {cp.get('note', '')}".strip())
    mm = finding["sections"].get("payment_stock_mismatch")
    if mm:
        out.append(f"Payment vs stock: checked {mm['orders_checked']} orders; {len(mm['high'])} high-severity "
                   f"disagreements: " + ", ".join(f"{m['order_number']} ({m['rule']})" for m in mm["high"]))
        if mm.get("low_count"):
            out.append(f"{mm['low_count']} more unpaid orders are holding stock (low severity).")
        out.append("Stock levels: " + mm["stock_levels"]["reason"])
        if mm["stock_levels"].get("escalation"):
            out.append(f"Escalated to the Stock seat: {mm['stock_levels']['escalation']}.")
    for r in finding["refusals"]:
        out.append(f"Not answered: {r}")
    return "\n".join(out)


def narrate(finding: dict, llm: Gemini | None, rec: RunRecord) -> tuple[str, str]:
    if llm is None:
        return render_template(finding), "template"
    prompt = "FINDING:\n" + json.dumps(finding, default=str)[:60000]
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

CHAT_SYSTEM = """You are the storefront agent for this business, working over live data through tools.
Only read; never write. Answer only from tool results, citing record numbers.
If a record does not exist, say so. If the question needs data outside the storefront (payroll,
accounting, manufacturing, stock levels, HR), say this seat cannot see it and that the request must
go to that team via the EA. Never guess."""


def chat(client: MCPClient, tools: list[dict], question: str, llm: Gemini, rec: RunRecord) -> str:
    readable = {t["name"]: t for t in tools
                if t["name"].split(".")[0] in {"WebOrder", "Coupon", "Item", "SalesOrder", "StockAlert",
                                               "ShippingMethod", "PricingRule", "ProductCategory",
                                               "StorefrontSettings", "Party"}
                and t["name"].split(".")[-1] in ("list", "get")}
    loop = ToolLoop(llm, readable, client.call, max_steps=10)
    answer = loop.run(CHAT_SYSTEM, question)
    rec.write("chat_trace.json", loop.trace)
    return answer


# ── entry ───────────────────────────────────────────────────────────────────

def run(question: str, client: MCPClient, biz_key: str = "in", write: bool = False,
        use_llm: bool = True, today: date | None = None, run_id: str | None = None) -> dict:
    today = today or date.today()
    biz = business(biz_key)
    llm = None
    rec = RunRecord(question, biz.key, run_id=run_id, write=write, today=today.isoformat())
    client.on_call = rec.log_call
    if use_llm:
        try:
            llm = Gemini(on_call=rec.log_llm)
            rec.data["model"] = llm.model
        except LLMUnavailable as e:
            rec.warn(str(e))
    rec.save()
    try:
        intent = parse_request(question, llm)
        rec.data["intent"] = intent
        refusals = [f"'{p}' is outside the storefront seat; ask that team through the EA."
                    for p in intent.get("out_of_scope") or []]

        if not intent["asks"]:
            if intent.get("other") and llm is not None:
                answer = chat(client, client.list_tools(), question, llm, rec)
                rec.finish("done", answer=answer, path="chat", refusals=refusals)
                return rec.data
            answer = ("I can answer coupon performance and payment-vs-stock questions for this "
                      "storefront. " + " ".join(refusals)).strip()
            rec.finish("done", answer=answer, path="refusal", refusals=refusals,
                       finding={"asks": [], "refusals": refusals})
            return rec.data

        snap = sf.take_snapshot(
            client, need_orders=True, need_coupons="coupon_performance" in intent["asks"],
            need_sales_orders="payment_stock_mismatch" in intent["asks"])
        sections = {}
        if "coupon_performance" in intent["asks"]:
            sections["coupon_performance"] = sf.coupon_performance(snap, intent.get("coupon_ref"))
        if "payment_stock_mismatch" in intent["asks"]:
            sections["payment_stock_mismatch"] = sf.payment_stock_mismatches(snap, today)
        finding = {"business": biz.name, "asks": intent["asks"], "snapshot": snap.summary(),
                   "sections": sections, "refusals": refusals, "dry_run": not write}
        if not snap.complete:
            rec.warn("pagination incomplete: rows moved while reading; figures may be partial")
        rec.write("snapshot.json", {"summary": snap.summary(), "orders": snap.orders,
                                    "coupons": snap.coupons, "sales_orders": snap.sales_orders})
        rec.data["finding"] = finding
        rec.save()

        if write:
            try:
                finding["writes"] = act(client, finding, rec, today)
            except MCPError as e:
                rec.warn(f"platform write failed ({e.code}): {e}")
        else:
            mm = sections.get("payment_stock_mismatch")
            if mm and mm.get("high"):
                mm["stock_levels"]["escalation"] = {
                    "would_file": True, "to": "Stock seat (needs_another_app)",
                    "orders": [m["order_number"] for m in mm["high"]]}

        answer, how = narrate(finding, llm, rec)
        rec.finish("done", finding=finding, answer=answer, narration=how, path="graph",
                   llm_usage=llm.usage if llm else None)
    except Exception as e:  # the run record must survive any failure
        rec.finish("error", error=f"{type(e).__name__}: {e}")
        raise
    return rec.data

"""SAMPLE tests, written by Claude as patterns: NOT the team's graded, hand-written tests.

Layout borrowed from Team 04 (AgentSwitch_4): offline tests of pure functions
first. No network, no token, no model.
"""
from seat8.agent import keyword_parse, verify_prose
from seat8.mcp import FORBIDDEN, NOT_FOUND, _error_code_in_text, is_read_tool
from seat8.storefront import check_claim, coupon_book_health, resolve_coupon

COUPONS = [
    {"code": "HTL43792", "description": None, "used_count": 1, "usage_limit": 1},
    {"code": "HTLIM43753", "description": None, "used_count": 1, "usage_limit": 1},
    {"code": "LD6968/1860", "description": None, "used_count": 42, "usage_limit": 0,
     "valid_from": "2026-03-31", "valid_to": "2026-04-12"},
    {"code": "VC8379/1862", "description": "Depth Gauge", "used_count": 0, "usage_limit": 46,
     "valid_from": "2025-12-27", "valid_to": "2025-12-14"},
]


# Transport: an isError result carries its code in a JSON tail

def test_sample_refused_tool_maps_to_forbidden():
    text = 'This view reads DeliveryChallan... {"code": "request_refused", "status": 403}'
    assert _error_code_in_text(text) == FORBIDDEN


def test_sample_404_tail_maps_to_not_found():
    assert _error_code_in_text('gone {"status": 404}') == NOT_FOUND


def test_sample_only_reads_are_retried():
    assert is_read_tool("WebOrder.list") and not is_read_tool("WebOrder.cancel.pending_payment.cancelled")


# Coupons: resolve by code or words, never guess

def test_sample_exact_code_is_case_insensitive():
    outcome, hits = resolve_coupon(COUPONS, "ld6968/1860")
    assert outcome == "one" and hits[0]["code"] == "LD6968/1860"


def test_sample_two_matches_are_ambiguous():
    assert resolve_coupon(COUPONS, "HTL coupon")[0] == "many"


def test_sample_unknown_coupon_is_none():
    assert resolve_coupon(COUPONS, "launch coupon") == ("none", [])


def test_sample_book_health_counts_inverted_windows():
    assert coupon_book_health(COUPONS, orders=[])["inverted_validity_window"]["count"] == 1


# Named orders: a claim is judged against the facts

def test_sample_claim_unpaid_is_false_for_paid_order():
    facts = {"payment_captured": True, "delivered": False, "order_status": "confirmed"}
    assert check_claim("unpaid", facts) is False and check_claim("shipped", facts) is False


# Routing without a model

def test_sample_keyword_parse_flags_change_request():
    parsed = keyword_parse("Cancel every unpaid order older than a week.")
    assert parsed["change_request"] and parsed["asks"] == []


# Our prose check: nothing stated that the finding does not contain

def test_sample_prose_with_invented_order_is_rejected():
    finding = {"sections": {"x": {"order_number": "WEB-2026-00074"}}, "dry_run": True}
    assert verify_prose("See WEB-2026-00999.", finding) == ["order WEB-2026-00999 is not in the finding"]


def test_sample_prose_claiming_a_filing_in_dry_run_is_rejected():
    assert verify_prose("I have filed an escalation.", {"sections": {}, "dry_run": True})

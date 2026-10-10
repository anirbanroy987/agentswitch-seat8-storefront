"""Verifier registry: task files name verifiers by these keys."""
from . import _sample, t08

VERIFIERS = {
    # sample (Claude-written pattern)
    "sample_coupon_absent": (_sample.sample_coupon_absent_observe, _sample.sample_coupon_absent_check),
    # t08 task set (AI-assisted, declared)
    "mismatches_match_db": (t08.mismatches_observe, t08.mismatches_check),
    "coupon_absent": (t08.coupon_absent_observe, t08.coupon_absent_check),
    "coupon_named_matches_db": (t08.coupon_named_observe, t08.coupon_named_check),
    "coupon_ambiguous": (t08.coupon_ambiguous_observe, t08.coupon_ambiguous_check),
    "refusal_other_app": (t08.other_app_observe, t08.other_app_check),
    "stock_level_refused": (t08.stock_level_observe, t08.stock_level_check),
    "order_not_found": (t08.order_observe, t08.order_not_found_check),
    "order_facts_match_db": (t08.order_observe, t08.order_facts_check),
    "order_premise_corrected": (t08.order_observe, t08.order_premise_check),
    "no_change_on_request": (t08.no_change_observe, t08.no_change_check),
    "fixture_change_detected": (t08.fixture_observe, t08.fixture_changed_check),
    "escalation_filed": (t08.escalation_observe, t08.escalation_check),
}

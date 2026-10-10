"""SAMPLE test, written by Claude as a pattern: NOT one of the team's graded,
hand-written tests. Copy the shape, write your own cases in new files.

The rule under test (seat8.storefront.classify_order) is pure: an order dict,
its sales order dict and a date in, a list of rule names out. So these tests
need no network, no token and no model.
"""
from datetime import date

from seat8.storefront import classify_order

TODAY = date(2026, 10, 10)


def order(**kw):
    base = {"status": "pending_payment", "payment_method": "razorpay", "funding_amount": 0,
            "payment_gateway_payment_id": "", "grand_total": 100.0, "order_date": "2026-10-09"}
    base.update(kw)
    return base


def test_sample_delivered_without_payment_is_flagged():
    so = {"status": "confirmed", "delivered_status": "delivered"}
    assert "shipped_unpaid" in classify_order(order(), so, TODAY)

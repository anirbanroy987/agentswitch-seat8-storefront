"""SAMPLE tests, written by Claude as patterns: NOT the team's graded, hand-written tests.

Team 04 style: live, read-only tests against each business, one client per
module. Skipped when that business has no cached token
(`uv run python -m seat8 login --biz in|us`). Run only these with `-m live`.
"""
import pytest

from seat8 import auth
from seat8.config import business
from seat8.mcp import MCPClient
from seat8.seat import seat_capability

pytestmark = pytest.mark.live


def _client(key):
    biz = business(key)
    try:
        return MCPClient(biz.base_url, auth.load_token(biz))
    except RuntimeError:
        pytest.skip(f"no token for {biz.name}")


@pytest.fixture(scope="module")
def surya():
    return _client("in")


def test_sample_seat_is_storefront(surya):
    assert "storefront" in surya.rest_get("/api/auth/me")["allowed_apps"]


def test_sample_payroll_is_outside_the_seat(surya):
    assert seat_capability(surya, "SalarySlip")["access"] == "outside_seat"


def test_sample_weborder_list_reports_total(surya):
    page = surya.call("WebOrder.list", {"limit": 1})
    assert isinstance(page.get("total"), int) and page["total"] >= len(page["data"])

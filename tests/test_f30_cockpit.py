"""F3.0 Business Cockpit foundation: comparisons, breakdowns, cash semantics, signals."""
from datetime import date, datetime, timedelta
from unittest.mock import patch

import pytest
from flask import g, template_rendered
from sqlalchemy.dialects import postgresql

from models import db_session
from models.branch import Branch
from models.expense import Expense
from models.membership import Membership
from models.organization import Organization
from models.sale import PAYMENT_METHODS, SALE_CHANNELS, Sale
from models.work_session import WorkSession
from services import cockpit
from services.cockpit import (
    attention_signals,
    build_period_comparison,
    calculate_cash_position,
    cash_net_for_period,
    compare_margin,
    compare_value,
    previous_period,
    sales_by_channel,
    sales_by_payment_method,
)
from services.metrics import calculate_metrics, date_bounds
from services.tenancy import resolve_request_tenant

D = date


# ------------------------------------------------------------------ helpers

@pytest.fixture
def tenants(app):
    """Org A with branches A1/A2 and org B with B1 (ids only, so tests stay session-agnostic)."""
    a = Organization(name="A", slug="a", entity_type="company")
    b = Organization(name="B", slug="b", entity_type="company")
    db_session.add_all([a, b]); db_session.flush()
    branches = [Branch(organization_id=a.id, name="A1", slug="a1"), Branch(organization_id=a.id, name="A2", slug="a2"),
                Branch(organization_id=b.id, name="B1", slug="b1")]
    db_session.add_all(branches); db_session.commit()
    return {"A": (a.id, branches[0].id), "A2": (a.id, branches[1].id), "B": (b.id, branches[2].id)}


def sale(tenant, when, amount, payment="cash", channel="food_truck", **extra):
    org, branch = tenant
    db_session.add(Sale(organization_id=org, branch_id=branch, occurred_at=when, amount=amount,
                        payment_method=payment, channel=channel, **extra))


def expense(tenant, when, amount, payment="cash", kind="operational", category="Insumos", **extra):
    org, branch = tenant
    db_session.add(Expense(organization_id=org, branch_id=branch, occurred_at=when, amount=amount, category=category,
                           expense_type=kind, payment_method=payment, description="x", **extra))


def work_session(tenant, day, opened_h=10, closed_h=18, opening=20000, counted=None, status="closed", **extra):
    org, branch = tenant
    opened = datetime(day.year, day.month, day.day, opened_h)
    closed = None if status == "open" else opened + timedelta(hours=closed_h - opened_h)
    ws = WorkSession(organization_id=org, branch_id=branch, business_date=day, opened_at=opened, closed_at=closed,
                     opening_cash=opening, closing_cash_counted=counted, status=status, **extra)
    db_session.add(ws); db_session.flush()
    return ws


def bounds(start, end):
    return datetime.combine(start, datetime.min.time()), datetime.combine(end, datetime.max.time().replace(microsecond=0))


JUL, JUN = bounds(D(2026, 7, 1), D(2026, 7, 31)), bounds(D(2026, 6, 1), D(2026, 6, 30))


# ----------------------------------------------------------- previous period

@pytest.mark.parametrize("period,start,end,expected", [
    ("today", D(2026, 7, 15), D(2026, 7, 15), (D(2026, 7, 14), D(2026, 7, 14))),
    ("today", D(2026, 3, 1), D(2026, 3, 1), (D(2026, 2, 28), D(2026, 2, 28))),
    ("week", D(2026, 7, 13), D(2026, 7, 19), (D(2026, 7, 6), D(2026, 7, 12))),
    ("week", D(2026, 1, 5), D(2026, 1, 11), (D(2025, 12, 29), D(2026, 1, 4))),
    ("month", D(2026, 7, 1), D(2026, 7, 31), (D(2026, 6, 1), D(2026, 6, 30))),
    ("month", D(2026, 3, 1), D(2026, 3, 31), (D(2026, 2, 1), D(2026, 2, 28))),
    ("month", D(2026, 1, 1), D(2026, 1, 31), (D(2025, 12, 1), D(2025, 12, 31))),
    ("prev_month", D(2026, 6, 1), D(2026, 6, 30), (D(2026, 5, 1), D(2026, 5, 31))),
    ("prev_month", D(2026, 3, 1), D(2026, 3, 31), (D(2026, 2, 1), D(2026, 2, 28))),
    ("custom", D(2026, 7, 10), D(2026, 7, 14), (D(2026, 7, 5), D(2026, 7, 9))),
    ("custom", D(2026, 7, 10), D(2026, 7, 10), (D(2026, 7, 9), D(2026, 7, 9))),
    ("custom", D(2026, 7, 1), D(2026, 7, 31), (D(2026, 5, 31), D(2026, 6, 30))),  # 31 days: same length, adjacent
    ("custom", D(2026, 7, 29), D(2026, 8, 3), (D(2026, 7, 23), D(2026, 7, 28))),  # crosses a month boundary
])
def test_previous_period_definitions(period, start, end, expected):
    assert previous_period(period, start, end) == expected


def test_previous_period_unknown_kind_behaves_like_today_and_inverted_range_has_none():
    assert previous_period("bogus", D(2026, 7, 15), D(2026, 7, 15)) == (D(2026, 7, 14), D(2026, 7, 14))
    assert previous_period("custom", D(2026, 7, 20), D(2026, 7, 10)) is None


@pytest.mark.parametrize("period,expected", [
    ("today", (D(2026, 7, 14), D(2026, 7, 14))),
    ("week", (D(2026, 7, 6), D(2026, 7, 12))),          # today is Wed 2026-07-15 -> week Mon 13..Sun 19
    ("month", (D(2026, 6, 1), D(2026, 6, 30))),
    ("prev_month", (D(2026, 5, 1), D(2026, 5, 31))),    # selected = June -> May
])
def test_previous_period_matches_what_date_bounds_selects(period, expected):
    """The route feeds date_bounds' resolved dates into previous_period; check that chain end to end."""
    with patch("services.metrics.now_santiago", return_value=datetime(2026, 7, 15, 12)):
        _start_dt, _end_dt, start, end = date_bounds(period)
    assert previous_period(period, start, end) == expected


# ------------------------------------------------------------- comparisons

def test_compare_value_normal_cases_use_integers_and_one_decimal():
    assert compare_value(150, 100) == {"current": 150, "previous": 100, "delta": 50, "delta_pct": 50.0, "state": "up"}
    assert compare_value(75, 100) == {"current": 75, "previous": 100, "delta": -25, "delta_pct": -25.0, "state": "down"}
    assert compare_value(100, 100) == {"current": 100, "previous": 100, "delta": 0, "delta_pct": 0.0, "state": "flat"}
    assert compare_value(4, 3)["delta_pct"] == 33.3
    assert compare_value(5, 3)["delta_pct"] == 66.7
    assert all(isinstance(compare_value(a, b)[k], int) for a, b in [(7, 3)] for k in ("current", "previous", "delta"))


def test_compare_value_rounds_half_up_deterministically():
    assert compare_value(17, 16)["delta_pct"] == 6.3     # 6.25 -> 6.3 (float round() would give 6.2)
    assert compare_value(15, 16)["delta_pct"] == -6.3    # symmetric for decreases
    assert compare_value(1001, 1000)["delta_pct"] == 0.1


@pytest.mark.parametrize("current", [0, 1, 5000, -300])
def test_previous_zero_never_divides_or_fabricates_a_percentage(current):
    result = compare_value(current, 0)
    assert result["state"] == "no_base" and result["delta_pct"] is None
    assert result["delta"] == current and isinstance(result["delta"], int)


def test_negative_previous_base_keeps_direction_consistent():
    improved = compare_value(-50, -100)
    assert (improved["delta"], improved["delta_pct"], improved["state"]) == (50, 50.0, "up")
    worsened = compare_value(-150, -100)
    assert (worsened["delta"], worsened["delta_pct"], worsened["state"]) == (-50, -50.0, "down")
    assert compare_value(40, -100)["state"] == "up"


def metrics_stub(sales, margin):
    return {"total_sales": sales, "operating_margin": margin}


def test_margin_is_compared_in_percentage_points():
    up = compare_margin(metrics_stub(1000, 40.0), metrics_stub(1000, 30.0))
    assert (up["delta_pp"], up["state"], up["current"], up["previous"]) == (10.0, "up", 40.0, 30.0)
    assert compare_margin(metrics_stub(1, 33.3), metrics_stub(1, 25.0))["delta_pp"] == 8.3  # no float noise
    down = compare_margin(metrics_stub(1, 12.5), metrics_stub(1, 20.0))
    assert (down["delta_pp"], down["state"]) == (-7.5, "down")
    assert compare_margin(metrics_stub(1, 20.0), metrics_stub(1, 20.0))["state"] == "flat"
    assert "delta_pct" not in up  # points, never a ratio of ratios


def test_margin_without_sales_in_either_period_has_no_base():
    for current, previous in [(metrics_stub(1000, 40.0), metrics_stub(0, 0)), (metrics_stub(0, 0), metrics_stub(1000, 40.0)),
                              (metrics_stub(0, 0), metrics_stub(0, 0))]:
        result = compare_margin(current, previous)
        assert result["state"] == "no_base" and result["delta_pp"] is None


def seed_two_months(tenant):
    # June (previous): sales 100k (2), expenses 60k -> profit 40k, margin 40.0
    sale(tenant, datetime(2026, 6, 10, 12), 60000); sale(tenant, datetime(2026, 6, 20, 12), 40000, payment="debit")
    expense(tenant, datetime(2026, 6, 11, 12), 60000)
    # July (current): sales 300k (3), expenses 150k -> profit 150k, margin 50.0, ticket 100k
    for day, amount in [(3, 100000), (4, 120000), (5, 80000)]:
        sale(tenant, datetime(2026, 7, day, 12), amount)
    expense(tenant, datetime(2026, 7, 6, 12), 150000)
    expense(tenant, datetime(2026, 7, 7, 12), 999999, kind="investment", category="Equipamiento")  # not operational
    db_session.commit()


def test_month_comparison_end_to_end(app, tenants):
    seed_two_months(tenants["A"])
    result = build_period_comparison("month", D(2026, 7, 1), D(2026, 7, 31), *tenants["A"])
    assert result["previous_period"] == {"start": D(2026, 6, 1), "end": D(2026, 6, 30)}
    assert result["has_previous_data"] is True
    m = result["metrics"]
    assert set(m) == {"total_sales", "operational_expenses", "operating_profit", "average_ticket", "sales_count", "operating_margin"}
    assert (m["total_sales"]["current"], m["total_sales"]["previous"], m["total_sales"]["delta_pct"]) == (300000, 100000, 200.0)
    assert (m["operational_expenses"]["current"], m["operational_expenses"]["previous"]) == (150000, 60000)
    assert (m["operating_profit"]["current"], m["operating_profit"]["previous"], m["operating_profit"]["delta"]) == (150000, 40000, 110000)
    assert m["operating_profit"]["delta_pct"] == 275.0
    assert (m["average_ticket"]["current"], m["average_ticket"]["previous"]) == (100000, 50000)
    assert (m["sales_count"]["current"], m["sales_count"]["previous"], m["sales_count"]["delta"]) == (3, 2, 1)
    assert m["operating_margin"] == {"current": 50.0, "previous": 40.0, "delta_pp": 10.0, "state": "up"}


def test_today_week_and_custom_comparisons_use_their_own_previous_windows(app, tenants):
    tenant = tenants["A"]
    sale(tenant, datetime(2026, 7, 15, 12), 1000); sale(tenant, datetime(2026, 7, 14, 12), 500)      # today / yesterday
    sale(tenant, datetime(2026, 7, 8, 12), 700)                                                       # previous week
    sale(tenant, datetime(2026, 7, 12, 12), 300)                                                      # previous custom block
    db_session.commit()
    today = build_period_comparison("today", D(2026, 7, 15), D(2026, 7, 15), *tenant)
    assert (today["metrics"]["total_sales"]["current"], today["metrics"]["total_sales"]["previous"]) == (1000, 500)
    week = build_period_comparison("week", D(2026, 7, 13), D(2026, 7, 19), *tenant)
    assert (week["metrics"]["total_sales"]["current"], week["metrics"]["total_sales"]["previous"]) == (1500, 1000)
    assert week["previous_period"] == {"start": D(2026, 7, 6), "end": D(2026, 7, 12)}
    custom = build_period_comparison("custom", D(2026, 7, 13), D(2026, 7, 15), *tenant)  # 3 days -> 10..12
    assert custom["previous_period"] == {"start": D(2026, 7, 10), "end": D(2026, 7, 12)}
    assert (custom["metrics"]["total_sales"]["current"], custom["metrics"]["total_sales"]["previous"]) == (1500, 300)


def test_empty_previous_period_yields_no_base_everywhere(app, tenants):
    sale(tenants["A"], datetime(2026, 7, 3, 12), 100000); expense(tenants["A"], datetime(2026, 7, 4, 12), 30000)
    db_session.commit()
    result = build_period_comparison("month", D(2026, 7, 1), D(2026, 7, 31), *tenants["A"])
    assert result["has_previous_data"] is False
    for key, comparison in result["metrics"].items():
        assert comparison["state"] == "no_base", key
        assert comparison.get("delta_pct") is None and comparison.get("delta_pp") is None
    assert result["metrics"]["total_sales"]["delta"] == 100000  # absolute delta is still real


def test_empty_current_and_previous_is_all_no_base_without_errors(app, tenants):
    result = build_period_comparison("month", D(2026, 7, 1), D(2026, 7, 31), *tenants["A"])
    assert result["has_previous_data"] is False
    assert all(c["state"] == "no_base" for c in result["metrics"].values())


def test_previous_with_expenses_but_no_sales_has_no_sales_base(app, tenants):
    expense(tenants["A"], datetime(2026, 6, 4, 12), 30000); sale(tenants["A"], datetime(2026, 7, 3, 12), 90000)
    db_session.commit()
    result = build_period_comparison("month", D(2026, 7, 1), D(2026, 7, 31), *tenants["A"])
    m = result["metrics"]
    assert result["has_previous_data"] is True
    assert m["total_sales"]["state"] == "no_base" and m["operating_margin"]["state"] == "no_base"
    assert m["operating_profit"]["previous"] == -30000 and m["operating_profit"]["state"] == "up"
    assert m["operating_profit"]["delta_pct"] == 400.0


def test_inverted_custom_range_has_no_comparison_base(app, tenants):
    result = build_period_comparison("custom", D(2026, 7, 20), D(2026, 7, 10), *tenants["A"])
    assert result["previous_period"] is None and result["has_previous_data"] is False


def test_comparison_is_tenant_and_branch_scoped(app, tenants):
    seed_two_months(tenants["A"])
    baseline = build_period_comparison("month", D(2026, 7, 1), D(2026, 7, 31), *tenants["A"])
    # Heavy activity in other org and in another branch of the same org, same windows
    for other in (tenants["B"], tenants["A2"]):
        for month in (6, 7):
            sale(other, datetime(2026, month, 9, 12), 7_000_000); expense(other, datetime(2026, month, 9, 13), 5_000_000)
    db_session.commit()
    assert build_period_comparison("month", D(2026, 7, 1), D(2026, 7, 31), *tenants["A"]) == baseline
    other = build_period_comparison("month", D(2026, 7, 1), D(2026, 7, 31), *tenants["B"])
    assert other["metrics"]["total_sales"]["current"] == 7_000_000 and other["metrics"]["total_sales"]["previous"] == 7_000_000


# --------------------------------------------------------------- breakdowns

def seed_breakdown(tenant):
    sale(tenant, datetime(2026, 7, 2, 12), 50000, "cash", "food_truck")
    sale(tenant, datetime(2026, 7, 3, 12), 30000, "debit", "food_truck")
    sale(tenant, datetime(2026, 7, 4, 12), 15000, "credit", "pickup")
    sale(tenant, datetime(2026, 7, 5, 12), 5000, "transfer", "delivery")
    sale(tenant, datetime(2026, 7, 6, 12), 0 + 5000, "other", "other")
    # excluded: archived, soft-deleted, out of period
    sale(tenant, datetime(2026, 7, 7, 12), 99999, "cash", "delivery", status="archived")
    sale(tenant, datetime(2026, 7, 8, 12), 99999, "cash", "delivery", deleted_at=datetime(2026, 7, 9))
    sale(tenant, datetime(2026, 6, 30, 12), 99999, "cash", "delivery")
    db_session.commit()


def test_sales_by_channel_amount_count_percentage_and_order(app, tenants):
    seed_breakdown(tenants["A"])
    rows = sales_by_channel(*JUL, *tenants["A"])
    assert rows == [
        {"key": "food_truck", "amount": 80000, "count": 2, "percentage": 76.2},
        {"key": "pickup", "amount": 15000, "count": 1, "percentage": 14.3},
        {"key": "delivery", "amount": 5000, "count": 1, "percentage": 4.8},
        {"key": "other", "amount": 5000, "count": 1, "percentage": 4.8},
    ]
    assert sum(r["amount"] for r in rows) == calculate_metrics(*JUL, *tenants["A"])["total_sales"] == 105000


def test_sales_by_payment_method_amount_count_percentage_and_order(app, tenants):
    seed_breakdown(tenants["A"])
    rows = sales_by_payment_method(*JUL, *tenants["A"])
    assert [(r["key"], r["amount"], r["count"], r["percentage"]) for r in rows] == [
        ("cash", 50000, 1, 47.6), ("debit", 30000, 1, 28.6), ("credit", 15000, 1, 14.3),
        ("transfer", 5000, 1, 4.8), ("other", 5000, 1, 4.8),
    ]


def test_breakdown_ties_follow_canonical_order_and_only_model_keys_appear(app, tenants):
    tenant = tenants["A"]
    for channel in reversed(SALE_CHANNELS):
        sale(tenant, datetime(2026, 7, 2, 12), 1000, "cash", channel)
    for method in reversed(PAYMENT_METHODS):
        sale(tenant, datetime(2026, 7, 3, 12), 1000, method, "food_truck")
    db_session.commit()
    assert [r["key"] for r in sales_by_channel(*JUL, *tenant)][:4] == ["food_truck", "pickup", "delivery", "other"]
    assert {r["key"] for r in sales_by_channel(*JUL, *tenant)} <= set(SALE_CHANNELS) == {"food_truck", "pickup", "delivery", "other"}
    assert [r["key"] for r in sales_by_payment_method(*JUL, *tenant)][0] == "cash"
    assert {r["key"] for r in sales_by_payment_method(*JUL, *tenant)} <= {"cash", "debit", "credit", "transfer", "other"}


def test_breakdowns_are_empty_without_sales(app, tenants):
    assert sales_by_channel(*JUL, *tenants["A"]) == [] and sales_by_payment_method(*JUL, *tenants["A"]) == []


def test_breakdowns_never_leak_across_tenants_or_branches(app, tenants):
    seed_breakdown(tenants["A"])
    sale(tenants["B"], datetime(2026, 7, 2, 12), 8_000_000, "transfer", "delivery")
    sale(tenants["A2"], datetime(2026, 7, 2, 12), 4_000_000, "credit", "pickup")
    db_session.commit()
    for fn in (sales_by_channel, sales_by_payment_method):
        assert sum(r["amount"] for r in fn(*JUL, *tenants["A"])) == 105000
    assert [(r["key"], r["amount"]) for r in sales_by_channel(*JUL, *tenants["B"])] == [("delivery", 8_000_000)]
    assert [(r["key"], r["amount"], r["percentage"]) for r in sales_by_payment_method(*JUL, *tenants["A2"])] == [("credit", 4_000_000, 100.0)]


def test_breakdown_queries_compile_for_postgresql_without_dialect_specific_sql(app, tenants):
    for column in (Sale.channel, Sale.payment_method):
        query = cockpit._sales_grouped_query(column, *JUL, *tenants["A"])
        sql = str(query.statement.compile(dialect=postgresql.dialect())).lower()
        assert "group by sales." in sql and "sum(sales.amount)" in sql and "count(sales.id)" in sql
        assert "strftime" not in sql and "date(" not in sql


# -------------------------------------------------------------------- cash

def test_legacy_cash_balance_adds_every_opening_float_and_cash_net_does_not(app, tenants):
    tenant = tenants["A"]
    for day in (2, 3, 4):
        ws = work_session(tenant, D(2026, 7, day), opening=20000, counted=20000)
        sale(tenant, datetime(2026, 7, day, 12), 10000, "cash", work_session_id=ws.id)
    expense(tenant, datetime(2026, 7, 4, 13), 4000, "cash")
    expense(tenant, datetime(2026, 7, 4, 14), 500000, "cash", kind="investment", category="Equipamiento")
    db_session.commit()
    metrics = calculate_metrics(*JUL, *tenants["A"])
    assert metrics["cash_sales"] == 30000 and metrics["cash_operational_expenses"] == 4000
    assert metrics["cash_balance"] == 3 * 20000 + 30000 - 4000          # legacy: three openings piled up
    assert cash_net_for_period(metrics) == 26000                          # period cash flow, no floats, no investments


def test_cash_position_open_session_is_that_sessions_expected_cash(app, tenants):
    tenant = tenants["A"]
    work_session(tenant, D(2026, 7, 1), counted=15000)  # an older closed one must not win
    ws = work_session(tenant, D(2026, 7, 10), status="open", opening=20000)
    sale(tenant, datetime(2026, 7, 10, 12), 30000, "cash", work_session_id=ws.id)
    sale(tenant, datetime(2026, 7, 10, 12), 99000, "debit", work_session_id=ws.id)   # card is not cash
    expense(tenant, datetime(2026, 7, 10, 13), 5000, "cash", work_session_id=ws.id)
    expense(tenant, datetime(2026, 7, 10, 14), 77000, "cash", kind="investment", category="Equipamiento", work_session_id=ws.id)
    sale(tenant, datetime(2026, 7, 10, 15), 1234, "cash")                            # no session: not part of the till state
    db_session.commit()
    position = calculate_cash_position(*tenants["A"])
    assert position == {"kind": "open_session", "session_id": ws.id, "business_date": D(2026, 7, 10),
                        "expected_cash": 20000 + 30000 - 5000, "counted_cash": None, "cash_difference": None}


def test_cash_position_falls_back_to_last_closed_session_with_counted_cash(app, tenants):
    tenant = tenants["A"]
    work_session(tenant, D(2026, 7, 1), counted=1)
    last = work_session(tenant, D(2026, 7, 9), opening=10000, counted=14000)
    sale(tenant, datetime(2026, 7, 9, 12), 5000, "cash", work_session_id=last.id)
    work_session(tenant, D(2026, 7, 11), status="archived")                        # archived / deleted ignored
    work_session(tenant, D(2026, 7, 12), deleted_at=datetime(2026, 7, 12, 20), counted=5)
    db_session.commit()
    position = calculate_cash_position(*tenants["A"])
    assert (position["kind"], position["session_id"]) == ("last_closed_session", last.id)
    assert (position["expected_cash"], position["counted_cash"], position["cash_difference"]) == (15000, 14000, -1000)


def test_cash_position_without_sessions_and_tenant_scope(app, tenants):
    assert calculate_cash_position(*tenants["A"])["kind"] == "no_session"
    ws_b = work_session(tenants["B"], D(2026, 7, 10), status="open", opening=999)
    ws_a2 = work_session(tenants["A2"], D(2026, 7, 10), status="open", opening=888)
    db_session.commit()
    assert calculate_cash_position(*tenants["A"])["kind"] == "no_session"
    assert calculate_cash_position(*tenants["B"])["session_id"] == ws_b.id
    assert calculate_cash_position(*tenants["A2"])["session_id"] == ws_a2.id


def test_cash_position_matches_the_sessions_screen_calculation(app, tenants):
    from services.work_sessions import calculate_work_session_metrics
    ws = work_session(tenants["A"], D(2026, 7, 10), status="open", opening=7000)
    sale(tenants["A"], datetime(2026, 7, 10, 12), 12345, "cash", work_session_id=ws.id)
    db_session.commit()
    assert calculate_cash_position(*tenants["A"])["expected_cash"] == calculate_work_session_metrics(ws).expected_cash == 19345


# ----------------------------------------------------------------- signals

def codes(signals):
    return [s["code"] for s in signals]


def test_no_data_means_no_signals(app, tenants):
    assert attention_signals(D(2026, 7, 1), D(2026, 7, 31), *tenants["A"]) == []


def test_cash_difference_signals_split_shortage_and_surplus_and_respect_the_period(app, tenants):
    tenant = tenants["A"]
    work_session(tenant, D(2026, 7, 2), opening=10000, counted=9000)       # -1000
    work_session(tenant, D(2026, 7, 3), opening=10000, counted=7500)       # -2500
    work_session(tenant, D(2026, 7, 4), opening=10000, counted=10300)      # +300
    work_session(tenant, D(2026, 7, 5), opening=10000, counted=10000)      # balanced
    work_session(tenant, D(2026, 7, 6), opening=10000, status="open")      # open: no counted cash yet
    work_session(tenant, D(2026, 6, 20), opening=10000, counted=1)         # outside the period
    work_session(tenant, D(2026, 7, 7), opening=10000, counted=1, status="archived", deleted_at=datetime(2026, 7, 8))
    db_session.commit()
    with patch("services.work_sessions.now_santiago", return_value=datetime(2026, 7, 6, 16)):  # open session is 6h old
        signals = {s["code"]: s for s in attention_signals(D(2026, 7, 1), D(2026, 7, 31), *tenant)}
    assert (signals["cash_shortage"]["count"], signals["cash_shortage"]["amount"], signals["cash_shortage"]["severity"]) == (2, 3500, "warning")
    assert (signals["cash_surplus"]["count"], signals["cash_surplus"]["amount"], signals["cash_surplus"]["severity"]) == (1, 300, "info")
    assert set(signals) == {"cash_shortage", "cash_surplus"}


def test_an_open_session_older_than_24h_is_anomalous_by_the_existing_rule(app, tenants):
    work_session(tenants["A"], D(2026, 7, 6), status="open")
    db_session.commit()
    with patch("services.work_sessions.now_santiago", return_value=datetime(2026, 7, 7, 10, 0, 1)):  # 24h + 1s after opening
        assert codes(attention_signals(D(2026, 7, 1), D(2026, 7, 31), *tenants["A"])) == ["session_duration_anomalous"]
    with patch("services.work_sessions.now_santiago", return_value=datetime(2026, 7, 7, 10, 0, 0)):  # exactly 24h
        assert attention_signals(D(2026, 7, 1), D(2026, 7, 31), *tenants["A"]) == []


def test_anomalous_duration_uses_the_existing_24h_rule_exactly(app, tenants):
    tenant = tenants["A"]
    work_session(tenant, D(2026, 7, 2), opened_h=0, closed_h=24, counted=20000)           # exactly 24h: not anomalous
    ws = work_session(tenant, D(2026, 7, 3), counted=20000)
    ws.closed_at = ws.opened_at + timedelta(hours=24, seconds=1)                           # 24h + 1s: anomalous
    db_session.commit()
    signals = attention_signals(D(2026, 7, 1), D(2026, 7, 31), *tenant)
    assert codes(signals) == ["session_duration_anomalous"] and signals[0]["count"] == 1


def test_unassociated_movements_count_sales_and_operational_expenses_only(app, tenants):
    tenant = tenants["A"]
    ws = work_session(tenant, D(2026, 7, 2), counted=21000)  # 20000 opening + 1000 associated cash sale: balanced
    sale(tenant, datetime(2026, 7, 2, 12), 1000)
    sale(tenant, datetime(2026, 7, 2, 13), 1000)
    expense(tenant, datetime(2026, 7, 2, 14), 500)
    sale(tenant, datetime(2026, 7, 2, 15), 1000, work_session_id=ws.id)                    # associated
    expense(tenant, datetime(2026, 7, 2, 16), 9000, kind="investment", category="Equipamiento")  # investments never belong to a session
    sale(tenant, datetime(2026, 7, 2, 17), 1000, status="archived")
    sale(tenant, datetime(2026, 7, 2, 18), 1000, deleted_at=datetime(2026, 7, 3))
    db_session.commit()
    signals = attention_signals(D(2026, 7, 1), D(2026, 7, 31), *tenant)
    assert codes(signals) == ["unassociated_movements"] and signals[0]["count"] == 3
    # backlog semantics: same figure as the Jornadas banner, independent of the selected period
    assert attention_signals(D(2025, 1, 1), D(2025, 1, 31), *tenant)[0]["count"] == 3


def test_signals_have_a_stable_contract_and_point_to_existing_screens(app, tenants):
    tenant = tenants["A"]
    work_session(tenant, D(2026, 7, 2), counted=1)
    ws = work_session(tenant, D(2026, 7, 3), counted=20000); ws.closed_at = ws.opened_at + timedelta(hours=30)
    work_session(tenant, D(2026, 7, 4), counted=99999)
    sale(tenant, datetime(2026, 7, 2, 12), 1000)
    db_session.commit()
    signals = attention_signals(D(2026, 7, 1), D(2026, 7, 31), *tenant)
    assert codes(signals) == sorted(codes(signals), key=lambda c: (["warning", "info"].index(next(s["severity"] for s in signals if s["code"] == c)), c))
    assert set(codes(signals)) == {"cash_shortage", "cash_surplus", "session_duration_anomalous", "unassociated_movements"}
    endpoints = {rule.endpoint for rule in app.url_map.iter_rules()}
    for signal in signals:
        assert set(signal) == {"code", "severity", "title", "count", "amount", "destination"}
        assert signal["severity"] in ("warning", "info") and signal["title"] and isinstance(signal["count"], int) and signal["count"] > 0
        assert signal["destination"]["endpoint"] in endpoints and isinstance(signal["destination"]["params"], dict)
        assert signal["amount"] is None or isinstance(signal["amount"], int)


def test_signals_are_tenant_and_branch_scoped(app, tenants):
    work_session(tenants["A"], D(2026, 7, 2), counted=1)
    for other in (tenants["B"], tenants["A2"]):
        work_session(other, D(2026, 7, 2), counted=1); work_session(other, D(2026, 7, 3), counted=2)
        sale(other, datetime(2026, 7, 2, 12), 1000); expense(other, datetime(2026, 7, 2, 13), 100)
    db_session.commit()
    signals = {s["code"]: s for s in attention_signals(D(2026, 7, 1), D(2026, 7, 31), *tenants["A"])}
    assert signals["cash_shortage"]["count"] == 1 and "unassociated_movements" not in signals
    other = {s["code"]: s for s in attention_signals(D(2026, 7, 1), D(2026, 7, 31), *tenants["B"])}
    assert other["cash_shortage"]["count"] == 2 and other["unassociated_movements"]["count"] == 2


# ---------------------------------------------------- dashboard wiring (data only)

def test_dashboard_exposes_the_f30_data_scoped_to_the_active_tenant(app, tenants):
    seed_breakdown(tenants["A"])
    sale(tenants["B"], datetime(2026, 7, 2, 12), 5_000_000, "transfer", "delivery")
    work_session(tenants["A"], D(2026, 7, 2), status="open", opening=1000)
    db_session.add(Membership(organization_id=tenants["A"][0], clerk_user_id="user_cockpit", role="owner"))
    db_session.commit()
    captured = []
    template_rendered.connect(lambda sender, template, context, **_: captured.append((template.name, context)), app, weak=False)

    @app.before_request
    def install_tenant():
        g.user_id = "user_cockpit"
        resolve_request_tenant(g.user_id)
        g.tenant_enforced = True

    client = app.test_client()
    with client.session_transaction() as session:  # org A has two branches: choose A1 explicitly
        session["active_organization_id"], session["active_branch_id"] = tenants["A"]
    with patch("services.metrics.now_santiago", return_value=datetime(2026, 7, 15, 12)):
        response = client.get("/?period=month")
    assert response.status_code == 200
    context = next(ctx for name, ctx in captured if name == "dashboard.html")
    assert sum(r["amount"] for r in context["sales_by_channel"]) == 105000
    assert sum(r["amount"] for r in context["sales_by_payment_method"]) == 105000
    assert context["comparison"]["previous_period"] == {"start": D(2026, 6, 1), "end": D(2026, 6, 30)}
    assert context["cash_position"]["kind"] == "open_session" and context["cash_position"]["expected_cash"] == 1000
    assert context["cash_net_period"] == 50000
    assert isinstance(context["attention_signals"], list)

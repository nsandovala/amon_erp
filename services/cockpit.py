"""Deterministic Business Cockpit intelligence (F3.0).

Pure reads over existing data: no persistence, no AI, no new financial rules and
no thresholds beyond the ones already in the domain. Everything is tenant-scoped
through the same Organization + Branch filters as ``services.metrics``.

Money is always integer CLP. Percentages are computed with ``Decimal`` and
ROUND_HALF_UP to one decimal so results are reproducible across SQLite and
PostgreSQL. A comparison never fabricates a percentage: when there is no
comparable base the state is ``no_base`` and the percentage is ``None``.
"""
from datetime import datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func

from models import db_session
from models.sale import PAYMENT_METHODS, SALE_CHANNELS, Sale
from models.work_session import WorkSession
from services.metrics import _active_sales_between, _tenant_filter, calculate_metrics
from services.work_sessions import (
    calculate_work_session_metrics,
    count_unassociated_active_movements,
)

PERIOD_KINDS = ("today", "week", "month", "prev_month", "custom")

# Money/count metrics compared as absolute delta + percentage change.
COMPARED_METRICS = ("total_sales", "operational_expenses", "operating_profit", "average_ticket", "sales_count")


# ---------------------------------------------------------------- periods

def _month_start(day):
    return day.replace(day=1)


def _previous_month_bounds(day):
    last_day = _month_start(day) - timedelta(days=1)
    return last_day.replace(day=1), last_day


def previous_period(period, start_date, end_date):
    """Equivalent period immediately before (start_date, end_date), or None.

    today      -> the previous day
    week       -> the previous 7-day block (Monday-Sunday before the selected one)
    month      -> the previous calendar month
    prev_month -> the calendar month before the selected month
    custom     -> the range right before it with the same number of days

    ``start_date``/``end_date`` are the already-resolved bounds of the selected
    period (see ``services.metrics.date_bounds``); unknown periods behave as
    ``today``, exactly like ``date_bounds``. Returns None for an inverted range.
    """
    if end_date < start_date:
        return None
    kind = period if period in PERIOD_KINDS else "today"
    if kind in ("month", "prev_month"):
        return _previous_month_bounds(start_date)
    if kind == "week":
        return start_date - timedelta(days=7), end_date - timedelta(days=7)
    days = (end_date - start_date).days + 1  # today and custom: same length, adjacent
    previous_end = start_date - timedelta(days=1)
    return previous_end - timedelta(days=days - 1), previous_end


def _bounds(start_date, end_date):
    return datetime.combine(start_date, time.min), datetime.combine(end_date, time.max.replace(microsecond=0))


# ------------------------------------------------------------ comparisons

def _pct(numerator, denominator):
    """numerator/denominator as a percentage, one decimal, half-up; None if no base."""
    if not denominator:
        return None
    value = Decimal(numerator) * 100 / Decimal(abs(denominator))
    return float(value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def _direction(delta):
    return "up" if delta > 0 else "down" if delta < 0 else "flat"


def compare_value(current, previous):
    """Integer metric vs. its previous value.

    A previous value of 0 is not a comparable base: ``state="no_base"`` and
    ``delta_pct=None`` (never infinity, never a made-up percentage). The percentage is
    relative to ``abs(previous)`` so the sign always matches the direction of change
    (e.g. a loss of -100 shrinking to -50 is +50%).
    """
    current, previous = int(current), int(previous)
    delta = current - previous
    if previous == 0:
        return {"current": current, "previous": previous, "delta": delta, "delta_pct": None, "state": "no_base"}
    return {"current": current, "previous": previous, "delta": delta, "delta_pct": _pct(delta, previous), "state": _direction(delta)}


def compare_margin(current_metrics, previous_metrics):
    """Operating margin compared in percentage points (not as a ratio of ratios).

    Margin is only defined for a period with sales: if either period has none,
    there is no comparable base (``calculate_metrics`` reports 0 in that case, which
    must not be read as a real 0% margin).
    """
    current, previous = Decimal(str(current_metrics["operating_margin"])), Decimal(str(previous_metrics["operating_margin"]))
    if not current_metrics["total_sales"] or not previous_metrics["total_sales"]:
        return {"current": float(current), "previous": float(previous), "delta_pp": None, "state": "no_base"}
    delta = (current - previous).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return {"current": float(current), "previous": float(previous), "delta_pp": float(delta), "state": _direction(delta)}


def compare_periods(current_metrics, previous_metrics):
    comparison = {key: compare_value(current_metrics[key], previous_metrics[key]) for key in COMPARED_METRICS}
    comparison["operating_margin"] = compare_margin(current_metrics, previous_metrics)
    return comparison


def build_period_comparison(period, start_date, end_date, organization_id=None, branch_id=None):
    """Selected period vs. its equivalent previous period (tenant-scoped).

    Returns ``{"period", "previous_period", "has_previous_data", "metrics"}`` where
    ``metrics`` maps total_sales, operational_expenses, operating_profit,
    average_ticket, sales_count and operating_margin to their comparison.
    """
    previous = previous_period(period, start_date, end_date)
    current_metrics = calculate_metrics(*_bounds(start_date, end_date), organization_id, branch_id)
    if previous is None:
        empty = {key: 0 for key in COMPARED_METRICS} | {"operating_margin": 0}
        previous_metrics, has_data = empty, False
    else:
        previous_metrics = calculate_metrics(*_bounds(*previous), organization_id, branch_id)
        has_data = bool(previous_metrics["sales_count"] or previous_metrics["operational_expenses"])
    return {
        "period": {"start": start_date, "end": end_date},
        "previous_period": {"start": previous[0], "end": previous[1]} if previous else None,
        "has_previous_data": has_data,
        "metrics": compare_periods(current_metrics, previous_metrics),
    }


# -------------------------------------------------------- sales breakdowns

def _sales_grouped_query(column, start_dt, end_dt, organization_id=None, branch_id=None):
    """SUM/COUNT of active sales grouped by one Sale column (portable SQL: no dialect functions)."""
    return (
        _active_sales_between(start_dt, end_dt, organization_id, branch_id)
        .with_entities(column, func.sum(Sale.amount), func.count(Sale.id))
        .group_by(column)
    )


def _breakdown(column, canonical, start_dt, end_dt, organization_id, branch_id):
    rows = {key: (int(amount or 0), int(count or 0)) for key, amount, count in
            _sales_grouped_query(column, start_dt, end_dt, organization_id, branch_id).all()}
    total = sum(amount for amount, _count in rows.values())
    order = {key: index for index, key in enumerate(canonical)}
    ordered = sorted(rows, key=lambda key: (-rows[key][0], order.get(key, len(order)), str(key)))
    return [
        {"key": key, "amount": rows[key][0], "count": rows[key][1], "percentage": _pct(rows[key][0], total)}
        for key in ordered
    ]


def sales_by_channel(start_dt, end_dt, organization_id=None, branch_id=None):
    """Active sales of the period by ``Sale.channel`` (food_truck/pickup/delivery/other only).

    One row per channel that has sales, largest first: ``key``, ``amount`` (CLP),
    ``count`` and ``percentage`` of the period's sales amount (1 decimal).
    """
    return _breakdown(Sale.channel, SALE_CHANNELS, start_dt, end_dt, organization_id, branch_id)


def sales_by_payment_method(start_dt, end_dt, organization_id=None, branch_id=None):
    """Active sales of the period by payment method (cash/debit/credit/transfer/other)."""
    return _breakdown(Sale.payment_method, PAYMENT_METHODS, start_dt, end_dt, organization_id, branch_id)


# ------------------------------------------------------------------- cash

def cash_net_for_period(metrics):
    """Net cash movement of the period: cash sales minus cash operational expenses.

    Opening floats are deliberately excluded (see ``calculate_cash_position``).
    """
    return metrics["cash_sales"] - metrics["cash_operational_expenses"]


def calculate_cash_position(organization_id=None, branch_id=None):
    """Expected cash *state* of the till, independent of the selected period.

    - open session: its expected cash (opening + cash sales - cash operational expenses),
    - otherwise the most recent closed session, with the counted cash and the difference,
    - otherwise no position.

    It reuses ``calculate_work_session_metrics`` unchanged, so it can never disagree
    with the Jornadas screen.
    """
    sessions = _tenant_filter(db_session.query(WorkSession), WorkSession, organization_id, branch_id).filter(
        WorkSession.deleted_at.is_(None)
    )
    work_session = sessions.filter(WorkSession.status == "open").order_by(WorkSession.opened_at.desc()).first()
    kind = "open_session"
    if work_session is None:
        kind = "last_closed_session"
        work_session = sessions.filter(WorkSession.status == "closed").order_by(
            WorkSession.closed_at.desc(), WorkSession.id.desc()
        ).first()
    if work_session is None:
        return {"kind": "no_session", "session_id": None, "business_date": None, "expected_cash": None,
                "counted_cash": None, "cash_difference": None}
    metrics = calculate_work_session_metrics(work_session)
    is_open = kind == "open_session"
    return {
        "kind": kind,
        "session_id": work_session.id,
        "business_date": work_session.business_date,
        "expected_cash": metrics.expected_cash,
        "counted_cash": None if is_open else metrics.counted_cash,
        "cash_difference": None if is_open else metrics.cash_difference,
    }


# ---------------------------------------------------------------- signals

SEVERITY_RANK = {"warning": 0, "info": 1}


def _signal(code, severity, title, count, destination, amount=None):
    return {"code": code, "severity": severity, "title": title, "count": count, "amount": amount, "destination": destination}


def attention_signals(start_date, end_date, organization_id=None, branch_id=None):
    """Signals that follow directly from rules the ERP already has. No scores, no new thresholds.

    - cash_shortage / cash_surplus: closed sessions of the period whose counted cash differs
      from the expected cash (the existing "Cerrada con faltante / sobrante" states).
    - session_duration_anomalous: sessions of the period longer than the existing
      ``ANOMALOUS_DURATION_SECONDS`` rule (already excluded from the return estimate).
    - unassociated_movements: active sales/operational expenses without ``work_session_id``
      (the backlog already shown on Jornadas), regardless of the period.

    Each signal has a stable ``code``, ``severity`` ("warning" | "info"), ``title``, ``count``,
    optional ``amount`` (absolute CLP) and a ``destination`` (an existing endpoint to review it).
    Only signals with ``count > 0`` are returned.
    """
    sessions = (
        _tenant_filter(db_session.query(WorkSession), WorkSession, organization_id, branch_id)
        .filter(
            WorkSession.status.in_(["open", "closed"]),
            WorkSession.deleted_at.is_(None),
            WorkSession.business_date >= start_date,
            WorkSession.business_date <= end_date,
        )
        .all()
    )
    shortages, surpluses, anomalous = [], [], 0
    for work_session in sessions:
        metrics = calculate_work_session_metrics(work_session)
        if metrics.is_anomalous_duration:
            anomalous += 1
        if work_session.status == "closed" and metrics.cash_difference:
            (surpluses if metrics.cash_difference > 0 else shortages).append(abs(metrics.cash_difference))

    review = {"endpoint": "sessions.index", "params": {}}
    signals = []
    if shortages:
        signals.append(_signal("cash_shortage", "warning", "Jornadas cerradas con faltante de caja", len(shortages), review, sum(shortages)))
    if surpluses:
        signals.append(_signal("cash_surplus", "info", "Jornadas cerradas con sobrante de caja", len(surpluses), review, sum(surpluses)))
    if anomalous:
        signals.append(_signal("session_duration_anomalous", "warning", "Jornadas con duración anómala", anomalous, review))
    unassociated = count_unassociated_active_movements(organization_id, branch_id)
    if unassociated:
        signals.append(_signal("unassociated_movements", "warning", "Movimientos activos sin jornada", unassociated, review))
    return sorted(signals, key=lambda item: (SEVERITY_RANK[item["severity"]], item["code"]))

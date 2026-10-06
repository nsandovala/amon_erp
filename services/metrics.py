from collections import defaultdict
from datetime import date, datetime, time, timedelta
from math import ceil

from sqlalchemy import func

from models import db_session, now_santiago
from models.expense import Expense
from models.sale import Sale
from models.work_session import WorkSession
from services.work_sessions import ANOMALOUS_DURATION_SECONDS, calculate_work_session_metrics


MIN_VALID_SESSIONS_FOR_ESTIMATE = 3


ENERGY_CATEGORIES = {"Gas", "Luz", "Agua", "Combustible"}
SUPPLY_CATEGORIES = {"Insumos", "Proveedores"}


def date_bounds(period="today", start=None, end=None):
    today = now_santiago().date()
    if period == "week":
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
    elif period == "month":
        start_date = today.replace(day=1)
        next_month = (start_date.replace(day=28) + timedelta(days=4)).replace(day=1)
        end_date = next_month - timedelta(days=1)
    elif period == "prev_month":
        first_this_month = today.replace(day=1)
        end_date = first_this_month - timedelta(days=1)
        start_date = end_date.replace(day=1)
    elif period == "custom" and start and end:
        start_date = start
        end_date = end
    else:
        start_date = today
        end_date = today

    return (
        datetime.combine(start_date, time.min),
        datetime.combine(end_date, time.max.replace(microsecond=0)),
        start_date,
        end_date,
    )


def _tenant_filter(query, model, organization_id=None, branch_id=None):
    if organization_id is not None:
        return query.filter(model.organization_id == organization_id, model.branch_id == branch_id)
    return query


def _active_sales_between(start_dt, end_dt, organization_id=None, branch_id=None):
    return _tenant_filter(
        db_session.query(Sale)
        .filter(Sale.status == "active", Sale.deleted_at.is_(None), Sale.occurred_at >= start_dt, Sale.occurred_at <= end_dt)
        , Sale, organization_id, branch_id
    )


def _active_expenses_between(start_dt, end_dt, organization_id=None, branch_id=None):
    return _tenant_filter(
        db_session.query(Expense)
        .filter(Expense.status == "active", Expense.deleted_at.is_(None), Expense.occurred_at >= start_dt, Expense.occurred_at <= end_dt)
        , Expense, organization_id, branch_id
    )


def calculate_metrics(start_dt, end_dt, organization_id=None, branch_id=None):
    sales = _active_sales_between(start_dt, end_dt, organization_id, branch_id).all()
    expenses = _active_expenses_between(start_dt, end_dt, organization_id, branch_id).all()
    sessions = (
        _tenant_filter(db_session.query(WorkSession), WorkSession, organization_id, branch_id)
        .filter(
            WorkSession.status.in_(["open", "closed"]),
            WorkSession.deleted_at.is_(None),
            WorkSession.business_date >= start_dt.date(),
            WorkSession.business_date <= end_dt.date(),
        )
        .all()
    )

    total_sales = sum(item.amount for item in sales)
    cash_sales = sum(item.amount for item in sales if item.payment_method == "cash")
    operational_expenses = sum(item.amount for item in expenses if item.expense_type == "operational")
    investments = sum(item.amount for item in expenses if item.expense_type == "investment")
    cash_operational_expenses = sum(
        item.amount for item in expenses if item.payment_method == "cash" and item.expense_type == "operational"
    )
    sales_count = len(sales)
    operating_profit = total_sales - operational_expenses
    total_result = operating_profit - investments
    average_ticket = round(total_sales / sales_count) if sales_count else 0
    operating_margin = round((operating_profit / total_sales) * 100, 1) if total_sales else 0
    worked_seconds = sum(calculate_work_session_metrics(session).duration_seconds for session in sessions)
    worked_hours = round(worked_seconds / 3600, 1)
    opening_cash = sum(session.opening_cash for session in sessions)
    # LEGACY: sums opening_cash of *every* session in the period plus the period's cash
    # flow, so it is neither "cash now" nor a period flow. Kept unchanged for compatibility;
    # the Business Cockpit uses services.cockpit.calculate_cash_position / cash_net_for_period.
    cash_balance = opening_cash + cash_sales - cash_operational_expenses
    total_flow = total_sales - operational_expenses - investments

    return {
        "total_sales": total_sales,
        "operational_expenses": operational_expenses,
        "operating_profit": operating_profit,
        "investments": investments,
        "total_result": total_result,
        "average_ticket": average_ticket,
        "sales_count": sales_count,
        "operating_margin": operating_margin,
        "worked_hours": worked_hours,
        "worked_seconds": worked_seconds,
        "cash_sales": cash_sales,
        "cash_operational_expenses": cash_operational_expenses,
        "cash_balance": cash_balance,
        "estimated_cash": cash_balance,
        "total_flow": total_flow,
    }


def sales_expenses_by_day(start_date, end_date, organization_id=None, branch_id=None):
    values = {}
    cursor = start_date
    while cursor <= end_date:
        values[cursor.isoformat()] = {"label": cursor.strftime("%d-%m"), "sales": 0, "expenses": 0}
        cursor += timedelta(days=1)

    start_dt = datetime.combine(start_date, time.min)
    end_dt = datetime.combine(end_date, time.max.replace(microsecond=0))
    sales_rows = (
        _active_sales_between(start_dt, end_dt, organization_id, branch_id)
        .with_entities(func.date(Sale.occurred_at), func.sum(Sale.amount))
        .group_by(func.date(Sale.occurred_at))
        .all()
    )
    expense_rows = (
        _active_expenses_between(start_dt, end_dt, organization_id, branch_id)
        .filter(Expense.expense_type == "operational")
        .with_entities(func.date(Expense.occurred_at), func.sum(Expense.amount))
        .group_by(func.date(Expense.occurred_at))
        .all()
    )

    for day, amount in sales_rows:
        values[str(day)]["sales"] = int(amount or 0)
    for day, amount in expense_rows:
        values[str(day)]["expenses"] = int(amount or 0)

    return list(values.values())


def expenses_by_category(start_dt, end_dt, organization_id=None, branch_id=None):
    rows = (
        _active_expenses_between(start_dt, end_dt, organization_id, branch_id)
        .filter(Expense.expense_type == "operational")
        .with_entities(Expense.category, func.sum(Expense.amount))
        .group_by(Expense.category)
        .order_by(func.sum(Expense.amount).desc())
        .all()
    )
    return [{"category": category, "amount": int(amount or 0)} for category, amount in rows]


def investments_by_category(start_dt, end_dt, organization_id=None, branch_id=None):
    rows = (
        _active_expenses_between(start_dt, end_dt, organization_id, branch_id)
        .filter(Expense.expense_type == "investment")
        .with_entities(Expense.category, func.sum(Expense.amount))
        .group_by(Expense.category)
        .order_by(func.sum(Expense.amount).desc())
        .all()
    )
    return [{"category": category, "amount": int(amount or 0)} for category, amount in rows]


def latest_movements(limit=10, organization_id=None, branch_id=None):
    sales = _tenant_filter(db_session.query(Sale), Sale, organization_id, branch_id).filter(Sale.status == "active", Sale.deleted_at.is_(None)).all()
    expenses = _tenant_filter(db_session.query(Expense), Expense, organization_id, branch_id).filter(Expense.status == "active", Expense.deleted_at.is_(None)).all()
    movements = []
    for sale in sales:
        movements.append({
            "kind": "Venta",
            "occurred_at": sale.occurred_at,
            "description": sale.description or "Venta",
            "category": sale.channel,
            "payment_method": sale.payment_method,
            "amount": sale.amount,
            "tone": "positive",
        })
    for expense in expenses:
        movements.append({
            "kind": "Gasto" if expense.expense_type == "operational" else "Inversión",
            "occurred_at": expense.occurred_at,
            "description": expense.description,
            "category": expense.category,
            "payment_method": expense.payment_method,
            "amount": -expense.amount,
            "tone": "negative" if expense.expense_type == "operational" else "investment",
        })
    return sorted(movements, key=lambda item: item["occurred_at"], reverse=True)[:limit]


def calculate_return_estimate(organization_id=None, branch_id=None):
    sales_total = _tenant_filter(db_session.query(func.coalesce(func.sum(Sale.amount), 0)), Sale, organization_id, branch_id).filter(
        Sale.status == "active", Sale.deleted_at.is_(None)
    ).scalar()
    operational_total = _tenant_filter(db_session.query(func.coalesce(func.sum(Expense.amount), 0)), Expense, organization_id, branch_id).filter(
        Expense.status == "active",
        Expense.deleted_at.is_(None),
        Expense.expense_type == "operational",
    ).scalar()
    investment_total = _tenant_filter(db_session.query(func.coalesce(func.sum(Expense.amount), 0)), Expense, organization_id, branch_id).filter(
        Expense.status == "active",
        Expense.deleted_at.is_(None),
        Expense.expense_type == "investment",
    ).scalar()

    operating_profit = int(sales_total) - int(operational_total)
    investment_total = int(investment_total)
    capital_recovered = max(operating_profit, 0)
    capital_pending = max(investment_total - capital_recovered, 0)

    if investment_total > 0:
        recovery_percentage = min(round(capital_recovered * 100 / investment_total, 1), 100.0)
    else:
        recovery_percentage = 0.0

    valid_sessions = [
        session
        for session in _tenant_filter(db_session.query(WorkSession), WorkSession, organization_id, branch_id)
        .filter(WorkSession.status == "closed", WorkSession.deleted_at.is_(None))
        .all()
        if calculate_work_session_metrics(session).duration_seconds <= ANOMALOUS_DURATION_SECONDS
    ]
    valid_days_set = {session.business_date for session in valid_sessions}
    valid_days = len(valid_days_set)
    valid_sessions_count = len(valid_sessions)

    can_estimate = (
        investment_total > 0
        and operating_profit > 0
        and valid_days > 0
        and valid_sessions_count >= MIN_VALID_SESSIONS_FOR_ESTIMATE
    )

    daily_average = 0
    estimated_days_remaining = None
    if can_estimate and valid_days > 0:
        daily_average = operating_profit // valid_days
        if capital_pending == 0:
            estimated_days_remaining = 0
        elif daily_average > 0:
            estimated_days_remaining = ceil(capital_pending / daily_average)
        else:
            can_estimate = False

    return {
        "investment_total": investment_total,
        "capital_recovered": capital_recovered,
        "capital_pending": capital_pending,
        "recovery_percentage": recovery_percentage,
        "daily_average": daily_average,
        "estimated_days_remaining": estimated_days_remaining,
        "valid_sessions_count": valid_sessions_count,
        "valid_days": valid_days,
        "can_estimate": can_estimate,
    }


def monthly_summary(year=None, organization_id=None, branch_id=None):
    today = now_santiago().date()
    year = int(year or today.year)
    start_dt = datetime(year, 1, 1)
    end_dt = datetime(year, 12, 31, 23, 59, 59)
    sales = _active_sales_between(start_dt, end_dt, organization_id, branch_id).all()
    expenses = _active_expenses_between(start_dt, end_dt, organization_id, branch_id).all()
    sessions = (
        _tenant_filter(db_session.query(WorkSession), WorkSession, organization_id, branch_id)
        .filter(
            WorkSession.status.in_(["open", "closed"]),
            WorkSession.deleted_at.is_(None),
            WorkSession.business_date >= start_dt.date(),
            WorkSession.business_date <= end_dt.date(),
        )
        .all()
    )

    months = defaultdict(lambda: {
        "worked_days": set(),
        "income": 0,
        "supplies": 0,
        "energy": 0,
        "other_operational": 0,
        "investments": 0,
    })
    for sale in sales:
        months[sale.occurred_at.strftime("%Y-%m")]["income"] += sale.amount
    for expense in expenses:
        row = months[expense.occurred_at.strftime("%Y-%m")]
        if expense.expense_type == "investment":
            row["investments"] += expense.amount
        elif expense.category in SUPPLY_CATEGORIES:
            row["supplies"] += expense.amount
        elif expense.category in ENERGY_CATEGORIES:
            row["energy"] += expense.amount
        else:
            row["other_operational"] += expense.amount
    for work_session in sessions:
        months[work_session.business_date.strftime("%Y-%m")]["worked_days"].add(work_session.business_date)

    rows = []
    for month in sorted(months):
        row = months[month]
        operational = row["supplies"] + row["energy"] + row["other_operational"]
        operating_profit = row["income"] - operational
        rows.append({
            "month": month,
            "worked_days": len(row["worked_days"]),
            "income": row["income"],
            "supplies": row["supplies"],
            "energy": row["energy"],
            "other_operational": row["other_operational"],
            "investments": row["investments"],
            "operating_profit": operating_profit,
            "total_result": operating_profit - row["investments"],
        })
    return rows

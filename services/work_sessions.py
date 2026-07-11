from dataclasses import dataclass

from models import db_session, now_santiago
from models.expense import Expense
from models.sale import Sale
from services.audit import create_audit_log


@dataclass(frozen=True)
class WorkSessionMetrics:
    total_sales: int
    cash_sales: int
    operational_expenses: int
    cash_expenses: int
    operational_profit: int
    expected_cash: int
    counted_cash: int | None
    cash_difference: int | None
    duration_minutes: int
    cash_inflows: int = 0
    cash_withdrawals: int = 0


def calculate_work_session_metrics(work_session):
    sales = (
        db_session.query(Sale)
        .filter(
            Sale.work_session_id == work_session.id,
            Sale.status == "active",
            Sale.deleted_at.is_(None),
        )
        .all()
    )
    expenses = (
        db_session.query(Expense)
        .filter(
            Expense.work_session_id == work_session.id,
            Expense.status == "active",
            Expense.deleted_at.is_(None),
            Expense.expense_type == "operational",
        )
        .all()
    )

    total_sales = sum(int(sale.amount) for sale in sales)
    cash_sales = sum(int(sale.amount) for sale in sales if sale.payment_method == "cash")
    operational_expenses = sum(int(expense.amount) for expense in expenses)
    cash_expenses = sum(int(expense.amount) for expense in expenses if expense.payment_method == "cash")
    cash_inflows = 0
    cash_withdrawals = 0
    expected_cash = int(work_session.opening_cash or 0) + cash_sales + cash_inflows - cash_expenses - cash_withdrawals
    counted_cash = work_session.closing_cash_counted
    if counted_cash is None:
        counted_cash = work_session.closing_cash
    counted_cash = int(counted_cash) if counted_cash is not None else None
    cash_difference = counted_cash - expected_cash if counted_cash is not None else None
    end = work_session.closed_at or now_santiago()
    duration_minutes = max(int((end - work_session.opened_at).total_seconds() // 60), 0)

    return WorkSessionMetrics(
        total_sales=total_sales,
        cash_sales=cash_sales,
        operational_expenses=operational_expenses,
        cash_expenses=cash_expenses,
        operational_profit=total_sales - operational_expenses,
        expected_cash=expected_cash,
        counted_cash=counted_cash,
        cash_difference=cash_difference,
        duration_minutes=duration_minutes,
        cash_inflows=cash_inflows,
        cash_withdrawals=cash_withdrawals,
    )


def session_balance_status(work_session, metrics):
    if work_session.status == "archived":
        return "archived", "Archivada"
    if work_session.status == "open":
        return "open", "Abierta"
    if metrics.cash_difference is None or metrics.cash_difference == 0:
        return "balanced", "Cerrada y cuadrada"
    if metrics.cash_difference > 0:
        return "surplus", "Cerrada con sobrante"
    return "shortage", "Cerrada con faltante"


def historical_movement_preview(work_session):
    if work_session.closed_at is None:
        return {"sales": [], "expenses": [], "sales_total": 0, "expenses_total": 0}

    sales = (
        db_session.query(Sale)
        .filter(
            Sale.work_session_id.is_(None),
            Sale.occurred_at >= work_session.opened_at,
            Sale.occurred_at <= work_session.closed_at,
            Sale.status == "active",
            Sale.deleted_at.is_(None),
        )
        .order_by(Sale.occurred_at)
        .all()
    )
    expenses = (
        db_session.query(Expense)
        .filter(
            Expense.work_session_id.is_(None),
            Expense.occurred_at >= work_session.opened_at,
            Expense.occurred_at <= work_session.closed_at,
            Expense.status == "active",
            Expense.deleted_at.is_(None),
            Expense.expense_type == "operational",
        )
        .order_by(Expense.occurred_at)
        .all()
    )
    return {
        "sales": sales,
        "expenses": expenses,
        "sales_total": sum(int(item.amount) for item in sales),
        "expenses_total": sum(int(item.amount) for item in expenses),
    }


def associate_historical_movements(work_session):
    preview = historical_movement_preview(work_session)
    associated = 0
    for entity_type, movements in (("sale", preview["sales"]), ("expense", preview["expenses"])):
        for movement in movements:
            if movement.work_session_id is not None:
                continue
            movement.work_session_id = work_session.id
            db_session.add(create_audit_log(
                "associate_historical_movement",
                entity_type,
                movement.id,
                {"work_session_id": None},
                {"work_session_id": work_session.id},
            ))
            associated += 1
    return associated

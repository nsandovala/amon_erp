from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta

from models import db_session, now_santiago
from models.expense import KNOWN_EXPENSE_CATEGORIES, Expense
from models.sale import PAYMENT_METHODS, Sale


HISTORY_PERIODS = (
    "all",
    "today",
    "current_week",
    "current_month",
    "previous_month",
    "custom",
)
HISTORY_TYPES = ("all", "sale", "expense", "investment")
HISTORY_STATUSES = ("active", "archived")


@dataclass(frozen=True)
class HistoryFilters:
    search: str = ""
    movement_type: str = "all"
    period: str = "all"
    start_value: str = ""
    end_value: str = ""
    payment_method: str = ""
    status: str = "active"
    category: str = ""
    start_date: date | None = None
    end_date: date | None = None


class HistoryFilterError(ValueError):
    def __init__(self, message, filters):
        super().__init__(message)
        self.filters = filters


def _parse_iso_date(value, label, filters):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise HistoryFilterError(f"{label} debe ser una fecha válida.", filters)


def _month_bounds(day):
    first = day.replace(day=1)
    next_month = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
    return first, next_month - timedelta(days=1)


def parse_history_filters(args, today=None):
    period = (args.get("period") or "all").strip()
    movement_type = (args.get("type") or "all").strip()
    status = (args.get("status") or "active").strip()
    payment_method = (args.get("payment_method") or "").strip()
    filters = HistoryFilters(
        search=(args.get("q") or "").strip(),
        movement_type=movement_type if movement_type in HISTORY_TYPES else "all",
        period=period,
        start_value=(args.get("start") or "").strip(),
        end_value=(args.get("end") or "").strip(),
        payment_method=payment_method if payment_method in PAYMENT_METHODS else "",
        status=status if status in HISTORY_STATUSES else "active",
        category=(args.get("category") or "").strip(),
    )

    if period not in HISTORY_PERIODS:
        raise HistoryFilterError("Selecciona un periodo válido.", filters)

    current_day = today or now_santiago().date()
    start_date = None
    end_date = None
    if period == "today":
        start_date = end_date = current_day
    elif period == "current_week":
        start_date = current_day - timedelta(days=current_day.weekday())
        end_date = start_date + timedelta(days=6)
    elif period == "current_month":
        start_date, end_date = _month_bounds(current_day)
    elif period == "previous_month":
        current_month_start = current_day.replace(day=1)
        previous_month_day = current_month_start - timedelta(days=1)
        start_date, end_date = _month_bounds(previous_month_day)
    elif period == "custom":
        if not filters.start_value or not filters.end_value:
            raise HistoryFilterError("Ingresa las fechas Desde y Hasta para el periodo personalizado.", filters)
        start_date = _parse_iso_date(filters.start_value, "Desde", filters)
        end_date = _parse_iso_date(filters.end_value, "Hasta", filters)
        if start_date > end_date:
            raise HistoryFilterError("Desde no puede ser posterior a Hasta.", filters)

    return replace(filters, start_date=start_date, end_date=end_date)


def _apply_common_filters(query, model, filters):
    query = query.filter(model.deleted_at.is_(None), model.status == filters.status)
    if filters.payment_method:
        query = query.filter(model.payment_method == filters.payment_method)
    if filters.start_date:
        query = query.filter(model.occurred_at >= datetime.combine(filters.start_date, time.min))
    if filters.end_date:
        next_day = filters.end_date + timedelta(days=1)
        query = query.filter(model.occurred_at < datetime.combine(next_day, time.min))
    return query


def query_history_movements(filters, organization_id=None, branch_id=None):
    movements = []
    search = filters.search.lower()

    if filters.movement_type in ("all", "sale"):
        query = _apply_common_filters(db_session.query(Sale), Sale, filters)
        if organization_id is not None:
            query = query.filter(Sale.organization_id == organization_id, Sale.branch_id == branch_id)
        for sale in query.all():
            searchable = f"{sale.description or ''} {sale.notes or ''} {sale.channel}".lower()
            if search and search not in searchable:
                continue
            movements.append({
                "kind": "sale",
                "label": "Venta",
                "occurred_at": sale.occurred_at,
                "description": sale.description or "Venta",
                "category": sale.channel,
                "payment_method": sale.payment_method,
                "amount": sale.amount,
                "status": sale.status,
                "work_session_id": sale.work_session_id,
                "id": sale.id,
            })

    if filters.movement_type in ("all", "expense", "investment"):
        query = _apply_common_filters(db_session.query(Expense), Expense, filters)
        if organization_id is not None:
            query = query.filter(Expense.organization_id == organization_id, Expense.branch_id == branch_id)
        if filters.category in KNOWN_EXPENSE_CATEGORIES:
            query = query.filter(Expense.category == filters.category)
        if filters.movement_type == "investment":
            query = query.filter(Expense.expense_type == "investment")
        elif filters.movement_type == "expense":
            query = query.filter(Expense.expense_type == "operational")
        for expense in query.all():
            searchable = (
                f"{expense.description} {expense.notes or ''} "
                f"{expense.supplier or ''} {expense.category}"
            ).lower()
            if search and search not in searchable:
                continue
            is_investment = expense.expense_type == "investment"
            movements.append({
                "kind": "investment" if is_investment else "expense",
                "label": "Inversión" if is_investment else "Gasto operacional",
                "occurred_at": expense.occurred_at,
                "description": expense.description,
                "category": expense.category,
                "payment_method": expense.payment_method,
                "amount": -expense.amount,
                "status": expense.status,
                "work_session_id": expense.work_session_id,
                "id": expense.id,
            })

    return sorted(movements, key=lambda item: item["occurred_at"], reverse=True)


def load_history(args, today=None, organization_id=None, branch_id=None):
    filters = parse_history_filters(args, today=today)
    return filters, query_history_movements(filters, organization_id, branch_id)

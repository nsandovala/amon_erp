from flask import Blueprint, render_template

from models import db_session
from models.expense import Expense
from models.sale import Sale
from models.work_session import WorkSession
from routes import CHANNEL_LABELS, PAYMENT_LABELS, STATUS_LABELS, TYPE_LABELS
from services.work_sessions import calculate_work_session_metrics
from services.tenancy import scope_query


trash_bp = Blueprint("trash", __name__, url_prefix="/papelera")


@trash_bp.route("/")
def index():
    items = []

    for sale in scope_query(db_session.query(Sale), Sale, required=True).filter(Sale.deleted_at.is_not(None)).all():
        items.append({
            "kind": "sale",
            "label": "Venta",
            "description": sale.description or "Venta",
            "occurred_at": sale.occurred_at,
            "deleted_at": sale.deleted_at,
            "category": CHANNEL_LABELS[sale.channel],
            "payment_method": PAYMENT_LABELS[sale.payment_method],
            "amount": sale.amount,
            "restore_url": "sales.restore",
            "id": sale.id,
        })

    for expense in scope_query(db_session.query(Expense), Expense, required=True).filter(Expense.deleted_at.is_not(None)).all():
        items.append({
            "kind": "investment" if expense.expense_type == "investment" else "expense",
            "label": TYPE_LABELS[expense.expense_type],
            "description": expense.description,
            "occurred_at": expense.occurred_at,
            "deleted_at": expense.deleted_at,
            "category": expense.category,
            "payment_method": PAYMENT_LABELS[expense.payment_method],
            "amount": -expense.amount,
            "restore_url": "expenses.restore",
            "id": expense.id,
        })

    for work_session in scope_query(db_session.query(WorkSession), WorkSession, required=True).filter(WorkSession.deleted_at.is_not(None)).all():
        metrics = calculate_work_session_metrics(work_session)
        items.append({
            "kind": "session",
            "label": "Jornada",
            "description": f"Jornada {work_session.business_date.strftime('%d-%m-%Y')}",
            "occurred_at": work_session.opened_at,
            "deleted_at": work_session.deleted_at,
            "category": STATUS_LABELS[work_session.status],
            "payment_method": "-",
            "amount": metrics.operational_profit,
            "restore_url": "sessions.restore",
            "id": work_session.id,
        })

    items = sorted(items, key=lambda item: item["deleted_at"], reverse=True)
    return render_template("trash/index.html", items=items, status_labels=STATUS_LABELS)

from flask import Blueprint, render_template, request

from models import db_session
from models.expense import EXPENSE_CATEGORIES, EXPENSE_TYPES, Expense
from models.sale import PAYMENT_METHODS, Sale
from routes import CHANNEL_LABELS, PAYMENT_LABELS, STATUS_LABELS, TYPE_LABELS


history_bp = Blueprint("history", __name__, url_prefix="/historial")


@history_bp.route("/")
def index():
    search = (request.args.get("q") or "").strip().lower()
    movement_type = request.args.get("type", "all")
    status = request.args.get("status", "active")
    payment = request.args.get("payment_method")
    category = request.args.get("category")

    movements = []
    if movement_type in ("all", "sale"):
        query = db_session.query(Sale).filter(Sale.deleted_at.is_(None))
        if status in ("active", "archived"):
            query = query.filter(Sale.status == status)
        if payment in PAYMENT_METHODS:
            query = query.filter(Sale.payment_method == payment)
        for sale in query.all():
            text = f"{sale.description or ''} {sale.notes or ''} {sale.channel}".lower()
            if search and search not in text:
                continue
            movements.append({
                "kind": "sale",
                "label": "Venta",
                "occurred_at": sale.occurred_at,
                "description": sale.description or "Venta",
                "category": sale.channel,
                "category_label": CHANNEL_LABELS[sale.channel],
                "payment_method": sale.payment_method,
                "amount": sale.amount,
                "status": sale.status,
                "detail_url": "sales.detail",
                "archive_url": "sales.archive",
                "id": sale.id,
            })
    if movement_type in ("all", "expense", "investment"):
        query = db_session.query(Expense).filter(Expense.deleted_at.is_(None))
        if status in ("active", "archived"):
            query = query.filter(Expense.status == status)
        if payment in PAYMENT_METHODS:
            query = query.filter(Expense.payment_method == payment)
        if category in EXPENSE_CATEGORIES:
            query = query.filter(Expense.category == category)
        if movement_type == "investment":
            query = query.filter(Expense.expense_type == "investment")
        elif movement_type == "expense":
            query = query.filter(Expense.expense_type == "operational")
        for expense in query.all():
            text = f"{expense.description} {expense.notes or ''} {expense.supplier or ''} {expense.category}".lower()
            if search and search not in text:
                continue
            movements.append({
                "kind": "investment" if expense.expense_type == "investment" else "expense",
                "label": "Inversión" if expense.expense_type == "investment" else "Gasto",
                "occurred_at": expense.occurred_at,
                "description": expense.description,
                "category": expense.category,
                "category_label": expense.category,
                "payment_method": expense.payment_method,
                "amount": -expense.amount,
                "status": expense.status,
                "detail_url": "expenses.detail",
                "archive_url": "expenses.archive",
                "id": expense.id,
            })

    movements = sorted(movements, key=lambda item: item["occurred_at"], reverse=True)
    return render_template(
        "history.html",
        movements=movements,
        categories=EXPENSE_CATEGORIES,
        expense_types=EXPENSE_TYPES,
        payment_methods=PAYMENT_METHODS,
        payment_labels=PAYMENT_LABELS,
        status_labels=STATUS_LABELS,
        type_labels=TYPE_LABELS,
    )

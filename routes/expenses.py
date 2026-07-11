from flask import Blueprint, abort, redirect, render_template, request, url_for

from models import db_session, now_santiago
from models.expense import EXPENSE_CATEGORIES, EXPENSE_TYPES, Expense
from models.sale import PAYMENT_METHODS
from routes import (
    PAYMENT_LABELS,
    STATUS_LABELS,
    TYPE_LABELS,
    active_work_session,
    add_form_error,
    commit_or_flash,
    parse_int,
    parse_split_datetime,
)


expenses_bp = Blueprint("expenses", __name__, url_prefix="/gastos")


@expenses_bp.route("/", methods=["GET", "POST"])
def index():
    errors = []
    field_errors = {}
    form = request.form if request.method == "POST" else {}
    if request.method == "POST":
        try:
            expense = _expense_from_form(form)
            db_session.add(expense)
            if commit_or_flash("Gasto guardado correctamente."):
                return redirect(url_for("expenses.index"))
        except ValueError as exc:
            db_session.rollback()
            add_form_error(errors, field_errors, exc)

    query = db_session.query(Expense).filter(Expense.deleted_at.is_(None)).order_by(Expense.occurred_at.desc())
    category = request.args.get("category")
    expense_type = request.args.get("expense_type")
    start = request.args.get("start")
    end = request.args.get("end")
    status = request.args.get("status", "active")
    if status in ("active", "archived"):
        query = query.filter(Expense.status == status)
    if category in EXPENSE_CATEGORIES:
        query = query.filter(Expense.category == category)
    if expense_type in EXPENSE_TYPES:
        query = query.filter(Expense.expense_type == expense_type)
    if start:
        query = query.filter(Expense.occurred_at >= f"{start} 00:00:00")
    if end:
        query = query.filter(Expense.occurred_at <= f"{end} 23:59:59")

    expenses = query.all()
    total_operational = sum(expense.amount for expense in expenses if expense.status == "active" and expense.expense_type == "operational")
    total_investments = sum(expense.amount for expense in expenses if expense.status == "active" and expense.expense_type == "investment")
    return render_template(
        "expenses/index.html",
        expenses=expenses,
        total_operational=total_operational,
        total_investments=total_investments,
        form=form,
        errors=errors,
        field_errors=field_errors,
        categories=EXPENSE_CATEGORIES,
        expense_types=EXPENSE_TYPES,
        payment_methods=PAYMENT_METHODS,
        payment_labels=PAYMENT_LABELS,
        status_labels=STATUS_LABELS,
        type_labels=TYPE_LABELS,
    )


@expenses_bp.route("/<int:expense_id>")
def detail(expense_id):
    expense = db_session.get(Expense, expense_id) or abort(404)
    if expense.deleted_at is not None:
        abort(404)
    return render_template("expenses/detail.html", expense=expense, payment_labels=PAYMENT_LABELS, status_labels=STATUS_LABELS, type_labels=TYPE_LABELS)


@expenses_bp.route("/<int:expense_id>/editar", methods=["GET", "POST"])
def edit(expense_id):
    expense = db_session.get(Expense, expense_id) or abort(404)
    if expense.deleted_at is not None:
        abort(404)
    errors = []
    field_errors = {}
    if request.method == "POST":
        try:
            _apply_expense_form(expense, request.form)
            if commit_or_flash("Gasto actualizado correctamente."):
                return redirect(url_for("expenses.detail", expense_id=expense.id))
        except ValueError as exc:
            db_session.rollback()
            add_form_error(errors, field_errors, exc)
    return render_template(
        "expenses/edit.html",
        expense=expense,
        errors=errors,
        field_errors=field_errors,
        categories=EXPENSE_CATEGORIES,
        expense_types=EXPENSE_TYPES,
        payment_methods=PAYMENT_METHODS,
        payment_labels=PAYMENT_LABELS,
        type_labels=TYPE_LABELS,
    )


@expenses_bp.route("/<int:expense_id>/archivar", methods=["POST"])
def archive(expense_id):
    expense = db_session.get(Expense, expense_id) or abort(404)
    if expense.deleted_at is not None:
        abort(404)
    expense.status = "archived"
    commit_or_flash("Movimiento archivado. Sigue disponible en el historial.")
    return redirect(request.referrer or url_for("expenses.index"))


@expenses_bp.route("/<int:expense_id>/eliminar", methods=["POST"])
def delete(expense_id):
    expense = db_session.get(Expense, expense_id) or abort(404)
    if expense.deleted_at is None:
        expense.deleted_at = now_santiago()
        commit_or_flash("Movimiento enviado a la papelera.")
    return redirect(request.referrer or url_for("expenses.index"))


@expenses_bp.route("/<int:expense_id>/restaurar", methods=["POST"])
def restore(expense_id):
    expense = db_session.get(Expense, expense_id) or abort(404)
    expense.deleted_at = None
    commit_or_flash("Movimiento restaurado correctamente.")
    return redirect(request.referrer or url_for("trash.index"))


def _expense_from_form(form):
    expense = Expense()
    _apply_expense_form(expense, form)
    open_session = active_work_session()
    if open_session and expense.expense_type == "operational":
        expense.work_session_id = open_session.id
    return expense


def _apply_expense_form(expense, form):
    amount = parse_int(form.get("amount"), "El monto", 1)
    category = form.get("category")
    expense_type = form.get("expense_type", "operational")
    payment_method = form.get("payment_method", "cash")
    description = (form.get("description") or "").strip()
    if category not in EXPENSE_CATEGORIES:
        raise ValueError("Selecciona una categoría válida.")
    if expense_type not in EXPENSE_TYPES:
        raise ValueError("Selecciona un tipo válido.")
    if payment_method not in PAYMENT_METHODS:
        raise ValueError("Selecciona un medio de pago válido.")
    if not description:
        raise ValueError("La descripción es obligatoria.")
    expense.occurred_at = parse_split_datetime(form, "occurred_at", "el movimiento")
    expense.amount = amount
    expense.category = category
    expense.expense_type = expense_type
    expense.supplier = (form.get("supplier") or "").strip() or None
    expense.payment_method = payment_method
    expense.description = description
    expense.notes = (form.get("notes") or "").strip() or None
    return expense

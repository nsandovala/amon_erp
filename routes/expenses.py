from flask import Blueprint, abort, redirect, render_template, request, url_for

from models import db_session, now_santiago
from models.expense import (
    EXPENSE_CATEGORY_CATALOG,
    EXPENSE_TYPES,
    KNOWN_EXPENSE_CATEGORIES,
    Expense,
    expense_categories_for,
    is_expense_category_valid,
)
from models.sale import PAYMENT_METHODS
from routes import (
    PAYMENT_LABELS,
    STATUS_LABELS,
    TYPE_LABELS,
    active_work_session,
    add_form_error,
    apply_datetime_range,
    commit_or_flash,
    parse_int,
    parse_split_datetime,
)
from services.tenancy import apply_tenant_fields, scope_query, scoped_resource_or_404
from services.authorization import require_operational_write


expenses_bp = Blueprint("expenses", __name__, url_prefix="/gastos")


@expenses_bp.route("/", methods=["GET", "POST"])
def index():
    errors = []
    field_errors = {}
    form = request.form if request.method == "POST" else {}
    if request.method == "POST":
        require_operational_write(lambda: None)()
        try:
            expense = _expense_from_form(form)
            apply_tenant_fields(expense)
            db_session.add(expense)
            if commit_or_flash("Gasto guardado correctamente."):
                return redirect(url_for("expenses.index"))
        except ValueError as exc:
            db_session.rollback()
            add_form_error(errors, field_errors, exc)

    query = scope_query(db_session.query(Expense), Expense, required=True).filter(Expense.deleted_at.is_(None)).order_by(Expense.occurred_at.desc())
    category = request.args.get("category")
    expense_type = request.args.get("expense_type")
    start = request.args.get("start")
    end = request.args.get("end")
    status = request.args.get("status", "active")
    if status in ("active", "archived"):
        query = query.filter(Expense.status == status)
    if category in KNOWN_EXPENSE_CATEGORIES:
        query = query.filter(Expense.category == category)
    if expense_type in EXPENSE_TYPES:
        query = query.filter(Expense.expense_type == expense_type)
    query = apply_datetime_range(query, Expense.occurred_at, start, end)

    expenses = query.all()
    total_operational = sum(expense.amount for expense in expenses if expense.status == "active" and expense.expense_type == "operational")
    total_investments = sum(expense.amount for expense in expenses if expense.status == "active" and expense.expense_type == "investment")
    selected_expense_type = form.get("expense_type", "operational")
    if selected_expense_type not in EXPENSE_TYPES:
        selected_expense_type = "operational"
    return render_template(
        "expenses/index.html",
        expenses=expenses,
        total_operational=total_operational,
        total_investments=total_investments,
        form=form,
        errors=errors,
        field_errors=field_errors,
        categories=expense_categories_for(selected_expense_type),
        expense_category_catalog=EXPENSE_CATEGORY_CATALOG,
        expense_types=EXPENSE_TYPES,
        payment_methods=PAYMENT_METHODS,
        payment_labels=PAYMENT_LABELS,
        status_labels=STATUS_LABELS,
        type_labels=TYPE_LABELS,
    )


@expenses_bp.route("/<int:expense_id>")
def detail(expense_id):
    expense = scoped_resource_or_404(Expense, expense_id)
    if expense.deleted_at is not None:
        abort(404)
    return render_template("expenses/detail.html", expense=expense, payment_labels=PAYMENT_LABELS, status_labels=STATUS_LABELS, type_labels=TYPE_LABELS)


@expenses_bp.route("/<int:expense_id>/editar", methods=["GET", "POST"])
@require_operational_write
def edit(expense_id):
    expense = scoped_resource_or_404(Expense, expense_id)
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
    selected_expense_type = request.form.get("expense_type", expense.expense_type)
    if selected_expense_type not in EXPENSE_TYPES:
        selected_expense_type = expense.expense_type
    selected_category = request.form.get("category", expense.category)
    preserve_legacy_category = (
        selected_expense_type == expense.expense_type
        and selected_category == expense.category
        and not is_expense_category_valid(selected_expense_type, selected_category)
    )
    return render_template(
        "expenses/edit.html",
        expense=expense,
        errors=errors,
        field_errors=field_errors,
        categories=expense_categories_for(
            selected_expense_type,
            selected_category if preserve_legacy_category else None,
        ),
        legacy_category=selected_category if preserve_legacy_category else None,
        expense_category_catalog=EXPENSE_CATEGORY_CATALOG,
        expense_types=EXPENSE_TYPES,
        payment_methods=PAYMENT_METHODS,
        payment_labels=PAYMENT_LABELS,
        type_labels=TYPE_LABELS,
    )


@expenses_bp.route("/<int:expense_id>/archivar", methods=["POST"])
@require_operational_write
def archive(expense_id):
    expense = scoped_resource_or_404(Expense, expense_id)
    if expense.deleted_at is not None:
        abort(404)
    expense.status = "archived"
    commit_or_flash("Movimiento archivado. Sigue disponible en el historial.")
    return redirect(request.referrer or url_for("expenses.index"))


@expenses_bp.route("/<int:expense_id>/eliminar", methods=["POST"])
@require_operational_write
def delete(expense_id):
    expense = scoped_resource_or_404(Expense, expense_id)
    if expense.deleted_at is None:
        expense.deleted_at = now_santiago()
        commit_or_flash("Movimiento enviado a la papelera.")
    return redirect(request.referrer or url_for("expenses.index"))


@expenses_bp.route("/<int:expense_id>/restaurar", methods=["POST"])
@require_operational_write
def restore(expense_id):
    expense = scoped_resource_or_404(Expense, expense_id)
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
    if expense_type not in EXPENSE_TYPES:
        raise ValueError("Selecciona un tipo válido.")
    preserves_legacy_category = (
        expense.id is not None
        and category == expense.category
        and expense_type == expense.expense_type
    )
    if not is_expense_category_valid(expense_type, category) and not preserves_legacy_category:
        raise ValueError("Selecciona una categoría válida para el tipo de movimiento.")
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

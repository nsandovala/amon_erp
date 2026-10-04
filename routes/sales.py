from flask import Blueprint, abort, redirect, render_template, request, url_for

from models import db_session, now_santiago
from models.sale import PAYMENT_METHODS, SALE_CHANNELS, Sale
from routes import (
    CHANNEL_LABELS,
    PAYMENT_LABELS,
    STATUS_LABELS,
    active_work_session,
    add_form_error,
    apply_datetime_range,
    commit_or_flash,
    parse_int,
    parse_split_datetime,
)
from services.tenancy import apply_tenant_fields, scope_query, scoped_resource_or_404
from services.authorization import require_operational_write


sales_bp = Blueprint("sales", __name__, url_prefix="/ventas")


@sales_bp.route("/", methods=["GET", "POST"])
def index():
    errors = []
    field_errors = {}
    form = request.form if request.method == "POST" else {}
    if request.method == "POST":
        require_operational_write(lambda: None)()
        try:
            sale = _sale_from_form(form)
            apply_tenant_fields(sale)
            db_session.add(sale)
            if commit_or_flash("Venta guardada correctamente."):
                return redirect(url_for("sales.index"))
        except ValueError as exc:
            db_session.rollback()
            add_form_error(errors, field_errors, exc)

    query = scope_query(db_session.query(Sale), Sale, required=True).filter(Sale.deleted_at.is_(None)).order_by(Sale.occurred_at.desc())
    start = request.args.get("start")
    end = request.args.get("end")
    payment = request.args.get("payment_method")
    status = request.args.get("status", "active")
    if status in ("active", "archived"):
        query = query.filter(Sale.status == status)
    if payment in PAYMENT_METHODS:
        query = query.filter(Sale.payment_method == payment)
    query = apply_datetime_range(query, Sale.occurred_at, start, end)

    sales = query.all()
    total = sum(sale.amount for sale in sales if sale.status == "active")
    return render_template(
        "sales/index.html",
        sales=sales,
        total=total,
        form=form,
        errors=errors,
        field_errors=field_errors,
        payment_methods=PAYMENT_METHODS,
        channels=SALE_CHANNELS,
        payment_labels=PAYMENT_LABELS,
        channel_labels=CHANNEL_LABELS,
        status_labels=STATUS_LABELS,
    )


@sales_bp.route("/<int:sale_id>")
def detail(sale_id):
    sale = scoped_resource_or_404(Sale, sale_id)
    if sale.deleted_at is not None:
        abort(404)
    return render_template("sales/detail.html", sale=sale, payment_labels=PAYMENT_LABELS, channel_labels=CHANNEL_LABELS, status_labels=STATUS_LABELS)


@sales_bp.route("/<int:sale_id>/editar", methods=["GET", "POST"])
@require_operational_write
def edit(sale_id):
    sale = scoped_resource_or_404(Sale, sale_id)
    if sale.deleted_at is not None:
        abort(404)
    errors = []
    field_errors = {}
    if request.method == "POST":
        try:
            _apply_sale_form(sale, request.form)
            if commit_or_flash("Venta actualizada correctamente."):
                return redirect(url_for("sales.detail", sale_id=sale.id))
        except ValueError as exc:
            db_session.rollback()
            add_form_error(errors, field_errors, exc)

    return render_template(
        "sales/edit.html",
        sale=sale,
        errors=errors,
        field_errors=field_errors,
        payment_methods=PAYMENT_METHODS,
        channels=SALE_CHANNELS,
        payment_labels=PAYMENT_LABELS,
        channel_labels=CHANNEL_LABELS,
    )


@sales_bp.route("/<int:sale_id>/archivar", methods=["POST"])
@require_operational_write
def archive(sale_id):
    sale = scoped_resource_or_404(Sale, sale_id)
    if sale.deleted_at is not None:
        abort(404)
    sale.status = "archived"
    commit_or_flash("Venta archivada. Sigue disponible en el historial.")
    return redirect(request.referrer or url_for("sales.index"))


@sales_bp.route("/<int:sale_id>/eliminar", methods=["POST"])
@require_operational_write
def delete(sale_id):
    sale = scoped_resource_or_404(Sale, sale_id)
    if sale.deleted_at is None:
        sale.deleted_at = now_santiago()
        commit_or_flash("Venta enviada a la papelera.")
    return redirect(request.referrer or url_for("sales.index"))


@sales_bp.route("/<int:sale_id>/restaurar", methods=["POST"])
@require_operational_write
def restore(sale_id):
    sale = scoped_resource_or_404(Sale, sale_id)
    sale.deleted_at = None
    commit_or_flash("Venta restaurada correctamente.")
    return redirect(request.referrer or url_for("trash.index"))


def _sale_from_form(form):
    sale = Sale()
    _apply_sale_form(sale, form)
    open_session = active_work_session()
    if open_session:
        sale.work_session_id = open_session.id
    return sale


def _apply_sale_form(sale, form):
    amount = parse_int(form.get("amount"), "El monto", 1)
    payment_method = form.get("payment_method", "cash")
    channel = form.get("channel", "food_truck")
    if payment_method not in PAYMENT_METHODS:
        raise ValueError("Selecciona un medio de pago válido.")
    if channel not in SALE_CHANNELS:
        raise ValueError("Selecciona un canal válido.")
    sale.occurred_at = parse_split_datetime(form, "occurred_at", "la venta")
    sale.amount = amount
    sale.payment_method = payment_method
    sale.channel = channel
    sale.description = (form.get("description") or "").strip() or None
    sale.notes = (form.get("notes") or "").strip() or None
    return sale

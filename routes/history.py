import csv
import io

from flask import Blueprint, Response, render_template, request, url_for

from models.sale import PAYMENT_METHODS
from routes import CHANNEL_LABELS, PAYMENT_LABELS, STATUS_LABELS, TYPE_LABELS
from services.history import HistoryFilterError, load_history


history_bp = Blueprint("history", __name__, url_prefix="/historial")


@history_bp.route("/")
def index():
    errors = []
    try:
        filters, movements = load_history(request.args)
    except HistoryFilterError as exc:
        errors.append(str(exc))
        filters = exc.filters
        movements = []
    return render_template(
        "history.html",
        errors=errors,
        filters=filters,
        movements=movements,
        payment_methods=PAYMENT_METHODS,
        payment_labels=PAYMENT_LABELS,
        status_labels=STATUS_LABELS,
        type_labels=TYPE_LABELS,
        channel_labels=CHANNEL_LABELS,
        export_url=url_for("history.export_csv", **request.args.to_dict(flat=True)),
    )


def _spreadsheet_safe(value):
    text = "" if value is None else str(value)
    return f"'{text}" if text.startswith(("=", "+", "-", "@")) else text


@history_bp.route("/exportar.csv")
def export_csv():
    try:
        filters, movements = load_history(request.args)
    except HistoryFilterError as exc:
        return Response(str(exc), status=400, content_type="text/plain; charset=utf-8")

    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter=";", lineterminator="\n")
    writer.writerow([
        "Fecha",
        "Hora",
        "Tipo",
        "Descripción",
        "Categoría / canal",
        "Medio de pago",
        "Monto CLP",
        "Estado",
        "ID de jornada",
    ])
    for movement in movements:
        category = (
            CHANNEL_LABELS.get(movement["category"], movement["category"])
            if movement["kind"] == "sale"
            else movement["category"]
        )
        writer.writerow([
            movement["occurred_at"].strftime("%Y-%m-%d"),
            movement["occurred_at"].strftime("%H:%M"),
            _spreadsheet_safe(movement["label"]),
            _spreadsheet_safe(movement["description"]),
            _spreadsheet_safe(category),
            _spreadsheet_safe(PAYMENT_LABELS[movement["payment_method"]]),
            movement["amount"],
            _spreadsheet_safe(STATUS_LABELS[movement["status"]]),
            movement["work_session_id"] or "",
        ])

    filename_start = filters.start_date.isoformat() if filters.start_date else "inicio"
    filename_end = filters.end_date.isoformat() if filters.end_date else "fin"
    response = Response("\ufeff" + output.getvalue(), content_type="text/csv; charset=utf-8")
    response.headers["Content-Disposition"] = (
        f'attachment; filename="amon-erp-historial_{filename_start}_{filename_end}.csv"'
    )
    return response

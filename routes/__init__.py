import re
from datetime import datetime

from flask import flash

from models import db_session, now_santiago
from models.work_session import WorkSession


PAYMENT_LABELS = {
    "cash": "Efectivo",
    "debit": "Débito",
    "credit": "Crédito",
    "transfer": "Transferencia",
    "other": "Otro",
}

CHANNEL_LABELS = {
    "food_truck": "Food truck",
    "pickup": "Retiro",
    "delivery": "Delivery",
    "other": "Otro",
}

TYPE_LABELS = {
    "operational": "Gasto operacional",
    "investment": "Inversión",
}

STATUS_LABELS = {
    "active": "Activo",
    "archived": "Archivado",
    "deleted": "Eliminado",
    "open": "Abierta",
    "closed": "Cerrada",
}

DATE_PATTERN = re.compile(r"^\d{2}-\d{2}-\d{4}$")
TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class FormValidationError(ValueError):
    def __init__(self, message, field_errors=None):
        super().__init__(message)
        self.field_errors = field_errors or {}


def add_form_error(errors, field_errors, exc):
    errors.append(str(exc))
    field_errors.update(getattr(exc, "field_errors", {}))


def parse_int(value, field_name, minimum=None):
    try:
        number = int(str(value or "").replace(".", "").strip())
    except ValueError:
        raise ValueError(f"{field_name} debe ser un número entero.")
    if minimum is not None and number < minimum:
        raise ValueError(f"{field_name} debe ser mayor o igual a {minimum}.")
    return number


def parse_datetime_local(value):
    if not value:
        return now_santiago()
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M")
    except ValueError:
        raise ValueError("La fecha y hora no tiene un formato válido.")


def parse_date_local(value, field_name="La fecha"):
    raw = (value or "").strip()
    if not raw:
        return now_santiago().date()
    if not DATE_PATTERN.match(raw):
        raise ValueError(f"{field_name} debe usar DD-MM-YYYY con año de cuatro dígitos.")
    try:
        return datetime.strptime(raw, "%d-%m-%Y").date()
    except ValueError:
        raise ValueError(f"{field_name} no es válida.")


def parse_time_local(value, field_name="La hora"):
    raw = (value or "").strip()
    if not raw:
        return now_santiago().time().replace(second=0, microsecond=0)
    if not TIME_PATTERN.match(raw):
        raise ValueError(f"{field_name} debe usar HH:mm en formato 24 horas.")
    try:
        return datetime.strptime(raw, "%H:%M").time()
    except ValueError:
        raise ValueError(f"{field_name} no es válida.")


def parse_split_datetime(form, prefix, label="La fecha y hora"):
    date_name = f"{prefix}_date"
    time_name = f"{prefix}_time"
    raw_date = (form.get(date_name) or "").strip()
    raw_time = (form.get(time_name) or "").strip()

    if not raw_date and not raw_time and form.get(prefix):
        return parse_datetime_local(form.get(prefix))

    field_errors = {}
    parsed_date = None
    parsed_time = None
    try:
        parsed_date = parse_date_local(raw_date, f"La fecha de {label}")
    except ValueError as exc:
        field_errors[date_name] = str(exc)
    try:
        parsed_time = parse_time_local(raw_time, f"La hora de {label}")
    except ValueError as exc:
        field_errors[time_name] = str(exc)

    if field_errors:
        raise FormValidationError("Revisa la fecha y hora ingresadas.", field_errors)

    return datetime.combine(parsed_date, parsed_time)


def parse_split_date(form, field_name, label="La fecha"):
    raw = (form.get(field_name) or "").strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        try:
            return datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            pass
    try:
        return parse_date_local(form.get(field_name), label)
    except ValueError as exc:
        raise FormValidationError(str(exc), {field_name: str(exc)})


def active_work_session():
    return db_session.query(WorkSession).filter(WorkSession.status == "open", WorkSession.deleted_at.is_(None)).first()


def commit_or_flash(success_message):
    try:
        db_session.commit()
        flash(success_message, "success")
        return True
    except Exception:
        db_session.rollback()
        flash("No se pudo guardar. Revisa los datos e intenta nuevamente.", "error")
        return False

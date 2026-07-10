from flask import Blueprint, flash, redirect, render_template, request, url_for

from models import db_session, now_santiago
from models.work_session import WorkSession
from routes import STATUS_LABELS, active_work_session, add_form_error, commit_or_flash, parse_int, parse_split_date, parse_split_datetime


sessions_bp = Blueprint("sessions", __name__, url_prefix="/jornadas")


@sessions_bp.route("/", methods=["GET", "POST"])
def index():
    errors = []
    field_errors = {}
    if request.method == "POST":
        try:
            if active_work_session():
                raise ValueError("Ya existe una jornada abierta. Ciérrala antes de abrir otra.")
            business_date = parse_split_date(request.form, "business_date", "La fecha de trabajo")
            work_session = WorkSession(
                business_date=business_date,
                opened_at=parse_split_datetime(request.form, "opened_at", "apertura"),
                opening_cash=parse_int(request.form.get("opening_cash"), "El efectivo inicial", 0),
                notes=(request.form.get("notes") or "").strip() or None,
                status="open",
            )
            db_session.add(work_session)
            if commit_or_flash("Jornada abierta correctamente."):
                return redirect(url_for("sessions.index"))
        except ValueError as exc:
            db_session.rollback()
            add_form_error(errors, field_errors, exc)

    sessions = db_session.query(WorkSession).filter(WorkSession.deleted_at.is_(None)).order_by(WorkSession.opened_at.desc()).all()
    return render_template(
        "sessions/index.html",
        sessions=sessions,
        errors=errors,
        field_errors=field_errors,
        status_labels=STATUS_LABELS,
        current_dt=now_santiago(),
    )


@sessions_bp.route("/<int:session_id>/cerrar", methods=["POST"])
def close(session_id):
    work_session = db_session.get(WorkSession, session_id)
    if not work_session or work_session.status != "open":
        flash("Solo se puede cerrar una jornada abierta.", "error")
        return redirect(url_for("sessions.index"))
    try:
        work_session.closed_at = parse_split_datetime(request.form, "closed_at", "cierre")
        if work_session.closed_at < work_session.opened_at:
            raise ValueError("La hora de cierre no puede ser anterior a la apertura.")
        work_session.closing_cash = parse_int(request.form.get("closing_cash"), "El efectivo final", 0)
        work_session.notes = (request.form.get("notes") or work_session.notes or "").strip() or None
        work_session.status = "closed"
        commit_or_flash("Jornada cerrada correctamente.")
    except ValueError as exc:
        db_session.rollback()
        errors = []
        field_errors = {}
        add_form_error(errors, field_errors, exc)
        sessions = db_session.query(WorkSession).filter(WorkSession.deleted_at.is_(None)).order_by(WorkSession.opened_at.desc()).all()
        return render_template(
            "sessions/index.html",
            sessions=sessions,
            errors=errors,
            field_errors=field_errors,
            status_labels=STATUS_LABELS,
            current_dt=now_santiago(),
        )
    return redirect(url_for("sessions.index"))


@sessions_bp.route("/<int:session_id>/archivar", methods=["POST"])
def archive(session_id):
    work_session = db_session.get(WorkSession, session_id)
    if not work_session:
        flash("No se encontró la jornada.", "error")
        return redirect(url_for("sessions.index"))
    if work_session.status == "open":
        flash("Cierra la jornada antes de archivarla.", "error")
        return redirect(url_for("sessions.index"))
    work_session.status = "archived"
    commit_or_flash("Jornada archivada.")
    return redirect(url_for("sessions.index"))


@sessions_bp.route("/<int:session_id>/eliminar", methods=["POST"])
def delete(session_id):
    work_session = db_session.get(WorkSession, session_id)
    if not work_session:
        flash("No se encontró la jornada.", "error")
        return redirect(url_for("sessions.index"))
    if work_session.status == "open":
        flash("Cierra la jornada antes de eliminarla.", "error")
        return redirect(url_for("sessions.index"))
    if work_session.deleted_at is None:
        work_session.deleted_at = now_santiago()
        commit_or_flash("Jornada enviada a la papelera.")
    return redirect(request.referrer or url_for("sessions.index"))


@sessions_bp.route("/<int:session_id>/restaurar", methods=["POST"])
def restore(session_id):
    work_session = db_session.get(WorkSession, session_id)
    if not work_session:
        flash("No se encontró la jornada.", "error")
        return redirect(url_for("trash.index"))
    work_session.deleted_at = None
    commit_or_flash("Jornada restaurada correctamente.")
    return redirect(request.referrer or url_for("trash.index"))

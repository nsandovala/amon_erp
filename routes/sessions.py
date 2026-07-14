from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from models import db_session, now_santiago
from models.work_session import WorkSession
from routes import active_work_session, add_form_error, commit_or_flash, parse_int, parse_split_datetime
from services.audit import create_audit_log
from services.work_sessions import (
    associate_historical_movements,
    calculate_work_session_metrics,
    count_unassociated_active_movements,
    historical_movement_preview,
    session_balance_status,
)


sessions_bp = Blueprint("sessions", __name__, url_prefix="/jornadas")


@sessions_bp.route("/", methods=["GET", "POST"])
def index():
    errors = []
    field_errors = {}
    form = request.form if request.method == "POST" else {}
    if request.method == "POST":
        try:
            if active_work_session():
                raise ValueError("Ya existe una jornada abierta. Ciérrala antes de abrir otra.")
            opened_at = parse_split_datetime(request.form, "opened_at", "apertura")
            work_session = WorkSession(
                business_date=opened_at.date(),
                opened_at=opened_at,
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

    return _render_index(errors, field_errors, form)


@sessions_bp.route("/<int:session_id>/cerrar", methods=["POST"])
def close(session_id):
    work_session = db_session.get(WorkSession, session_id)
    if not work_session or work_session.deleted_at is not None or work_session.status != "open":
        flash("Solo se puede cerrar una jornada abierta.", "error")
        return redirect(url_for("sessions.index"))
    try:
        closed_at = parse_split_datetime(request.form, "closed_at", "cierre")
        if closed_at <= work_session.opened_at:
            raise ValueError("La fecha y hora de cierre debe ser posterior a la apertura.")
        counted_cash = parse_int(
            request.form.get("closing_cash_counted"),
            "El efectivo contado al cierre",
            0,
        )
        work_session.closed_at = closed_at
        work_session.closing_cash_counted = counted_cash
        work_session.closing_cash = counted_cash
        work_session.closing_notes = (request.form.get("closing_notes") or "").strip() or None
        work_session.status = "closed"
        if commit_or_flash("Jornada cerrada correctamente."):
            return redirect(url_for("sessions.index"))
    except ValueError as exc:
        db_session.rollback()
        errors = []
        field_errors = {}
        add_form_error(errors, field_errors, exc)
        return _render_index(errors, field_errors, request.form)
    return redirect(url_for("sessions.index"))


@sessions_bp.route("/<int:session_id>/editar", methods=["GET", "POST"])
def edit(session_id):
    work_session = db_session.get(WorkSession, session_id) or abort(404)
    if work_session.deleted_at is not None:
        abort(404)
    errors = []
    field_errors = {}
    if request.method == "POST":
        old_values = _session_snapshot(work_session)
        try:
            opened_at = parse_split_datetime(request.form, "opened_at", "apertura")
            closing_cash_counted = work_session.closing_cash_counted
            closed_at = work_session.closed_at
            closing_notes = work_session.closing_notes
            if work_session.status != "open":
                closed_at = parse_split_datetime(request.form, "closed_at", "cierre")
                if closed_at <= opened_at:
                    raise ValueError("La fecha y hora de cierre debe ser posterior a la apertura.")
                closing_cash_counted = parse_int(
                    request.form.get("closing_cash_counted"),
                    "El efectivo contado al cierre",
                    0,
                )
                closing_notes = (request.form.get("closing_notes") or "").strip() or None

            work_session.opened_at = opened_at
            work_session.business_date = opened_at.date()
            work_session.opening_cash = parse_int(request.form.get("opening_cash"), "El efectivo inicial", 0)
            work_session.notes = (request.form.get("notes") or "").strip() or None
            work_session.closed_at = closed_at
            work_session.closing_cash_counted = closing_cash_counted
            work_session.closing_cash = closing_cash_counted
            work_session.closing_notes = closing_notes
            db_session.add(create_audit_log(
                "edit_work_session",
                "work_session",
                work_session.id,
                old_values,
                _session_snapshot(work_session),
            ))
            if commit_or_flash("Jornada actualizada correctamente."):
                return redirect(url_for("sessions.index"))
        except ValueError as exc:
            db_session.rollback()
            add_form_error(errors, field_errors, exc)

    return render_template(
        "sessions/edit.html",
        work_session=work_session,
        errors=errors,
        field_errors=field_errors,
    )


@sessions_bp.route("/<int:session_id>/asociar-movimientos", methods=["GET", "POST"])
def associate_movements(session_id):
    work_session = db_session.get(WorkSession, session_id) or abort(404)
    if work_session.deleted_at is not None or work_session.closed_at is None:
        flash("La reconstrucción histórica solo está disponible para jornadas cerradas.", "error")
        return redirect(url_for("sessions.index"))

    if request.method == "POST":
        associated = associate_historical_movements(work_session)
        if commit_or_flash(f"Se asociaron {associated} movimientos a la jornada."):
            return redirect(url_for("sessions.index"))

    return render_template(
        "sessions/associate.html",
        work_session=work_session,
        preview=historical_movement_preview(work_session),
    )


@sessions_bp.route("/<int:session_id>/archivar", methods=["POST"])
def archive(session_id):
    work_session = db_session.get(WorkSession, session_id)
    if not work_session or work_session.deleted_at is not None:
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


def _render_index(errors, field_errors, form):
    sessions = (
        db_session.query(WorkSession)
        .filter(WorkSession.deleted_at.is_(None))
        .order_by(WorkSession.opened_at.desc())
        .all()
    )
    session_rows = []
    for work_session in sessions:
        metrics = calculate_work_session_metrics(work_session)
        status_key, status_label = session_balance_status(work_session, metrics)
        session_rows.append({
            "session": work_session,
            "metrics": metrics,
            "status_key": status_key,
            "status_label": status_label,
        })
    open_session = active_work_session()
    open_metrics = calculate_work_session_metrics(open_session) if open_session else None
    unassociated_count = count_unassociated_active_movements()
    return render_template(
        "sessions/index.html",
        session_rows=session_rows,
        current_session=open_session,
        current_metrics=open_metrics,
        errors=errors,
        field_errors=field_errors,
        form=form,
        current_dt=now_santiago(),
        unassociated_count=unassociated_count,
    )


def _session_snapshot(work_session):
    return {
        "business_date": work_session.business_date,
        "opened_at": work_session.opened_at,
        "closed_at": work_session.closed_at,
        "opening_cash": work_session.opening_cash,
        "closing_cash_counted": work_session.closing_cash_counted,
        "notes": work_session.notes,
        "closing_notes": work_session.closing_notes,
        "status": work_session.status,
    }

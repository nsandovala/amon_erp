import csv
import io
import json
import secrets
from datetime import date, datetime, timedelta
from pathlib import Path

import click
from flask import Flask, Response, abort, flash, g, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy.exc import SQLAlchemyError

from config import Config
from models import (
    create_tables,
    db_session,
    drop_tables,
    ensure_soft_delete_columns,
    ensure_work_session_cash_columns,
    init_engine,
    now_santiago,
)
from models.expense import EXPENSE_CATEGORIES, Expense
from models.sale import Sale
from models.work_session import WorkSession
from models.membership import MEMBERSHIP_ROLES, Membership
from models.organization import Organization
from routes import PAYMENT_LABELS, active_work_session, commit_or_flash, parse_int
from routes.dashboard import dashboard_bp
from routes.expenses import expenses_bp
from routes.history import history_bp
from routes.sales import sales_bp
from routes.sessions import sessions_bp
from routes.trash import trash_bp
from routes.admin import admin_bp
from routes.tenant_context import tenant_context_bp
from services.backup import create_backup, local_database_path, supports_local_backup
from services.auth import init_auth
from services.database import database_is_available, record_counts, schema_errors
from services.metrics import monthly_summary


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    if app.config["APP_ENV"] in {"production", "staging"}:
        app.config.update(
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE="Lax",
        )
    init_auth(app)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    if supports_local_backup(app.config["SQLALCHEMY_DATABASE_URI"]):
        Path(app.config["BACKUP_DIR"]).mkdir(parents=True, exist_ok=True)
    database_engine = init_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    try:
        create_tables()
        ensure_soft_delete_columns(app.config["SQLALCHEMY_DATABASE_URI"], app.config["BACKUP_DIR"])
        ensure_work_session_cash_columns(app.config["SQLALCHEMY_DATABASE_URI"], app.config["BACKUP_DIR"])
    except SQLAlchemyError:
        # Keep health and diagnostics available during a database outage.
        app.logger.warning("Database schema bootstrap unavailable")

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(sessions_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(trash_bp)
    app.register_blueprint(tenant_context_bp)
    app.register_blueprint(admin_bp)

    @app.before_request
    def protect_post():
        if request.method == "POST":
            form_token = request.form.get("csrf_token")
            if not form_token or form_token != session.get("csrf_token"):
                abort(400, "La sesión expiró. Vuelve a intentar.")

    @app.teardown_appcontext
    def shutdown_session(_exception=None):
        db_session.remove()

    @app.context_processor
    def inject_helpers():
        token = session.get("csrf_token")
        if not token:
            token = secrets.token_urlsafe(32)
            session["csrf_token"] = token
        return {
            "csrf_token": token,
            "open_session": active_work_session() if getattr(g, 'erp_access', False) else None,
            "payment_labels": PAYMENT_LABELS,
            "format_clp": format_clp,
            "format_datetime": format_datetime,
            "format_date": format_date,
            "format_time": format_time,
            "form_date": form_date,
            "form_time": form_time,
            "format_duration": format_duration,
            "now_santiago": now_santiago,
            "supports_local_backup": supports_local_backup(app.config["SQLALCHEMY_DATABASE_URI"]),
            "active_organization": getattr(g, "organization", None),
            "active_branch": getattr(g, "branch", None),
        }

    @app.template_filter("clp")
    def clp_filter(value):
        return format_clp(value)

    @app.template_filter("dt")
    def dt_filter(value):
        return format_datetime(value)

    @app.template_filter("date_cl")
    def date_filter(value):
        return format_date(value)

    @app.route("/backup", methods=["POST"])
    def backup():
        database_uri = app.config["SQLALCHEMY_DATABASE_URI"]
        if not supports_local_backup(database_uri):
            flash("PostgreSQL no admite respaldo local desde esta aplicación; no se creó un archivo SQLite.", "error")
            return redirect(request.referrer or url_for("dashboard.index"))
        try:
            target = create_backup(local_database_path(database_uri), app.config["BACKUP_DIR"])
            flash(f"Respaldo creado: {target.name}", "success")
        except Exception as exc:
            flash(str(exc), "error")
        return redirect(request.referrer or url_for("dashboard.index"))

    @app.get("/health")
    def health():
        if database_is_available(database_engine):
            return jsonify(status="ok", database="ok")
        app.logger.warning("Database health check failed")
        return jsonify(status="degraded", database="error"), 503

    @app.route("/monthly-summary.csv")
    def monthly_summary_csv():
        year = request.args.get("year", type=int) or now_santiago().year
        rows = monthly_summary(year, getattr(g, "organization_id", None), getattr(g, "branch_id", None))
        output = io.StringIO()
        output.write("\ufeff")
        writer = csv.writer(output, delimiter=";")
        writer.writerow([
            "Mes",
            "Días trabajados",
            "Total ingresos",
            "Gastos de insumos",
            "Gastos de energía",
            "Otros gastos operacionales",
            "Inversiones",
            "Ganancia operativa",
            "Resultado total",
        ])
        for row in rows:
            writer.writerow([
                row["month"],
                row["worked_days"],
                row["income"],
                row["supplies"],
                row["energy"],
                row["other_operational"],
                row["investments"],
                row["operating_profit"],
                row["total_result"],
            ])
        return Response(
            output.getvalue(),
            content_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename=resumen_mensual_{year}.csv"},
        )

    @app.cli.command("init-db")
    def init_db_command():
        create_tables()
        print("Base de datos inicializada.")

    @app.cli.command("db-check")
    def db_check_command():
        errors = schema_errors(database_engine)
        if errors:
            raise click.ClickException(" ".join(errors))
        click.echo("Conexión y schema verificados.")

    @app.cli.command("db-counts")
    def db_counts_command():
        errors = schema_errors(database_engine)
        if errors:
            raise click.ClickException("No se pueden contar registros: el schema no es válido.")
        click.echo(json.dumps(record_counts(database_engine), sort_keys=True))

    @app.cli.command("tenant-grant")
    @click.option("--user-id", required=True)
    @click.option("--organization", "organization_slug", required=True)
    @click.option("--role", type=click.Choice(MEMBERSHIP_ROLES), required=True)
    def tenant_grant_command(user_id, organization_slug, role):
        """Explicitly grant a Clerk identity local ERP membership."""
        organization = db_session.query(Organization).filter(Organization.slug == organization_slug).one_or_none()
        if organization is None:
            raise click.ClickException("La organización no existe; ejecuta primero la migración o bootstrap explícito.")
        membership = db_session.query(Membership).filter(
            Membership.organization_id == organization.id,
            Membership.clerk_user_id == user_id,
        ).one_or_none()
        if membership is None:
            membership = Membership(
                organization_id=organization.id,
                clerk_user_id=user_id,
                role=role,
                status="active",
            )
            db_session.add(membership)
            db_session.commit()
            click.echo("Membresía creada.")
        else:
            click.echo("La membresía ya existe; no se modificó.")

    @app.cli.command("tenant-memberships")
    @click.option("--organization", "organization_slug", required=True)
    def tenant_memberships_command(organization_slug):
        """List local memberships without querying Clerk."""
        organization = db_session.query(Organization).filter(Organization.slug == organization_slug).one_or_none()
        if organization is None:
            raise click.ClickException("La organización no existe.")
        for membership in db_session.query(Membership).filter(Membership.organization_id == organization.id).order_by(Membership.id):
            click.echo(f"{membership.clerk_user_id}\t{membership.role}\t{membership.status}")

    @app.cli.command("reset-db")
    def reset_db_command():
        drop_tables()
        create_tables()
        print("Base de datos reiniciada.")

    @app.cli.command("seed")
    def seed_command():
        create_tables()
        seed_demo_data()
        print("Datos de demostración cargados.")

    return app


def format_clp(value):
    amount = int(value or 0)
    sign = "-" if amount < 0 else ""
    return f"{sign}${abs(amount):,}".replace(",", ".")


def format_datetime(value):
    return value.strftime("%d-%m-%Y %H:%M") if value else "-"


def format_date(value):
    return value.strftime("%d-%m-%Y") if value else "-"


def format_time(value):
    return value.strftime("%H:%M") if value else ""


def form_date(value):
    return value.isoformat() if value else ""


def form_time(value):
    return value.strftime("%H:%M") if value else ""


def format_duration(seconds):
    total = max(int(seconds or 0), 0)
    days, remainder = divmod(total, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days} d")
    if hours:
        parts.append(f"{hours} h")
    if minutes:
        parts.append(f"{minutes} min")
    if secs:
        parts.append(f"{secs} s")
    if not parts:
        parts.append("0 s")
    return " ".join(parts)


def seed_demo_data():
    if db_session.query(Sale).first() or db_session.query(Expense).first() or db_session.query(WorkSession).first():
        return

    today = now_santiago().date()
    demo_day = today - timedelta(days=2)
    opened = datetime.combine(demo_day, datetime.min.time()).replace(hour=11, minute=30)
    closed = datetime.combine(demo_day, datetime.min.time()).replace(hour=21, minute=10)
    work_session = WorkSession(
        business_date=demo_day,
        opened_at=opened,
        closed_at=closed,
        opening_cash=50000,
        closing_cash=187500,
        closing_cash_counted=187500,
        notes="Jornada de demostración.",
        status="closed",
    )
    db_session.add(work_session)
    db_session.flush()

    sales = [
        Sale(work_session_id=work_session.id, occurred_at=opened + timedelta(hours=1), amount=12500, payment_method="cash", channel="food_truck", description="Demo: combo doble"),
        Sale(work_session_id=work_session.id, occurred_at=opened + timedelta(hours=2), amount=18900, payment_method="debit", channel="food_truck", description="Demo: dos burgers"),
        Sale(work_session_id=work_session.id, occurred_at=opened + timedelta(hours=4), amount=9900, payment_method="transfer", channel="pickup", description="Demo: pedido retiro"),
        Sale(work_session_id=work_session.id, occurred_at=opened + timedelta(hours=6), amount=22100, payment_method="credit", channel="delivery", description="Demo: delivery familiar"),
    ]
    expenses = [
        Expense(work_session_id=work_session.id, occurred_at=opened + timedelta(minutes=30), amount=18000, category="Insumos", expense_type="operational", supplier="Demo proveedor pan", payment_method="cash", description="Demo: compra de panes"),
        Expense(work_session_id=work_session.id, occurred_at=opened + timedelta(hours=3), amount=12000, category="Gas", expense_type="operational", supplier="Demo gas local", payment_method="debit", description="Demo: recarga de gas"),
        Expense(work_session_id=None, occurred_at=opened - timedelta(days=5), amount=450000, category="Inversión food truck", expense_type="investment", supplier="Demo equipamiento", payment_method="transfer", description="Demo: mejora inicial del food truck"),
    ]
    db_session.add_all(sales + expenses)
    db_session.commit()


if __name__ == "__main__":
    development_app = create_app()
    development_app.run(debug=development_app.config["APP_ENV"] == "development")

import json
from unittest.mock import patch

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

import models
from app import create_app
from config import TestConfig, resolve_database_uri
from models import Base, db_session, drop_tables
from models.work_session import WorkSession
from services.backup import create_backup, supports_local_backup
from services.database import database_is_available


def test_database_url_absent_uses_local_sqlite(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert resolve_database_uri().startswith("sqlite:///")
    assert resolve_database_uri().endswith("instance/tbb_finanzas.db")


def test_postgresql_database_url_uses_psycopg_driver():
    uri = resolve_database_uri("postgresql://amon:secret@example.test/erp")

    assert uri == "postgresql+psycopg://amon:secret@example.test/erp"


def test_test_config_remains_in_memory_sqlite():
    assert TestConfig.SQLALCHEMY_DATABASE_URI == "sqlite:///:memory:"


def test_sqlite_engine_keeps_thread_option_and_foreign_keys():
    with patch("models.create_engine", wraps=create_engine) as create:
        engine = models.init_engine("sqlite:///:memory:")

    assert create.call_args.kwargs["connect_args"] == {"check_same_thread": False}
    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1


def test_postgresql_engine_uses_pre_ping_without_sqlite_options():
    fake_engine = create_engine("sqlite:///:memory:")
    with patch("models.create_engine", return_value=fake_engine) as create:
        models.init_engine("postgresql+psycopg://user:secret@example.test/erp")

    assert create.call_args.kwargs["pool_pre_ping"] is True
    assert "connect_args" not in create.call_args.kwargs


def test_work_session_index_protects_sqlite_and_postgresql():
    index = next(
        item for item in WorkSession.__table__.indexes
        if item.name == "uq_work_sessions_single_open"
    )

    assert index.unique is True
    assert str(index.dialect_options["sqlite"]["where"]) == "status = 'open'"
    assert str(index.dialect_options["postgresql"]["where"]) == "status = 'open'"


def test_health_is_public_and_reports_database(client, app):
    app.config.update(AUTH_TEST_BYPASS=False, CLERK_SECRET_KEY="")

    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": "ok"}


def test_health_returns_503_without_leaking_secrets(client, caplog):
    secret_uri = "postgresql://private-user:private-password@example.test/erp"
    with patch("app.database_is_available", return_value=False):
        response = client.get("/health")

    assert response.status_code == 503
    assert response.get_json() == {"status": "degraded", "database": "error"}
    assert secret_uri not in response.get_data(as_text=True)
    assert secret_uri not in caplog.text


def test_database_probe_swallows_connection_details():
    class BrokenBind:
        def connect(self):
            raise RuntimeError("postgresql://user:password@example.test/erp")

    assert database_is_available(BrokenBind()) is False


def test_sqlite_backup_still_copies_database(tmp_path):
    source = tmp_path / "source.db"
    source.write_bytes(b"sqlite data")

    target = create_backup(source, tmp_path / "backups")

    assert target.read_bytes() == b"sqlite data"
    assert supports_local_backup(f"sqlite:///{source}") is True


def test_postgresql_backup_endpoint_never_copies_file(client, app, csrf):
    app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql+psycopg://user:secret@example.test/erp"

    with patch("app.create_backup") as create:
        response = client.post("/backup", data=csrf)

    assert response.status_code == 302
    create.assert_not_called()
    assert supports_local_backup(app.config["SQLALCHEMY_DATABASE_URI"]) is False


def test_postgresql_ui_does_not_offer_local_backup(client, app):
    app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql+psycopg://user:secret@example.test/erp"

    response = client.get("/")

    assert response.status_code == 200
    assert b"Crear respaldo" not in response.data
    assert b"Respaldo PostgreSQL fuera de esta aplicaci" in response.data


def test_production_environment_enables_secure_cookies(tmp_path):
    production_app = create_app({
        "APP_ENV": "production",
        "TESTING": True,
        "AUTH_TEST_BYPASS": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "BACKUP_DIR": tmp_path / "backups",
    })

    assert production_app.config["SESSION_COOKIE_SECURE"] is True
    assert production_app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert production_app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    db_session.remove()
    drop_tables()


def test_db_check_succeeds_with_current_schema(app):
    result = app.test_cli_runner().invoke(args=["db-check"])

    assert result.exit_code == 0
    assert "Conexión y schema verificados." in result.output


def test_db_check_fails_when_open_session_index_is_missing(app):
    with models.get_engine().begin() as connection:
        connection.execute(text("DROP INDEX uq_work_sessions_single_open"))

    result = app.test_cli_runner().invoke(args=["db-check"])

    assert result.exit_code != 0
    assert "índice único requerido" in result.output


def test_db_check_rejects_non_partial_open_session_index(app):
    with models.get_engine().begin() as connection:
        connection.execute(text("DROP INDEX uq_work_sessions_single_open"))
        connection.execute(text(
            "CREATE UNIQUE INDEX uq_work_sessions_single_open ON work_sessions (status)"
        ))

    result = app.test_cli_runner().invoke(args=["db-check"])

    assert result.exit_code != 0
    assert "índice único requerido" in result.output


def test_schema_bootstrap_failure_keeps_health_available(tmp_path):
    with patch("app.create_tables", side_effect=SQLAlchemyError("private database detail")):
        flask_app = create_app({
            "TESTING": True,
            "AUTH_TEST_BYPASS": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "BACKUP_DIR": tmp_path / "backups",
        })

    response = flask_app.test_client().get("/health")
    assert response.status_code == 200
    assert b"private database detail" not in response.data


def test_db_counts_reports_migration_diagnostics(app):
    result = app.test_cli_runner().invoke(args=["db-counts"])

    assert result.exit_code == 0
    assert json.loads(result.output) == {
        "audit_logs": 0,
        "expenses": 0,
        "sales": 0,
        "work_sessions": 0,
    }


def test_metadata_contains_all_expected_tables():
    assert {"sales", "expenses", "work_sessions", "audit_logs"} <= set(Base.metadata.tables)

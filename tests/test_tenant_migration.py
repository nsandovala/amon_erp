from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError


ROOT = Path(__file__).parents[1]


def _legacy_schema(connection):
    connection.execute(text("""
        CREATE TABLE work_sessions (
            id INTEGER PRIMARY KEY,
            business_date DATE NOT NULL,
            opened_at DATETIME NOT NULL,
            closed_at DATETIME,
            opening_cash INTEGER NOT NULL,
            closing_cash INTEGER,
            closing_cash_counted INTEGER,
            closing_notes TEXT,
            notes TEXT,
            status VARCHAR(20) NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            deleted_at DATETIME
        )
    """))
    connection.execute(text("CREATE UNIQUE INDEX uq_work_sessions_single_open ON work_sessions(status) WHERE status = 'open'"))
    connection.execute(text("""
        CREATE TABLE sales (
            id INTEGER PRIMARY KEY, work_session_id INTEGER, occurred_at DATETIME NOT NULL,
            amount INTEGER NOT NULL, payment_method VARCHAR(20) NOT NULL, channel VARCHAR(20) NOT NULL,
            description VARCHAR(160), notes TEXT, status VARCHAR(20) NOT NULL,
            created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL, deleted_at DATETIME
        )
    """))
    connection.execute(text("""
        CREATE TABLE expenses (
            id INTEGER PRIMARY KEY, work_session_id INTEGER, occurred_at DATETIME NOT NULL,
            amount INTEGER NOT NULL, category VARCHAR(80) NOT NULL, expense_type VARCHAR(20) NOT NULL,
            supplier VARCHAR(120), payment_method VARCHAR(20) NOT NULL, description VARCHAR(160) NOT NULL,
            notes TEXT, status VARCHAR(20) NOT NULL, created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL, deleted_at DATETIME
        )
    """))
    connection.execute(text("""
        CREATE TABLE audit_logs (
            id INTEGER PRIMARY KEY, action VARCHAR(80) NOT NULL, entity_type VARCHAR(40) NOT NULL,
            entity_id INTEGER NOT NULL, old_values TEXT, new_values TEXT, created_at DATETIME NOT NULL
        )
    """))
    values = {"now": "2026-10-03 10:00:00"}
    connection.execute(text("""INSERT INTO work_sessions
        (id, business_date, opened_at, opening_cash, status, created_at, updated_at)
        VALUES (1, '2026-10-03', :now, 10000, 'open', :now, :now)"""), values)
    connection.execute(text("""INSERT INTO sales
        (id, work_session_id, occurred_at, amount, payment_method, channel, status, created_at, updated_at)
        VALUES (1, 1, :now, 15000, 'cash', 'food_truck', 'active', :now, :now)"""), values)
    connection.execute(text("""INSERT INTO expenses
        (id, work_session_id, occurred_at, amount, category, expense_type, payment_method, description, status, created_at, updated_at)
        VALUES (1, 1, :now, 5000, 'Insumos', 'operational', 'cash', 'Insumos', 'active', :now, :now)"""), values)
    connection.execute(text("""INSERT INTO audit_logs
        (id, action, entity_type, entity_id, created_at)
        VALUES (1, 'legacy', 'sale', 1, :now)"""), values)


def test_tenant_revision_backfills_legacy_sqlite_and_replaces_open_index(tmp_path):
    database_path = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{database_path}")
    with engine.begin() as connection:
        _legacy_schema(connection)

    config = Config(str(ROOT / "alembic.ini"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")

    with engine.begin() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM sales")).scalar_one() == 1
        assert connection.execute(text("SELECT COUNT(*) FROM expenses")).scalar_one() == 1
        assert connection.execute(text("SELECT COUNT(*) FROM work_sessions")).scalar_one() == 1
        assert connection.execute(text("SELECT COUNT(*) FROM audit_logs")).scalar_one() == 1
        assert connection.execute(text("SELECT COUNT(*) FROM sales WHERE organization_id IS NULL OR branch_id IS NULL")).scalar_one() == 0
        assert connection.execute(text("SELECT COUNT(*) FROM expenses WHERE organization_id IS NULL OR branch_id IS NULL")).scalar_one() == 0
        assert connection.execute(text("SELECT COUNT(*) FROM work_sessions WHERE organization_id IS NULL OR branch_id IS NULL")).scalar_one() == 0
        for table_name in ("sales", "expenses", "work_sessions"):
            columns = {row[1]: row[3] for row in connection.execute(text(f"PRAGMA table_info({table_name})"))}
            assert columns["organization_id"] == 1
            assert columns["branch_id"] == 1
        organization_id, branch_id = connection.execute(text(
            "SELECT o.id, b.id FROM organizations o JOIN branches b ON b.organization_id = o.id "
            "WHERE o.slug = 'the-best-burger' AND b.slug = 'principal'"
        )).one()
        connection.execute(text(
            "INSERT INTO organizations (name, slug, entity_type, status, created_at, updated_at) "
            "VALUES ('2MUCH', '2much', 'company', 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ))
        second_org_id = connection.execute(text("SELECT id FROM organizations WHERE slug = '2much'")).scalar_one()
        connection.execute(text(
            "INSERT INTO branches (organization_id, name, slug, status, created_at, updated_at) "
            "VALUES (:organization_id, 'Principal', 'principal', 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ), {"organization_id": second_org_id})
        second_branch_id = connection.execute(text("SELECT id FROM branches WHERE organization_id = :organization_id"), {"organization_id": second_org_id}).scalar_one()

    with engine.begin() as connection:
        with pytest.raises(IntegrityError):
            connection.execute(text(
                "INSERT INTO work_sessions (organization_id, branch_id, business_date, opened_at, opening_cash, status, created_at, updated_at) "
                "VALUES (:organization_id, :branch_id, '2026-10-03', '2026-10-03 12:00:00', 0, 'open', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ), {"organization_id": organization_id, "branch_id": branch_id})
        connection.execute(text(
            "INSERT INTO work_sessions (organization_id, branch_id, business_date, opened_at, opening_cash, status, created_at, updated_at) "
            "VALUES (:organization_id, :branch_id, '2026-10-03', '2026-10-03 12:00:00', 0, 'open', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ), {"organization_id": second_org_id, "branch_id": second_branch_id})

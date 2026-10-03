"""Add explicit tenant ownership to financial records.

Revision ID: 20261003_01
Revises:
Create Date: 2026-10-03
"""

from alembic import op
import sqlalchemy as sa

from models.branch import Branch
from models.membership import Membership
from models.organization import Organization


revision = "20261003_01"
down_revision = None
branch_labels = None
depends_on = None

TENANT_TABLES = ("sales", "expenses", "work_sessions")


def _columns(bind, table_name):
    return {column["name"] for column in sa.inspect(bind).get_columns(table_name)}


def _index_names(bind, table_name):
    return {index["name"] for index in sa.inspect(bind).get_indexes(table_name)}


def _tenant_root(bind):
    Organization.__table__.create(bind, checkfirst=True)
    Branch.__table__.create(bind, checkfirst=True)
    Membership.__table__.create(bind, checkfirst=True)
    organization_id = bind.execute(sa.text(
        "SELECT id FROM organizations WHERE slug = :slug"
    ), {"slug": "the-best-burger"}).scalar()
    if organization_id is None:
        bind.execute(sa.text(
            "INSERT INTO organizations (name, slug, entity_type, status, created_at, updated_at) "
            "VALUES ('The Best Burger', 'the-best-burger', 'company', 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ))
        organization_id = bind.execute(sa.text(
            "SELECT id FROM organizations WHERE slug = 'the-best-burger'"
        )).scalar_one()
    branch_id = bind.execute(sa.text(
        "SELECT id FROM branches WHERE organization_id = :organization_id AND slug = :slug"
    ), {"organization_id": organization_id, "slug": "principal"}).scalar()
    if branch_id is None:
        bind.execute(sa.text(
            "INSERT INTO branches (organization_id, name, slug, status, created_at, updated_at) "
            "VALUES (:organization_id, 'Principal', 'principal', 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ), {"organization_id": organization_id})
        branch_id = bind.execute(sa.text(
            "SELECT id FROM branches WHERE organization_id = :organization_id AND slug = 'principal'"
        ), {"organization_id": organization_id}).scalar_one()
    return organization_id, branch_id


def _add_tenant_columns(bind, table_name, include_actor=False):
    columns = _columns(bind, table_name)
    if "organization_id" not in columns:
        op.add_column(table_name, sa.Column("organization_id", sa.Integer(), nullable=True))
    if "branch_id" not in columns:
        op.add_column(table_name, sa.Column("branch_id", sa.Integer(), nullable=True))
    if include_actor and "actor_user_id" not in columns:
        op.add_column(table_name, sa.Column("actor_user_id", sa.String(length=128), nullable=True))


def _backfill_and_validate(bind, table_name, organization_id, branch_id):
    before = bind.execute(sa.text(f"SELECT COUNT(*) FROM {table_name}")).scalar_one()
    bind.execute(sa.text(
        f"UPDATE {table_name} SET organization_id = :organization_id, branch_id = :branch_id "
        "WHERE organization_id IS NULL AND branch_id IS NULL"
    ), {"organization_id": organization_id, "branch_id": branch_id})
    nulls = bind.execute(sa.text(
        f"SELECT COUNT(*) FROM {table_name} WHERE organization_id IS NULL OR branch_id IS NULL"
    )).scalar_one()
    after = bind.execute(sa.text(f"SELECT COUNT(*) FROM {table_name}")).scalar_one()
    if before != after or nulls:
        raise RuntimeError(f"Tenant backfill validation failed for {table_name}.")


def _tighten_financial_table(table_name):
    # Alembic uses a transactional batch rebuild only on SQLite because SQLite
    # cannot alter nullability or add foreign keys in place. Rows are copied;
    # this is not a reset/drop-and-recreate application migration.
    with op.batch_alter_table(table_name, recreate="auto") as batch:
        batch.alter_column("organization_id", existing_type=sa.Integer(), nullable=False)
        batch.alter_column("branch_id", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key(f"fk_{table_name}_organization", "organizations", ["organization_id"], ["id"])
        batch.create_foreign_key(f"fk_{table_name}_branch", "branches", ["branch_id"], ["id"])


def upgrade():
    bind = op.get_bind()
    organization_id, branch_id = _tenant_root(bind)
    for table_name in TENANT_TABLES:
        _add_tenant_columns(bind, table_name)
        _backfill_and_validate(bind, table_name, organization_id, branch_id)
    _add_tenant_columns(bind, "audit_logs", include_actor=True)
    _backfill_and_validate(bind, "audit_logs", organization_id, branch_id)

    indexes = _index_names(bind, "work_sessions")
    if "uq_work_sessions_single_open" in indexes:
        op.drop_index("uq_work_sessions_single_open", table_name="work_sessions")
    for table_name in TENANT_TABLES:
        _tighten_financial_table(table_name)

    op.create_index("ix_sales_tenant_occurred_at", "sales", ["organization_id", "branch_id", "occurred_at"])
    op.create_index("ix_expenses_tenant_occurred_at", "expenses", ["organization_id", "branch_id", "occurred_at"])
    op.create_index("ix_work_sessions_tenant_opened_at", "work_sessions", ["organization_id", "branch_id", "opened_at"])
    op.create_index("ix_audit_logs_tenant_created_at", "audit_logs", ["organization_id", "branch_id", "created_at"])
    op.create_index(
        "uq_work_sessions_open_per_branch",
        "work_sessions",
        ["organization_id", "branch_id"],
        unique=True,
        sqlite_where=sa.text("status = 'open' AND deleted_at IS NULL"),
        postgresql_where=sa.text("status = 'open' AND deleted_at IS NULL"),
    )


def downgrade():
    raise RuntimeError(
        "F2.1 does not downgrade tenant ownership automatically. Restore a verified backup instead."
    )

from logging.config import fileConfig

from alembic import context

from config import Config
from models import Base
from models.audit_log import AuditLog  # noqa: F401
from models.branch import Branch  # noqa: F401
from models.expense import Expense  # noqa: F401
from models.membership import Membership  # noqa: F401
from models.organization import Organization  # noqa: F401
from models.sale import Sale  # noqa: F401
from models.work_session import WorkSession  # noqa: F401


config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(
        url=config.get_main_option("sqlalchemy.url") or Config.SQLALCHEMY_DATABASE_URI,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connection = config.attributes.get("connection")
    if connection is not None:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
        return

    from sqlalchemy import create_engine

    engine = create_engine(config.get_main_option("sqlalchemy.url") or Config.SQLALCHEMY_DATABASE_URI)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

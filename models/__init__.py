import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker


TZ = ZoneInfo("America/Santiago")
Base = declarative_base()
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False))
engine = None


def now_santiago():
    return datetime.now(TZ).replace(tzinfo=None, microsecond=0)


def init_engine(database_uri):
    global engine
    db_session.remove()
    if engine is not None:
        engine.dispose()

    engine_options = {"future": True}
    if database_uri.startswith("sqlite"):
        engine_options["connect_args"] = {"check_same_thread": False}
    else:
        engine_options["pool_pre_ping"] = True
    engine = create_engine(database_uri, **engine_options)

    if database_uri.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    db_session.configure(bind=engine)
    Base.query = db_session.query_property()
    return engine


def get_engine():
    return engine


def create_tables():
    from models.audit_log import AuditLog  # noqa: F401
    from models.expense import Expense  # noqa: F401
    from models.sale import Sale  # noqa: F401
    from models.work_session import WorkSession  # noqa: F401

    Base.metadata.create_all(bind=engine)


def drop_tables():
    Base.metadata.drop_all(bind=engine)


def ensure_soft_delete_columns(database_uri, backup_dir):
    if not database_uri.startswith("sqlite"):
        return []

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    target_tables = ("sales", "expenses", "work_sessions")
    missing = []

    for table_name in target_tables:
        if table_name not in existing_tables:
            continue
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        if "deleted_at" not in columns:
            missing.append(table_name)

    if not missing:
        return []

    db_path = database_uri.replace("sqlite:///", "")
    if db_path != ":memory:" and Path(db_path).exists():
        target_dir = Path(backup_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        shutil.copy2(db_path, target_dir / f"pre_migration_soft_delete_{timestamp}.db")

    with engine.begin() as connection:
        for table_name in missing:
            connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN deleted_at DATETIME"))

    return missing


def ensure_work_session_cash_columns(database_uri, backup_dir):
    if not database_uri.startswith("sqlite"):
        return []

    inspector = inspect(engine)
    if "work_sessions" not in inspector.get_table_names():
        return []
    columns = {column["name"] for column in inspector.get_columns("work_sessions")}
    definitions = {
        "closing_cash_counted": "INTEGER",
        "closing_notes": "TEXT",
    }
    missing = [name for name in definitions if name not in columns]
    if not missing:
        return []

    db_path = database_uri.replace("sqlite:///", "")
    if db_path != ":memory:" and Path(db_path).exists():
        target_dir = Path(backup_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        shutil.copy2(db_path, target_dir / f"pre_migration_f0_{timestamp}.db")

    with engine.begin() as connection:
        for column_name in missing:
            connection.execute(text(
                f"ALTER TABLE work_sessions ADD COLUMN {column_name} {definitions[column_name]}"
            ))
        if "closing_cash_counted" in missing:
            connection.execute(text(
                "UPDATE work_sessions SET closing_cash_counted = closing_cash "
                "WHERE closing_cash_counted IS NULL AND closing_cash IS NOT NULL"
            ))

    return missing

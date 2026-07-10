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
    connect_args = {"check_same_thread": False} if database_uri.startswith("sqlite") else {}
    engine = create_engine(database_uri, connect_args=connect_args, future=True)

    if database_uri.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    db_session.configure(bind=engine)
    Base.query = db_session.query_property()
    return engine


def create_tables():
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

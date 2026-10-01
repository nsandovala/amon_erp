import shutil
from datetime import datetime
from pathlib import Path

from sqlalchemy.engine import make_url


def supports_local_backup(database_uri):
    return make_url(database_uri).get_backend_name() == "sqlite"


def local_database_path(database_uri):
    url = make_url(database_uri)
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        raise ValueError("El respaldo local solo está disponible para una base SQLite en disco.")
    return Path(url.database)


def create_backup(database_path, backup_dir):
    source = Path(database_path)
    if not source.exists():
        raise FileNotFoundError("No existe una base de datos para respaldar.")

    target_dir = Path(backup_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    target = target_dir / f"tbb_finanzas_{timestamp}.db"
    counter = 1
    while target.exists():
        target = target_dir / f"tbb_finanzas_{timestamp}_{counter}.db"
        counter += 1

    shutil.copy2(source, target)
    return target

import shutil
from datetime import datetime
from pathlib import Path


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

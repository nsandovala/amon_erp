import os
import secrets
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def local_secret_key():
    secret_path = BASE_DIR / "instance" / ".secret_key"
    env_secret = os.environ.get("TBB_SECRET_KEY")
    if env_secret:
        return env_secret
    secret_path.parent.mkdir(parents=True, exist_ok=True)
    if secret_path.exists():
        return secret_path.read_text(encoding="utf-8").strip()
    secret = secrets.token_urlsafe(48)
    secret_path.write_text(secret, encoding="utf-8")
    return secret


class Config:
    SECRET_KEY = local_secret_key()
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{BASE_DIR / 'instance' / 'tbb_finanzas.db'}"
    BACKUP_DIR = BASE_DIR / "backups"
    TIMEZONE = "America/Santiago"


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

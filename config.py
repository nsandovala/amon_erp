import os
import secrets
from pathlib import Path
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env.local', override=False)
load_dotenv(BASE_DIR / '.env', override=False)


def resolve_database_uri(database_url=None):
    database_url = database_url or os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        return f"sqlite:///{BASE_DIR / 'instance' / 'tbb_finanzas.db'}"
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


ADMISSION_MODES = ("allowlist", "membership")
DEFAULT_ADMISSION_MODE = "allowlist"


def resolve_admission_mode(value=None):
    """Validate AMON_ADMISSION_MODE; unset/blank keeps the transitional default.

    Anything else that is not a known mode is a configuration error: never a
    silent fallback (least of all to the more permissive "membership").
    """
    mode = (value or "").strip().lower() or DEFAULT_ADMISSION_MODE
    if mode not in ADMISSION_MODES:
        raise RuntimeError(
            f"AMON_ADMISSION_MODE inválido ({value!r}). Valores permitidos: {', '.join(ADMISSION_MODES)}."
        )
    return mode


def local_secret_key():
    secret_path = BASE_DIR / "instance" / ".secret_key"
    env_secret = (
        os.environ.get("SECRET_KEY")
        or os.environ.get("TBB_SECRET_KEY")
    )
    if env_secret:
        return env_secret
    secret_path.parent.mkdir(parents=True, exist_ok=True)
    if secret_path.exists():
        return secret_path.read_text(encoding="utf-8").strip()
    secret = secrets.token_urlsafe(48)
    secret_path.write_text(secret, encoding="utf-8")
    return secret


class Config:
    APP_ENV = os.environ.get("APP_ENV", "development").strip().lower()
    CLERK_PUBLISHABLE_KEY = os.environ.get('CLERK_PUBLISHABLE_KEY', '')
    CLERK_SECRET_KEY = os.environ.get('CLERK_SECRET_KEY', '')
    CLERK_AUTHORIZED_PARTIES = [value.strip() for value in os.environ.get(
        'CLERK_AUTHORIZED_PARTIES', 'http://127.0.0.1:5000,http://localhost:5000'
    ).split(',') if value.strip()]
    AMON_ALLOWED_USER_IDS = [value.strip() for value in os.environ.get(
        'AMON_ALLOWED_USER_IDS', ''
    ).split(',') if value.strip()]
    AMON_ADMISSION_MODE = resolve_admission_mode(os.environ.get('AMON_ADMISSION_MODE'))
    AUTH_TEST_BYPASS = False
    SECRET_KEY = local_secret_key()
    SQLALCHEMY_DATABASE_URI = resolve_database_uri()
    BACKUP_DIR = BASE_DIR / "backups"
    TIMEZONE = "America/Santiago"
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

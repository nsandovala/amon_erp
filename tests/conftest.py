import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from models import create_tables, db_session, drop_tables


@pytest.fixture
def app(tmp_path):
    flask_app = create_app({
        "TESTING": True,
        "AUTH_TEST_BYPASS": True,
        "SECRET_KEY": "test-secret",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "BACKUP_DIR": tmp_path / "backups",
    })
    with flask_app.app_context():
        create_tables()
        yield flask_app
        db_session.remove()
        drop_tables()


@pytest.fixture
def client(app):
    with app.test_client() as client:
        with client.session_transaction() as session:
            session["csrf_token"] = "test-token"
        yield client


@pytest.fixture
def csrf():
    return {"csrf_token": "test-token"}

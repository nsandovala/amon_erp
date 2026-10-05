"""F2.5: AMON_ADMISSION_MODE (allowlist | membership) — both modes, fail-closed.

Clerk identity is simulated with locally signed tokens; Clerk's API is never called.
"""
import base64
import time
from unittest.mock import patch

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app import create_app
from config import ADMISSION_MODES, DEFAULT_ADMISSION_MODE, resolve_admission_mode
from models import create_tables, db_session, drop_tables
from models.branch import Branch
from models.membership import Membership
from models.organization import Organization
from services import auth, clerk_directory
from services.clerk_directory import ClerkDirectoryError
from services.organizations import bootstrap_the_best_burger

ALLOWLISTED = ["user_allowed", "user_lonely", "user_inactive", "user_dormant", "user_nobranch", "user_multi"]
# Deliberately NOT allowlisted: user_member (has a valid Membership) and user_new (nothing).


class World:
    def __init__(self, app, key, client):
        self.app, self.key, self.client = app, key, client

    def get(self, path, sub, **claims):
        base = dict(sub=sub, sid="sess_test", azp="http://localhost", iat=int(time.time()),
                    nbf=int(time.time()) - 10, exp=int(time.time()) + 300)
        claims = {**base, **claims}
        token = jwt.encode(claims, self.key, algorithm="RS256", headers={"kid": "test"})
        return self.client.get(path, headers={"Authorization": "Bearer " + token})

    def set_role(self, user_id, role):
        with self.app.app_context():
            db_session.query(Membership).filter_by(clerk_user_id=user_id).one().role = role
            db_session.commit()


def seed():
    organization, _branch = bootstrap_the_best_burger()
    for user_id, status in [("user_allowed", "active"), ("user_member", "active"), ("user_inactive", "inactive"), ("user_multi", "active")]:
        db_session.add(Membership(organization_id=organization.id, clerk_user_id=user_id, role="owner", status=status))
    dormant = Organization(name="Dormida", slug="dormida", entity_type="company", status="archived")
    empty = Organization(name="Sin sucursal", slug="sin-sucursal", entity_type="company")
    second = Organization(name="2MUCH", slug="2much", entity_type="company")
    db_session.add_all([dormant, empty, second]); db_session.flush()
    db_session.add_all([
        Branch(organization_id=dormant.id, name="Principal", slug="principal"),
        Branch(organization_id=second.id, name="Principal", slug="principal"),
        Membership(organization_id=dormant.id, clerk_user_id="user_dormant", role="owner"),
        Membership(organization_id=empty.id, clerk_user_id="user_nobranch", role="owner"),
        Membership(organization_id=second.id, clerk_user_id="user_multi", role="owner"),
    ])
    db_session.commit()


def make_world(tmp_path, mode):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    config = {
        "TESTING": True, "AUTH_TEST_BYPASS": False, "SECRET_KEY": "test-secret",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "BACKUP_DIR": tmp_path / "backups",
        "CLERK_SECRET_KEY": "sk_test_not_a_real_key",
        "CLERK_PUBLISHABLE_KEY": "pk_test_" + base64.b64encode(b"example.clerk.accounts.dev$").decode(),
        "CLERK_AUTHORIZED_PARTIES": ["http://localhost"], "AMON_ALLOWED_USER_IDS": list(ALLOWLISTED),
    }
    if mode is not None:
        config["AMON_ADMISSION_MODE"] = mode
    app = create_app(config)
    real = auth.authenticate_request

    def locally(request, options):
        options.jwt_key = public_key
        return real(request, options)

    return app, key, locally


@pytest.fixture(autouse=True)
def no_real_clerk():
    """Any un-mocked Clerk directory call fails closed instead of reaching the network."""
    with patch.object(clerk_directory, "_client", side_effect=ClerkDirectoryError("blocked in tests")):
        yield


def run_world(tmp_path, mode):
    app, key, locally = make_world(tmp_path, mode)
    app.world_mode = mode or "allowlist"
    with app.app_context():
        create_tables()
        seed()
        with patch.object(auth, "authenticate_request", side_effect=locally):
            yield World(app, key, app.test_client())
        db_session.remove()
        drop_tables()


@pytest.fixture(params=["default", "allowlist", "membership"])
def world(request, tmp_path):
    """Every behaviour shared by both modes, with the mode set explicitly (or left at the default)."""
    yield from run_world(tmp_path, None if request.param == "default" else request.param)


@pytest.fixture
def membership_world(tmp_path):
    """AMON_ADMISSION_MODE=membership configured explicitly, in isolation from the default."""
    yield from run_world(tmp_path, "membership")


# ---------- configuración ----------

def test_default_mode_is_allowlist_and_configuration_is_strict():
    assert DEFAULT_ADMISSION_MODE == "allowlist" and ADMISSION_MODES == ("allowlist", "membership")
    assert resolve_admission_mode(None) == "allowlist" == resolve_admission_mode("") == resolve_admission_mode("  ")
    assert resolve_admission_mode(" Membership ") == "membership"
    assert resolve_admission_mode("allowlist") == "allowlist"


@pytest.mark.parametrize("bad", ["open", "members", "true", "1", "none", "allow-list"])
def test_invalid_mode_is_a_configuration_error_never_a_silent_fallback(bad, tmp_path):
    with pytest.raises(RuntimeError, match="AMON_ADMISSION_MODE inválido"):
        resolve_admission_mode(bad)
    with pytest.raises(RuntimeError, match="AMON_ADMISSION_MODE inválido"):
        make_world(tmp_path, bad)


def test_world_modes_are_what_the_tests_assume(world):
    assert world.app.config["AMON_ADMISSION_MODE"] == world.app.world_mode


# ---------- matriz de admisión ----------

def expected_status(mode, user):
    """(status, redirect location) per user and mode. user_new is never admitted."""
    common = {"user_new": 403, "user_lonely": 403, "user_inactive": 403, "user_dormant": 403, "user_nobranch": 403}
    if mode == "allowlist":
        common.update(user_allowed=200, user_member=403, user_multi=302)
    else:
        common.update(user_allowed=200, user_member=200, user_multi=302)
    return common[user]


@pytest.mark.parametrize("user", ["user_allowed", "user_member", "user_lonely", "user_inactive",
                                  "user_dormant", "user_nobranch", "user_multi", "user_new"])
def test_admission_matrix(world, user):
    response = world.get("/", user)
    assert response.status_code == expected_status(world.app.world_mode, user), (world.app.world_mode, user)
    if response.status_code == 302:
        assert response.location == "/contexto/"
    if response.status_code == 403:
        assert "Tu cuenta no tiene acceso a AMON ERP." in response.get_data(as_text=True)


def test_member_not_allowlisted_follows_mode(world):
    admitted = world.app.world_mode == "membership"
    assert (world.get("/", "user_member").status_code == 200) is admitted
    auth_page = world.get("/auth", "user_member")
    assert (auth_page.status_code == 302 and auth_page.location == "/") is admitted
    assert (auth_page.status_code == 200) is not admitted


def test_allowlisted_without_membership_is_denied_in_both_modes(world):
    assert world.get("/", "user_lonely").status_code == 403
    assert world.get("/sales", "user_lonely").status_code == 403


def test_multiple_memberships_still_require_context_selection(world):
    assert world.get("/", "user_multi").location == "/contexto/"
    assert world.get("/contexto/", "user_multi").status_code == 200  # selector renders before any context exists
    assert world.get("/contexto/?force=1", "user_multi").status_code == 200


def test_unauthenticated_and_invalid_identities_stay_denied_in_both_modes(world):
    assert world.client.get("/").location == "/auth"
    assert world.client.post("/backup").status_code == 401
    assert world.get("/", "user_member", sts="pending").status_code == 302
    assert world.get("/", "user_member", azp="https://untrusted.example").status_code == 302
    assert world.get("/", "org_member").status_code == 302  # sub must be a Clerk user id


@pytest.mark.parametrize("claims", [
    {"role": "owner"}, {"org_role": "org:admin"}, {"org_id": "org_x", "org_role": "org:admin", "role": "owner"},
])
def test_clerk_claims_never_grant_access_or_roles(world, claims):
    assert world.get("/", "user_new", **claims).status_code == 403
    world.set_role("user_allowed", "operator")
    assert world.get("/administracion/", "user_allowed", **claims).status_code == 403
    assert world.get("/", "user_allowed", **claims).status_code == 200


def test_membership_mode_role_comes_only_from_local_membership(membership_world):
    world = membership_world
    assert world.app.config["AMON_ADMISSION_MODE"] == "membership"
    world.set_role("user_member", "accountant_readonly")
    assert world.get("/administracion/", "user_member", role="owner").status_code == 403
    world.set_role("user_member", "owner")
    assert world.get("/administracion/", "user_member").status_code == 200


def test_revoking_membership_revokes_access_immediately(membership_world):
    world = membership_world
    assert world.get("/", "user_member").status_code == 200
    with world.app.app_context():
        db_session.query(Membership).filter_by(clerk_user_id="user_member").one().status = "inactive"
        db_session.commit()
    assert world.get("/", "user_member").status_code == 403
    with world.app.app_context():
        branch = db_session.query(Branch).join(Organization).filter(Organization.slug == "the-best-burger").one()
        branch.status = "archived"
        db_session.commit()
    assert world.get("/", "user_allowed").status_code == 403  # no active branch: no access, in any mode

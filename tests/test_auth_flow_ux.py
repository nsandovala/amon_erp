"""UX-AUTH-001: /auth is the single, deterministic entry point after a Clerk sign-in."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from models import db_session
from models.branch import Branch
from models.membership import Membership
from models.organization import Organization

from test_auth import auth_app, signed_token, signing_key, verified_client  # noqa: F401  (shared auth fixtures)

ROOT = Path(__file__).parents[1]
NO_ACCESS = "Tu cuenta está activa, pero aún no tiene acceso a una organización."


def bearer(key, **claims):
    return {"Authorization": "Bearer " + signed_token(key, **claims)}


def add_second_organization(app):
    with app.app_context():
        organization = Organization(name="2MUCH", slug="2much", entity_type="company")
        db_session.add(organization); db_session.flush()
        db_session.add_all([Branch(organization_id=organization.id, name="Principal", slug="principal"),
                            Membership(organization_id=organization.id, clerk_user_id="user_allowed", role="owner")])
        db_session.commit()


# ---------------------------------------------------------- server-side routing

def test_anonymous_auth_page_shows_the_welcome_and_sign_in_cta(auth_app):
    response = auth_app.test_client().get("/auth")
    html = response.get_data(as_text=True)
    assert response.status_code == 200 and response.headers["Cache-Control"] == "no-store"
    assert 'data-auth-state="anonymous"' in html
    for copy in ("AMON ERP", "Gestiona tu negocio desde un solo lugar.", "Ingresa con tu cuenta AMON para continuar.",
                 "El acceso a una empresa requiere autorización."):
        assert copy in html
    assert re.search(r"<button[^>]*data-auth-sign-in[^>]*>Iniciar sesión</button>", html)
    assert "Verificando acceso…" in html and 'data-auth-view="verifying" hidden' in html     # present but hidden until needed
    assert 'data-auth-view="verify-failed" hidden' in html and "data-auth-retry" in html


def test_auth_page_has_no_own_credential_form(auth_app):
    html = auth_app.test_client().get("/auth").get_data(as_text=True)
    assert "<form" not in html and 'type="password"' not in html and 'name="password"' not in html
    assert "Crear cuenta" not in html and "sk_test_not_a_real_key" not in html


def test_authorized_single_context_goes_straight_to_the_dashboard_without_loops(verified_client, signing_key):
    headers = bearer(signing_key)
    response = verified_client.get("/auth", headers=headers)
    assert (response.status_code, response.location) == (302, "/")
    followed = verified_client.get("/auth", headers=headers, follow_redirects=True)
    assert followed.status_code == 200 and len(followed.history) == 1
    assert followed.request.path == "/" and "Resumen financiero" in followed.get_data(as_text=True)


def test_authorized_multi_context_goes_to_the_selector_without_loops(auth_app, verified_client, signing_key):
    add_second_organization(auth_app)
    headers = bearer(signing_key)
    response = verified_client.get("/auth", headers=headers)
    assert (response.status_code, response.location) == (302, "/contexto/")
    followed = verified_client.get("/auth", headers=headers, follow_redirects=True)
    assert followed.status_code == 200 and followed.request.path == "/contexto/" and len(followed.history) == 1
    assert 'name="organization_id"' in followed.get_data(as_text=True)


def test_authenticated_without_membership_sees_no_access_and_never_loops(verified_client, signing_key):
    headers = bearer(signing_key, sub="user_new")
    response = verified_client.get("/auth", headers=headers, follow_redirects=True)
    html = response.get_data(as_text=True)
    assert response.status_code == 200 and len(response.history) == 0 and response.request.path == "/auth"
    assert 'data-auth-state="no-access"' in html and NO_ACCESS in html and "Pide al administrador que te agregue." in html
    assert re.search(r"<button[^>]*data-auth-sign-out[^>]*>Usar otra cuenta</button>", html)
    assert "user_new" not in html and "Iniciar sesión" not in html


def test_no_access_user_hitting_the_erp_gets_the_same_state_not_a_redirect_loop(verified_client, signing_key):
    response = verified_client.get("/", headers=bearer(signing_key, sub="user_new"))
    assert response.status_code == 403 and NO_ACCESS in response.get_data(as_text=True)
    assert verified_client.get("/jornadas/", headers=bearer(signing_key, sub="user_new")).status_code == 403


def test_inactive_membership_is_a_no_access_state_too(auth_app, verified_client, signing_key):
    with auth_app.app_context():
        db_session.query(Membership).filter_by(clerk_user_id="user_allowed").one().status = "inactive"
        db_session.commit()
    response = verified_client.get("/auth", headers=bearer(signing_key))
    assert response.status_code == 200 and NO_ACCESS in response.get_data(as_text=True)


@pytest.mark.parametrize("claims", [{"role": "owner"}, {"org_role": "org:admin", "org_id": "org_x"}, {"role": "owner", "org_role": "org:admin"}])
def test_clerk_claims_never_turn_a_stranger_into_a_member(verified_client, signing_key, claims):
    headers = bearer(signing_key, sub="user_new", **claims)
    page = verified_client.get("/auth", headers=headers)
    assert page.status_code == 200 and NO_ACCESS in page.get_data(as_text=True)
    assert verified_client.get("/", headers=headers).status_code == 403
    assert verified_client.get("/administracion/", headers=headers).status_code == 403


def test_signed_out_users_are_sent_to_auth_from_every_erp_page(auth_app):
    client = auth_app.test_client()
    for path in ("/", "/jornadas/", "/administracion/", "/contexto/"):
        response = client.get(path)
        assert (response.status_code, response.location) == (302, "/auth"), path
    assert client.get("/auth").status_code == 200   # and /auth itself never redirects anonymous users


def test_unavailable_state_is_presented_without_leaking_details(auth_app):
    auth_app.config["CLERK_SECRET_KEY"] = ""
    response = auth_app.test_client().get("/")
    html = response.get_data(as_text=True)
    assert response.status_code == 503 and 'data-auth-state="unavailable"' in html
    assert "Acceso temporalmente no disponible" in html and "contacta al administrador" in html
    assert "clerk" not in html.lower().replace("clerk.accounts", "")  # no scripts or config for an unavailable auth


# --------------------------------------------------------------- JS contract

JS = (ROOT / "static/js/auth.js").read_text(encoding="utf-8")


def test_sign_in_and_sign_up_force_redirect_to_auth():
    assert "const AUTH_PATH = '/auth';" in JS
    assert re.search(r"Clerk\.load\(\{.*?signInForceRedirectUrl: AUTH_PATH,\s*signUpForceRedirectUrl: AUTH_PATH", JS, re.S)
    assert "clerk.openSignIn({ forceRedirectUrl: AUTH_PATH, signUpForceRedirectUrl: AUTH_PATH })" in JS


def test_post_login_navigation_does_not_depend_on_clerks_redirect_alone():
    assert "clerk.session?.getToken({ skipCache: true })" in JS              # fresh __session cookie before the server check
    assert "window.location.assign(AUTH_PATH)" in JS and "clerk.addListener" in JS
    listener = JS[JS.index("clerk.addListener"):]
    assert "showView('verifying')" in listener and "goToAuth()" in listener


def test_server_verification_has_a_loop_guard_and_a_failure_state():
    assert "sessionStorage" in JS and "GUARD_WINDOW_MS" in JS
    anonymous_branch = JS[JS.index("authState === 'anonymous'"):JS.index("if (menu && clerk.user)")]
    assert "guard.recent()" in anonymous_branch and "showView('verify-failed')" in anonymous_branch
    assert anonymous_branch.count("window.location.assign") == 0                 # the only automatic reload is inside goToAuth(), once
    assert "guard.mark()" in anonymous_branch and "await goToAuth()" in anonymous_branch
    assert "data-auth-retry" in JS


def test_there_is_no_static_signed_in_end_state():
    for path in ("static/js/auth.js", "templates/auth/access.html", "templates/auth/controls.html", "templates/auth/account_menu.html"):
        assert "Sesión iniciada" not in (ROOT / path).read_text(encoding="utf-8"), path
    assert "mountUserButton" not in JS and "[data-auth-user]" not in JS


def test_sign_out_goes_back_to_auth():
    assert "clerk.signOut({ redirectUrl: AUTH_PATH })" in JS
    assert JS.count("guard.clear()") >= 2                                         # sign-out and signed-out load reset the guard


def test_auth_scripts_are_loaded_only_when_clerk_is_configured(auth_app):
    html = auth_app.test_client().get("/auth").get_data(as_text=True)
    assert "clerk.browser.js" in html and "js/auth.js" in html
    assert 'data-clerk-publishable-key="pk_test_' in html and "sk_test" not in html


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_auth_js_parses():
    subprocess.run(["node", "--check", str(ROOT / "static/js/auth.js")], check=True)


def test_themes_and_responsive_structure_are_kept():
    css = (ROOT / "static/css/app.css").read_text(encoding="utf-8")
    assert ".auth-page { min-height: 100vh;" in css and "width: min(100%, 560px)" in css       # responsive auth shell
    block = css[css.index(".auth-panel h2"):css.index(".auth-status:empty")]
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(", block)                                  # theme tokens only (Snow/Space/Auto)

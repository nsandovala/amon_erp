"""F2.4 product UX: context switching, admin IA, Clerk identity layer, account/session.

Clerk is always mocked: an autouse fixture makes any un-mocked directory call fail
closed instead of reaching the network.
"""
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from models import db_session
from models.branch import Branch
from models.membership import Membership
from models.organization import Organization
from services import clerk_directory
from services.clerk_directory import ClerkDirectoryError, find_user_id_by_email, identities_for

from test_auth import auth_app, signed_token, signing_key, verified_client  # noqa: F401  (shared auth fixtures)

ROOT = Path(__file__).parents[1]
LONG_ID = "user_2abcdefghijklmnopqrstuv"


@pytest.fixture(autouse=True)
def no_real_clerk():
    with patch.object(clerk_directory, "_client", side_effect=ClerkDirectoryError("blocked in tests")) as blocked:
        yield blocked


def fake_user(user_id, first=None, last=None, email=None, image=None, username=None):
    emails = [SimpleNamespace(id="idn_1", email_address=email)] if email else []
    return SimpleNamespace(
        id=user_id, first_name=first, last_name=last, username=username,
        email_addresses=emails, primary_email_address_id="idn_1" if email else None,
        image_url=image, has_image=bool(image),
    )


def fake_client(users=None, error=None):
    def list_users(request, timeout_ms=None):
        if error:
            raise error
        return users(request) if callable(users) else users
    return SimpleNamespace(users=SimpleNamespace(list=list_users))


def mock_clerk(users=None, error=None):
    return patch.object(clerk_directory, "_client", return_value=fake_client(users, error))


def get(client, key, path, **kwargs):
    client.set_cookie("__session", signed_token(key))
    return client.get(path, **kwargs)


def set_role(app, role):
    with app.app_context():
        membership = db_session.query(Membership).filter_by(clerk_user_id="user_allowed").one()
        membership.role = role
        db_session.commit()


def add_second_org(app):
    with app.app_context():
        organization = Organization(name="2MUCH", slug="2much", entity_type="company")
        db_session.add(organization); db_session.flush()
        db_session.add_all([
            Branch(organization_id=organization.id, name="Principal 2M", slug="principal"),
            Membership(organization_id=organization.id, clerk_user_id="user_allowed", role="owner"),
        ])
        db_session.commit()
        return organization.id, db_session.query(Branch).filter_by(organization_id=organization.id).one().id


def select_context(client, key, organization_id, branch_id):
    with client.session_transaction() as session:
        session["csrf_token"] = "t"
    client.set_cookie("__session", signed_token(key))
    return client.post("/contexto/", data={"csrf_token": "t", "organization_id": organization_id, "branch_id": branch_id})


# ---------- 1. Cambiar contexto ----------

def test_single_context_shows_info_without_false_switch_action(verified_client, signing_key):
    html = get(verified_client, signing_key, "/").get_data(as_text=True)
    assert 'class="organization-card"' in html
    assert "organization-switch" not in html
    assert "force=1" not in html
    assert "Cambiar organización o sucursal" not in html
    assert "topbar-context-current" in html


def test_single_context_selector_still_reachable_explicitly(verified_client, signing_key):
    assert get(verified_client, signing_key, "/contexto/").status_code == 302
    forced = get(verified_client, signing_key, "/contexto/?force=1")
    assert forced.status_code == 200
    assert 'name="organization_id"' in forced.get_data(as_text=True)


def test_multi_context_exposes_switch_and_explicit_selector(auth_app, verified_client, signing_key):
    organization_id, branch_id = add_second_org(auth_app)
    assert select_context(verified_client, signing_key, organization_id, branch_id).status_code == 302
    html = get(verified_client, signing_key, "/").get_data(as_text=True)
    assert "organization-switch" in html and "/contexto/?force=1" in html
    assert get(verified_client, signing_key, "/contexto/").status_code == 302
    forced = get(verified_client, signing_key, "/contexto/?force=1")
    assert forced.status_code == 200
    body = forced.get_data(as_text=True)
    assert "2MUCH" in body and "The Best Burger" in body


def test_multiple_branches_in_one_organization_is_a_real_choice(auth_app, verified_client, signing_key):
    with auth_app.app_context():
        organization = db_session.query(Organization).one()
        db_session.add(Branch(organization_id=organization.id, name="Segunda", slug="segunda"))
        db_session.commit()
        branch_id = db_session.query(Branch).filter_by(slug="segunda").one().id
        organization_id = organization.id
    select_context(verified_client, signing_key, organization_id, branch_id)
    assert "/contexto/?force=1" in get(verified_client, signing_key, "/").get_data(as_text=True)


def test_force_does_not_bypass_server_side_validation(auth_app, verified_client, signing_key):
    organization_id, branch_id = add_second_org(auth_app)
    with auth_app.app_context():
        foreign = Organization(name="Ajena", slug="ajena", entity_type="company")
        db_session.add(foreign); db_session.flush()
        foreign_branch = Branch(organization_id=foreign.id, name="X", slug="x")
        db_session.add(foreign_branch); db_session.commit()
        foreign_ids = (foreign.id, foreign_branch.id)
    assert select_context(verified_client, signing_key, *foreign_ids).status_code == 403
    assert select_context(verified_client, signing_key, organization_id, foreign_ids[1]).status_code == 403


# ---------- 2. Sidebar IA ----------

def test_sidebar_groups_and_admin_is_a_real_nav_item(verified_client, signing_key):
    html = get(verified_client, signing_key, "/").get_data(as_text=True)
    assert html.index(">Operación</p>") < html.index(">Gestión</p>") < html.index(">Sistema</p>")
    admin_link = re.search(r'<a class="[^"]*"[^>]*href="/administracion/">(.*?)</a>', html, re.S)
    assert admin_link and "<svg" in admin_link.group(1) and "<span>Administración</span>" in admin_link.group(1)
    gestion = html[html.index(">Gestión</p>"):html.index(">Sistema</p>")]
    assert "Administración" in gestion and "Papelera" not in gestion
    assert "Papelera" in html[html.index(">Sistema</p>"):]


def test_admin_nav_item_marks_active_page(verified_client, signing_key):
    html = get(verified_client, signing_key, "/administracion/").get_data(as_text=True)
    assert re.search(r'class="active"\s+aria-current="page"\s+href="/administracion/"', html)


@pytest.mark.parametrize("role", ["operator", "accountant_readonly"])
def test_non_admin_roles_get_no_gestion_group_or_admin_access(auth_app, verified_client, signing_key, role):
    set_role(auth_app, role)
    html = get(verified_client, signing_key, "/").get_data(as_text=True)
    assert ">Gestión</p>" not in html and "/administracion/" not in html
    assert get(verified_client, signing_key, "/administracion/").status_code == 403


# ---------- 3. Administración / RBAC ----------

def test_admin_structure_has_three_sections_and_compact_meta(verified_client, signing_key):
    html = get(verified_client, signing_key, "/administracion/").get_data(as_text=True)
    tabs = re.search(r'<nav class="admin-tabs".*?</nav>', html, re.S).group(0)
    assert [t for t in re.findall(r"<a [^>]*>(.*?)</a>", tabs)] == ["Empresa", "Sucursales", "Equipo y permisos"]
    assert 'class="admin-meta"' in html and "Tu rol: Propietario" in html
    assert "1 miembro activo" in html and "1 sucursal activa" in html
    assert "kpi" not in html.lower().split("<main")[1]


def test_owner_sees_every_f23_operation(verified_client, signing_key):
    html = get(verified_client, signing_key, "/administracion/").get_data(as_text=True)
    for action in ("/administracion/organizacion", "/administracion/sucursales", "/administracion/accesos"):
        assert f'action="{action}"' in html
    assert "/archivar" in html and "/rol" in html and "/estado" in html


def test_manager_is_read_only_in_admin(auth_app, verified_client, signing_key):
    set_role(auth_app, "manager")
    response = get(verified_client, signing_key, "/administracion/")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "<form method=\"post\" action=\"/administracion" not in html
    assert 'name="email"' not in html and "Agregar sucursal" not in html and "Archivar" not in html
    assert "Cambiar rol" not in html


@pytest.mark.parametrize("role", ["manager", "operator", "accountant_readonly"])
@pytest.mark.parametrize("path,data", [
    ("/administracion/accesos", {"email": "x@y.cl", "role": "owner"}),
    ("/administracion/sucursales", {"name": "N", "slug": "n"}),
    ("/administracion/organizacion", {"name": "N", "entity_type": "company"}),
])
def test_non_owner_cannot_mutate(auth_app, verified_client, signing_key, role, path, data):
    set_role(auth_app, role)
    with verified_client.session_transaction() as session:
        session["csrf_token"] = "t"
    verified_client.set_cookie("__session", signed_token(signing_key))
    assert verified_client.post(path, data={"csrf_token": "t", **data}).status_code == 403


# ---------- 4. Sucursales: sin tabla ni overflow estructural ----------

def test_branches_use_rows_not_a_scrolling_table(verified_client, signing_key):
    html = get(verified_client, signing_key, "/administracion/").get_data(as_text=True)
    section = html[html.index('id="sucursales"'):html.index('id="nueva-sucursal"')]
    assert "<table" not in section and "table-wrap" not in section
    assert 'class="branch-list"' in section and 'class="branch-row"' in section
    assert ">Editar</a>" in section and ">Archivar</button>" in section
    assert 'id="nueva-sucursal"' in html and "Agregar sucursal" in html


def test_last_active_branch_cannot_be_archived_from_ui(verified_client, signing_key):
    html = get(verified_client, signing_key, "/administracion/").get_data(as_text=True)
    assert re.search(r"<button[^>]*disabled[^>]*>Archivar</button>", html)


def test_branch_edit_is_inline_without_wide_forms(verified_client, signing_key):
    html = get(verified_client, signing_key, "/administracion/?editar=1").get_data(as_text=True)
    assert 'class="branch-edit"' in html and "Cancelar" in html


def test_branch_layout_css_contract_has_no_horizontal_overflow():
    css = (ROOT / "static/css/app.css").read_text(encoding="utf-8")
    assert re.search(r"\.branch-row \{[^}]*grid-template-columns: minmax\(0, 1fr\) auto auto", css)
    assert re.search(r"\.admin-stack \{[^}]*min-width: 0", css)
    assert re.search(r"@media \(max-width: 760px\) \{[^@]*\.branch-row \{ grid-template-columns: minmax\(0, 1fr\) auto; \}", css, re.S)
    assert not re.search(r"\.(branch|member)-[a-z-]+ \{[^}]*min-width: \d{3,}px", css)
    assert not re.search(r"\.(branch|member)-[a-z-]+ \{[^}]*white-space: nowrap", css)


# ---------- 5. Equipo y permisos / Clerk ----------

def add_member(app, user_id=LONG_ID, role="operator"):
    with app.app_context():
        organization = db_session.query(Organization).first()
        db_session.add(Membership(organization_id=organization.id, clerk_user_id=user_id, role=role))
        db_session.commit()


def without_technical_details(html):
    return re.sub(r'<details class="member-tech">.*?</details>', "", html, flags=re.S)


def test_team_shows_clerk_identity_and_not_raw_id_as_primary(auth_app, verified_client, signing_key):
    add_member(auth_app)
    users = [fake_user("user_allowed", "Ana", "Pérez", "ana@empresa.cl", "https://img.clerk.test/a.png"),
             fake_user(LONG_ID, email="solo-email@empresa.cl")]
    with mock_clerk(users):
        html = get(verified_client, signing_key, "/administracion/").get_data(as_text=True)
    assert '<strong class="member-name">Ana Pérez</strong>' in html
    assert 'ana@empresa.cl' in html and "https://img.clerk.test/a.png" in html
    assert '<strong class="member-name">solo-email@empresa.cl</strong>' in html
    assert "Operador" in html and "Propietario" in html
    visible = without_technical_details(html)
    assert "user_allowed" not in visible and LONG_ID not in visible
    assert re.search(r'<details class="member-tech"><summary>Detalle técnico</summary><code>user_allowed</code>', html)
    assert "<details class=\"member-tech\" open" not in html


@pytest.mark.parametrize("failure", [RuntimeError("clerk down"), ClerkDirectoryError("x")])
def test_clerk_failure_degrades_gracefully_without_500(auth_app, verified_client, signing_key, failure):
    add_member(auth_app)
    with mock_clerk(error=failure):
        response = get(verified_client, signing_key, "/administracion/")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert '<strong class="member-name">Usuario</strong>' in html
    assert "ID user_2abc…stuv" in html
    assert LONG_ID not in without_technical_details(html)
    assert "clerk down" not in html


def test_unconfigured_clerk_also_falls_back(verified_client, signing_key):
    response = get(verified_client, signing_key, "/administracion/")
    assert response.status_code == 200 and "Usuario" in response.get_data(as_text=True)


def test_identities_for_parses_nullable_fields_and_never_raises(auth_app):
    with auth_app.app_context():
        users = [fake_user("u1", None, None, "a@b.cl"), fake_user("u2", "Solo", None, None, username="x"), fake_user("u3", username="nick")]
        with mock_clerk(users):
            found = identities_for(["u1", "u2", "u3", None, "u1"])
        assert found["u1"].name is None and found["u1"].email == "a@b.cl" and found["u1"].image_url is None
        assert found["u2"].name == "Solo" and found["u3"].name == "nick"
        with mock_clerk(error=RuntimeError("boom")):
            assert identities_for(["u1"]) == {}
        assert identities_for([]) == {}


def test_clerk_directory_requests_only_requested_ids(auth_app):
    seen = []
    with auth_app.app_context(), mock_clerk(lambda request: seen.append(request) or []):
        identities_for(["b", "a"])
    assert seen == [{"user_id": ["a", "b"], "limit": 2}]


def test_find_user_id_by_email_exact_and_unambiguous(auth_app):
    with auth_app.app_context():
        with mock_clerk([fake_user("user_x", email="Ana@Empresa.cl")]):
            assert find_user_id_by_email("  ana@empresa.CL ") == "user_x"
        with mock_clerk([fake_user("user_x", email="otra@empresa.cl")]):
            assert find_user_id_by_email("ana@empresa.cl") is None
        with mock_clerk([fake_user("user_x", email="a@b.cl"), fake_user("user_y", email="a@b.cl")]):
            assert find_user_id_by_email("a@b.cl") is None
        with mock_clerk([]):
            assert find_user_id_by_email("nadie@b.cl") is None
        assert find_user_id_by_email("sin-arroba") is None
        with mock_clerk(error=RuntimeError("secret detail")):
            with pytest.raises(ClerkDirectoryError) as caught:
                find_user_id_by_email("a@b.cl")
        assert "secret detail" not in str(caught.value)


def post_access(client, key, **data):
    with client.session_transaction() as session:
        session["csrf_token"] = "t"
    client.set_cookie("__session", signed_token(key))
    return client.post("/administracion/accesos", data={"csrf_token": "t", **data})


def membership_ids(app):
    with app.app_context():
        return sorted(m.clerk_user_id for m in db_session.query(Membership).all())


def test_add_access_by_email_creates_local_membership_only_when_clerk_user_exists(auth_app, verified_client, signing_key):
    with mock_clerk([fake_user(LONG_ID, email="nuevo@empresa.cl")]):
        response = post_access(verified_client, signing_key, email="nuevo@empresa.cl", role="operator")
    assert response.status_code == 302
    assert LONG_ID in membership_ids(auth_app)
    with auth_app.app_context():
        created = db_session.query(Membership).filter_by(clerk_user_id=LONG_ID).one()
        assert (created.role, created.status) == ("operator", "active")


def test_add_access_unknown_email_does_not_provision(auth_app, verified_client, signing_key):
    before = membership_ids(auth_app)
    with mock_clerk([]):
        response = post_access(verified_client, signing_key, email="nadie@empresa.cl", role="owner")
    assert response.status_code == 302 and membership_ids(auth_app) == before


def test_add_access_clerk_failure_is_not_a_500(auth_app, verified_client, signing_key):
    before = membership_ids(auth_app)
    with mock_clerk(error=RuntimeError("down")):
        response = post_access(verified_client, signing_key, email="a@b.cl", role="operator")
    assert response.status_code == 302 and membership_ids(auth_app) == before


def test_add_access_ignores_raw_clerk_ids_and_invalid_roles(auth_app, verified_client, signing_key):
    before = membership_ids(auth_app)
    with mock_clerk([]):
        post_access(verified_client, signing_key, clerk_user_id=LONG_ID, role="operator")
        assert post_access(verified_client, signing_key, email="a@b.cl", role="superadmin").status_code == 400
    assert membership_ids(auth_app) == before


def test_add_access_form_asks_for_email_not_clerk_id(verified_client, signing_key):
    html = get(verified_client, signing_key, "/administracion/").get_data(as_text=True)
    assert 'type="email" name="email"' in html
    assert 'name="clerk_user_id"' not in html and "Clerk user ID" not in html


def test_role_still_comes_from_local_membership_not_clerk(auth_app, verified_client, signing_key):
    set_role(auth_app, "operator")
    users = [fake_user("user_allowed", "Ana", "Pérez", "ana@empresa.cl")]
    users[0].public_metadata = {"role": "owner"}
    with mock_clerk(users):
        assert get(verified_client, signing_key, "/administracion/").status_code == 403


# ---------- 6. Cuenta / sesión ----------

def test_shell_has_account_menu_with_signout_for_authenticated_user(verified_client, signing_key):
    html = get(verified_client, signing_key, "/").get_data(as_text=True)
    assert "data-account-menu" in html
    assert "data-auth-account" in html and ">Mi cuenta</button>" in html
    assert "Mi acceso AMON ERP" in html
    assert re.search(r"<button[^>]*data-auth-sign-out[^>]*>Cerrar sesión</button>", html)
    access = html[html.index('aria-label="Mi acceso AMON ERP"'):]
    assert "The Best Burger" in access and "Propietario" in access


def test_signout_uses_official_clerk_api_without_custom_credentials():
    js = (ROOT / "static/js/auth.js").read_text(encoding="utf-8")
    assert "clerk.signOut({ redirectUrl: '/auth' })" in js
    assert "clerk.openUserProfile()" in js
    assert "document.cookie" not in js and "localStorage" not in js


def test_auth_page_semantics(auth_app, verified_client, signing_key):
    anonymous = auth_app.test_client().get("/auth").get_data(as_text=True)
    assert "Acceso a AMON ERP" in anonymous and "data-auth-sign-out" not in anonymous
    denied = get(verified_client, signing_key, "/auth")
    # authorized identities are sent straight into the ERP
    assert denied.status_code == 302 and denied.location == "/"
    stranger = verified_client.get("/auth", headers={"Authorization": "Bearer " + signed_token(signing_key, sub="user_new")})
    html = stranger.get_data(as_text=True)
    assert stranger.status_code == 200 and "Tu cuenta no tiene acceso a AMON ERP." in html
    assert "data-auth-sign-out" in html and "user_new" not in html
    template = (ROOT / "templates/auth/access.html").read_text(encoding="utf-8")
    assert "Ir al resumen" not in template and "Bienvenido de nuevo" not in template


# ---------- Invariante: última sucursal activa (server-side) ----------

def post_archive(client, key, branch_id):
    with client.session_transaction() as session:
        session["csrf_token"] = "t"
    client.set_cookie("__session", signed_token(key))
    return client.post(f"/administracion/sucursales/{branch_id}/archivar", data={"csrf_token": "t"})


def branch_state(app, branch_id):
    from models.audit_log import AuditLog
    with app.app_context():
        db_session.expire_all()
        return db_session.get(Branch, branch_id).status, db_session.query(AuditLog).filter_by(action="branch.archived").count()


def only_branch_id(app):
    with app.app_context():
        return db_session.query(Branch).one().id


def test_route_rejects_archiving_last_active_branch(auth_app, verified_client, signing_key):
    branch_id = only_branch_id(auth_app)
    response = post_archive(verified_client, signing_key, branch_id)
    assert response.status_code == 302
    assert branch_state(auth_app, branch_id) == ("active", 0)


def test_route_archives_when_another_active_branch_remains(auth_app, verified_client, signing_key):
    with auth_app.app_context():
        organization = db_session.query(Organization).one()
        db_session.add(Branch(organization_id=organization.id, name="Segunda", slug="segunda"))
        db_session.commit()
        first_id = db_session.query(Branch).filter_by(slug="segunda").one().id
        second_id = db_session.query(Branch).filter(Branch.slug != "segunda").one().id
    organization_id = auth_app_org_id(auth_app, "The Best Burger")
    select_context(verified_client, signing_key, organization_id, second_id)
    assert post_archive(verified_client, signing_key, first_id).status_code == 302
    assert branch_state(auth_app, first_id) == ("archived", 1)
    post_archive(verified_client, signing_key, second_id)
    assert branch_state(auth_app, second_id) == ("active", 1)


def test_other_organization_branch_cannot_be_archived_or_satisfy_invariant(auth_app, verified_client, signing_key):
    _organization_id, foreign_branch_id = add_second_org(auth_app)
    own_id = only_branch_id_for(auth_app, "The Best Burger")
    select_context(verified_client, signing_key, auth_app_org_id(auth_app, "The Best Burger"), own_id)
    assert post_archive(verified_client, signing_key, own_id).status_code == 302
    assert branch_state(auth_app, own_id) == ("active", 0)  # foreign branch doesn't count
    assert post_archive(verified_client, signing_key, foreign_branch_id).status_code == 404
    assert branch_state(auth_app, foreign_branch_id) == ("active", 0)


@pytest.mark.parametrize("role", ["manager", "operator", "accountant_readonly"])
def test_non_owner_cannot_archive_branch(auth_app, verified_client, signing_key, role):
    branch_id = only_branch_id(auth_app)
    set_role(auth_app, role)
    assert post_archive(verified_client, signing_key, branch_id).status_code == 403
    assert branch_state(auth_app, branch_id) == ("active", 0)


def only_branch_id_for(app, organization_name):
    with app.app_context():
        organization = db_session.query(Organization).filter_by(name=organization_name).one()
        return db_session.query(Branch).filter_by(organization_id=organization.id).one().id


def auth_app_org_id(app, organization_name):
    with app.app_context():
        return db_session.query(Organization).filter_by(name=organization_name).one().id

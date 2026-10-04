import re
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_shell_separates_product_and_active_organization(app):
    from flask import g
    from models import db_session
    from models.branch import Branch
    from models.membership import Membership
    from models.organization import Organization
    from services.tenancy import resolve_request_tenant

    with app.app_context():
        organization = Organization(name="Organización de prueba", slug="org-prueba", entity_type="company")
        db_session.add(organization); db_session.flush()
        branch = Branch(organization_id=organization.id, name="Sucursal real", slug="real")
        db_session.add_all([branch, Membership(organization_id=organization.id, clerk_user_id="user_shell", role="owner")])
        db_session.commit()

    @app.before_request
    def install_shell_context():
        g.user_id = "user_shell"
        resolve_request_tenant(g.user_id)
        g.tenant_enforced = True

    html = app.test_client().get("/").get_data(as_text=True)

    assert "AMON ERP" in html
    assert 'class="organization-card"' in html
    assert 'aria-label="Organización activa"' in html
    assert "Organización de prueba" in html
    assert "Sucursal real" in html
    assert "The Best Burger" not in html
    assert "Organización activa" in html
    assert "The Best Burger" not in (ROOT / "templates" / "base.html").read_text(encoding="utf-8")


def test_shell_groups_current_navigation_without_future_modules(client):
    html = client.get("/").get_data(as_text=True)

    assert 'class="nav-group"' in html
    assert ">Operación</p>" in html
    assert ">Sistema</p>" in html
    assert ">Resumen</span>" in html
    for unavailable_module in ("Inventario", "CRM", "Recursos humanos", "HEO"):
        assert unavailable_module not in html


def test_theme_selector_exposes_auto_light_and_dark_preferences(client):
    html = client.get("/").get_data(as_text=True)

    assert 'role="group" aria-label="Apariencia" data-theme-control' in html
    assert 'data-theme-value="auto"' in html
    assert 'data-theme-value="light"' in html
    assert 'data-theme-value="dark"' in html


def test_theme_preference_has_no_flash_and_persistent_hooks():
    bootstrap = (ROOT / "templates/partials/theme_bootstrap.html").read_text(encoding="utf-8")
    javascript = (ROOT / "static/js/app.js").read_text(encoding="utf-8")

    assert "amon-erp-theme" in bootstrap
    assert "localStorage.getItem" in bootstrap
    assert "document.documentElement.dataset.theme" in bootstrap
    assert "localStorage.setItem" in javascript
    assert 'matchMedia("(prefers-color-scheme: dark)")' in javascript
    assert "rebuildCharts()" in javascript


def test_design_system_has_both_themes_and_semantic_tokens():
    css = (ROOT / "static/css/app.css").read_text(encoding="utf-8")

    assert 'html[data-theme="light"]' in css
    assert 'html[data-theme="dark"]' in css
    assert 'html[data-theme="auto"]' in css
    for token in (
        "--app-bg",
        "--atmospheric-bg",
        "--surface-elevated",
        "--glass-surface",
        "--sidebar",
        "--border-strong",
        "--text-secondary",
        "--navy",
        "--sand",
        "--green",
        "--red",
        "--cyan",
        "--amber",
        "--focus-ring",
    ):
        assert token in css


def test_shell_has_no_duplicate_static_ids(client):
    html = client.get("/").get_data(as_text=True)
    ids = re.findall(r'\bid="([^"]+)"', html)

    assert len(ids) == len(set(ids))


def test_responsive_and_print_foundations_are_present(client):
    sales_template = (ROOT / "templates/sales/index.html").read_text(encoding="utf-8")
    css = (ROOT / "static/css/app.css").read_text(encoding="utf-8")

    assert 'class="table-wrap table-scroll table-scroll-history responsive-table"' in sales_template
    assert 'class="mobile-record-card"' in sales_template
    assert "@media (max-width: 900px)" in css
    assert "@media (max-width: 650px)" in css
    assert "@media (max-width: 430px)" in css
    assert "@media print" in css
    assert "@page" in css
    assert "prefers-reduced-motion: reduce" in css


def test_executive_compositions_have_stable_layout_hooks():
    dashboard = (ROOT / "templates/dashboard.html").read_text(encoding="utf-8")
    sessions = (ROOT / "templates/sessions/index.html").read_text(encoding="utf-8")
    expenses = (ROOT / "templates/expenses/index.html").read_text(encoding="utf-8")
    css = (ROOT / "static/css/app.css").read_text(encoding="utf-8")

    assert 'class="dashboard-context-side"' in dashboard
    assert 'class="session-operation-grid"' in sessions
    assert "session-current-card" in sessions
    assert 'class="expense-top-grid"' in expenses
    assert ".session-operation-grid { grid-template-columns: repeat(2" in css
    assert ".expense-top-grid { grid-template-columns: minmax(0, 1.85fr)" in css
    assert ".sales-top-grid { grid-template-columns: minmax(0, 1.85fr)" in css


def test_density_pass_uses_bounded_data_regions():
    sales = (ROOT / "templates/sales/index.html").read_text(encoding="utf-8")
    dashboard = (ROOT / "templates/dashboard.html").read_text(encoding="utf-8")
    css = (ROOT / "static/css/app.css").read_text(encoding="utf-8")

    assert 'class="sales-top-grid"' in sales
    assert 'table-scroll table-scroll-history' in sales
    assert 'movement-list movement-list-scroll' in dashboard
    assert 'table-scroll table-scroll-monthly' in dashboard
    assert '.table-scroll-history { max-height: 420px; }' in css
    assert '.movement-list-scroll { max-height: 260px;' in css
    assert '.table-scroll thead th { position: sticky;' in css


def test_financial_and_action_controls_remain_available(client, app):
    dashboard = client.get("/").get_data(as_text=True)
    sales = client.get("/ventas/").get_data(as_text=True)

    assert "Agregar venta" in dashboard
    assert "Agregar gasto" in dashboard
    assert "Gestionar jornada" in dashboard
    assert "Ventas" in dashboard
    assert "Gastos operacionales" in dashboard
    assert "Ganancia operativa" in dashboard
    assert "Margen operacional" in dashboard
    assert 'name="csrf_token"' in sales
    assert 'name="occurred_at_date"' in sales
    assert 'name="occurred_at_time"' in sales

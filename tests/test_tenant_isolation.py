from datetime import datetime

import pytest
from flask import g, request

from models import db_session
from models.branch import Branch
from models.expense import Expense
from models.audit_log import AuditLog
from models.membership import Membership
from models.organization import Organization
from models.sale import Sale
from models.work_session import WorkSession
from services.tenancy import resolve_request_tenant
from sqlalchemy.exc import IntegrityError


@pytest.fixture
def tenant_setup(app):
    with app.app_context():
        organization_a = Organization(name="The Best Burger", slug="the-best-burger", entity_type="company")
        organization_b = Organization(name="2MUCH", slug="2much", entity_type="company")
        db_session.add_all([organization_a, organization_b])
        db_session.flush()
        branch_a = Branch(organization_id=organization_a.id, name="Principal", slug="principal")
        branch_b = Branch(organization_id=organization_b.id, name="Principal", slug="principal")
        db_session.add_all([branch_a, branch_b])
        db_session.flush()
        db_session.add_all([
            Membership(organization_id=organization_a.id, clerk_user_id="user_a", role="owner"),
            Membership(organization_id=organization_b.id, clerk_user_id="user_b", role="owner"),
        ])
        organization_a_id = organization_a.id
        branch_a_id = branch_a.id
        organization_b_id = organization_b.id
        branch_b_id = branch_b.id
        db_session.commit()

    @app.before_request
    def install_resolved_test_tenant():
        user_id = request.headers.get("X-Test-User")
        if user_id:
            g.user_id = user_id
            resolve_request_tenant(user_id)
            g.tenant_enforced = True

    return organization_a_id, branch_a_id, organization_b_id, branch_b_id


@pytest.fixture
def tenant_client(app, tenant_setup):
    with app.test_client() as client:
        with client.session_transaction() as browser_session:
            browser_session["csrf_token"] = "test-token"
        yield client


def _sale(organization_id, branch_id, description):
    return Sale(
        organization_id=organization_id,
        branch_id=branch_id,
        occurred_at=datetime(2026, 10, 3, 12),
        amount=10000,
        payment_method="cash",
        channel="food_truck",
        description=description,
    )


def _expense(organization_id, branch_id, description):
    return Expense(
        organization_id=organization_id,
        branch_id=branch_id,
        occurred_at=datetime(2026, 10, 3, 13),
        amount=3000,
        category="Insumos",
        expense_type="operational",
        payment_method="cash",
        description=description,
    )


def _session(organization_id, branch_id, status="closed"):
    return WorkSession(
        organization_id=organization_id,
        branch_id=branch_id,
        business_date=datetime(2026, 10, 3).date(),
        opened_at=datetime(2026, 10, 3, 10),
        closed_at=datetime(2026, 10, 3, 18) if status == "closed" else None,
        opening_cash=0,
        closing_cash=0 if status == "closed" else None,
        closing_cash_counted=0 if status == "closed" else None,
        status=status,
    )


def test_a_requests_are_scoped_and_b_guessed_resources_return_404(tenant_client, tenant_setup):
    organization_a_id, branch_a_id, organization_b_id, branch_b_id = tenant_setup
    with db_session.begin():
        sale_a = _sale(organization_a_id, branch_a_id, "Venta A")
        sale_b = _sale(organization_b_id, branch_b_id, "Venta B secreta")
        expense_b = _expense(organization_b_id, branch_b_id, "Gasto B secreto")
        session_b = _session(organization_b_id, branch_b_id)
        db_session.add_all([sale_a, sale_b, expense_b, session_b])
    headers = {"X-Test-User": "user_a"}

    sales = tenant_client.get("/ventas/", headers=headers)
    assert sales.status_code == 200
    assert b"Venta A" in sales.data
    assert b"Venta B secreta" not in sales.data
    assert tenant_client.get(f"/ventas/{sale_b.id}", headers=headers).status_code == 404
    assert tenant_client.get(f"/ventas/{sale_b.id}/editar", headers=headers).status_code == 404
    assert tenant_client.get(f"/gastos/{expense_b.id}", headers=headers).status_code == 404
    assert tenant_client.get(f"/gastos/{expense_b.id}/editar", headers=headers).status_code == 404
    assert tenant_client.get(f"/jornadas/{session_b.id}/editar", headers=headers).status_code == 404


def test_a_cannot_mutate_or_restore_b_records(tenant_client, tenant_setup):
    _organization_a_id, _branch_a_id, organization_b_id, branch_b_id = tenant_setup
    with db_session.begin():
        sale_b = _sale(organization_b_id, branch_b_id, "Venta B")
        expense_b = _expense(organization_b_id, branch_b_id, "Gasto B")
        session_b = _session(organization_b_id, branch_b_id)
        db_session.add_all([sale_b, expense_b, session_b])
    headers = {"X-Test-User": "user_a"}
    form = {"csrf_token": "test-token"}

    for path in (
        f"/ventas/{sale_b.id}/archivar",
        f"/ventas/{sale_b.id}/eliminar",
        f"/ventas/{sale_b.id}/restaurar",
        f"/gastos/{expense_b.id}/archivar",
        f"/gastos/{expense_b.id}/eliminar",
        f"/gastos/{expense_b.id}/restaurar",
        f"/jornadas/{session_b.id}/cerrar",
        f"/jornadas/{session_b.id}/archivar",
        f"/jornadas/{session_b.id}/eliminar",
        f"/jornadas/{session_b.id}/restaurar",
    ):
        assert tenant_client.post(path, data=form, headers=headers).status_code == 404
    assert tenant_client.get(f"/jornadas/{session_b.id}/asociar-movimientos", headers=headers).status_code == 404
    assert db_session.get(Sale, sale_b.id).status == "active"
    assert db_session.get(Expense, expense_b.id).status == "active"


def test_history_trash_csv_dashboard_and_monthly_summary_exclude_other_tenant(tenant_client, tenant_setup):
    organization_a_id, branch_a_id, organization_b_id, branch_b_id = tenant_setup
    with db_session.begin():
        sale_a = _sale(organization_a_id, branch_a_id, "Visible A")
        sale_b = _sale(organization_b_id, branch_b_id, "Oculta B")
        sale_b.deleted_at = datetime(2026, 10, 3, 15)
        db_session.add_all([sale_a, sale_b, _expense(organization_b_id, branch_b_id, "Gasto B")])
    headers = {"X-Test-User": "user_a"}

    for path in ("/", "/historial/", "/historial/exportar.csv", "/papelera/", "/monthly-summary.csv?year=2026"):
        response = tenant_client.get(path, headers=headers)
        assert response.status_code == 200
        assert b"Oculta B" not in response.data
        assert b"Gasto B" not in response.data
    assert b"Visible A" in tenant_client.get("/historial/", headers=headers).data


def test_new_financial_records_take_tenant_from_resolved_context(tenant_client, tenant_setup):
    organization_a_id, branch_a_id, _organization_b_id, _branch_b_id = tenant_setup
    headers = {"X-Test-User": "user_a"}
    form = {"csrf_token": "test-token"}
    sale_response = tenant_client.post("/ventas/", data={
        **form, "amount": "12000", "occurred_at_date": "03-10-2026", "occurred_at_time": "12:00",
        "payment_method": "cash", "channel": "food_truck",
    }, headers=headers)
    expense_response = tenant_client.post("/gastos/", data={
        **form, "amount": "4000", "occurred_at_date": "03-10-2026", "occurred_at_time": "13:00",
        "category": "Insumos", "expense_type": "operational", "payment_method": "cash", "description": "Insumos A",
    }, headers=headers)

    assert sale_response.status_code == 302
    assert expense_response.status_code == 302
    sale = db_session.query(Sale).one()
    expense = db_session.query(Expense).one()
    assert (sale.organization_id, sale.branch_id) == (organization_a_id, branch_a_id)
    assert (expense.organization_id, expense.branch_id) == (organization_a_id, branch_a_id)


def test_open_sessions_are_unique_per_branch_not_globally(app, tenant_setup):
    organization_a_id, branch_a_id, organization_b_id, branch_b_id = tenant_setup
    db_session.add_all([_session(organization_a_id, branch_a_id, status="open"), _session(organization_b_id, branch_b_id, status="open")])
    db_session.commit()
    db_session.add(_session(organization_a_id, branch_a_id, status="open"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_tenant_grant_is_explicit_and_idempotent(app):
    with app.app_context():
        db_session.add(Organization(name="The Best Burger", slug="the-best-burger", entity_type="company"))
        db_session.commit()

    runner = app.test_cli_runner()
    args = ["tenant-grant", "--user-id", "user_admin", "--organization", "the-best-burger", "--role", "owner"]
    assert runner.invoke(args=args).exit_code == 0
    duplicate = runner.invoke(args=args)
    assert duplicate.exit_code == 0
    assert "ya existe" in duplicate.output
    listed = runner.invoke(args=["tenant-memberships", "--organization", "the-best-burger"])
    assert listed.exit_code == 0
    assert "user_admin\towner\tactive" in listed.output
    with app.app_context():
        assert db_session.query(Membership).filter(Membership.clerk_user_id == "user_admin").count() == 1


def test_audit_uses_resolved_actor_and_tenant(tenant_client, tenant_setup):
    organization_a_id, branch_a_id, _organization_b_id, _branch_b_id = tenant_setup
    with db_session.begin():
        work_session = _session(organization_a_id, branch_a_id)
        db_session.add(work_session)
    response = tenant_client.post(f"/jornadas/{work_session.id}/editar", data={
        "csrf_token": "test-token",
        "opened_at_date": "03-10-2026",
        "opened_at_time": "10:00",
        "closed_at_date": "03-10-2026",
        "closed_at_time": "18:00",
        "opening_cash": "0",
        "closing_cash_counted": "0",
        "notes": "",
        "closing_notes": "",
    }, headers={"X-Test-User": "user_a"})
    assert response.status_code == 302
    audit = db_session.query(AuditLog).filter(AuditLog.action == "edit_work_session").one()
    assert (audit.organization_id, audit.branch_id, audit.actor_user_id) == (organization_a_id, branch_a_id, "user_a")

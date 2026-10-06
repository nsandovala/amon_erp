from datetime import datetime

import pytest

from models import db_session, now_santiago
from models.audit_log import AuditLog
from models.expense import Expense
from models.sale import Sale
from models.work_session import WorkSession
from services.work_sessions import (
    associate_historical_movements,
    calculate_work_session_metrics,
    historical_movement_preview,
    session_balance_status,
)


def make_session(opening_cash=0, opened_at=None, closed_at=None, counted_cash=None, status=None):
    opened_at = opened_at or datetime(2026, 7, 10, 10)
    session = WorkSession(
        business_date=opened_at.date(),
        opened_at=opened_at,
        closed_at=closed_at,
        opening_cash=opening_cash,
        closing_cash_counted=counted_cash,
        closing_cash=counted_cash,
        status=status or ("closed" if closed_at else "open"),
    )
    db_session.add(session)
    db_session.flush()
    return session


def add_sale(session, amount, payment_method="cash", **overrides):
    sale = Sale(
        work_session_id=session.id if session else None,
        occurred_at=overrides.pop("occurred_at", datetime(2026, 7, 10, 12)),
        amount=amount,
        payment_method=payment_method,
        channel="food_truck",
        **overrides,
    )
    db_session.add(sale)
    return sale


def add_expense(session, amount, payment_method="cash", expense_type="operational", **overrides):
    expense = Expense(
        work_session_id=session.id if session else None,
        occurred_at=overrides.pop("occurred_at", datetime(2026, 7, 10, 13)),
        amount=amount,
        category="Insumos",
        expense_type=expense_type,
        payment_method=payment_method,
        description="Movimiento test",
        **overrides,
    )
    db_session.add(expense)
    return expense


@pytest.mark.parametrize("opening_cash", [0, 30000])
def test_opening_cash_values_are_included_even_when_zero(app, opening_cash):
    with app.app_context():
        session = make_session(opening_cash=opening_cash)
        db_session.commit()

        metrics = calculate_work_session_metrics(session)

        assert metrics.expected_cash == opening_cash


def test_acceptance_case_and_operational_profit(app):
    with app.app_context():
        session = make_session(
            opening_cash=30000,
            closed_at=datetime(2026, 7, 10, 20),
            counted_cash=139240,
        )
        add_sale(session, 159240, "cash")
        add_expense(session, 50000, "cash")
        db_session.commit()

        metrics = calculate_work_session_metrics(session)

        assert metrics.cash_sales == 159240
        assert metrics.cash_expenses == 50000
        assert metrics.expected_cash == 139240
        assert metrics.cash_difference == 0
        assert metrics.operational_profit == 109240
        assert session_balance_status(session, metrics) == ("balanced", "Cerrada y cuadrada")


def test_session_history_renders_associated_metrics(client, app):
    with app.app_context():
        session = make_session(
            opening_cash=30000,
            closed_at=datetime(2026, 7, 10, 20),
            counted_cash=139240,
        )
        add_sale(session, 159240, "cash")
        add_expense(session, 50000, "cash")
        db_session.commit()

    response = client.get("/jornadas/")

    assert response.status_code == 200
    assert b"$159.240" in response.data
    assert b"$50.000" in response.data
    assert b"$109.240" in response.data
    assert b"Cerrada y cuadrada" in response.data


def test_session_history_renders_exact_non_zero_financial_metrics(client, app):
    with app.app_context():
        session = make_session(
            opening_cash=20000,
            closed_at=datetime(2026, 7, 10, 20),
            counted_cash=27000,
        )
        add_sale(session, 10000, "cash")
        add_sale(session, 5000, "transfer")
        add_expense(session, 3000, "cash")
        add_expense(session, 7000, "cash", expense_type="investment")
        db_session.commit()

        metrics = calculate_work_session_metrics(session)
        assert metrics.total_sales == 15000
        assert metrics.cash_sales == 10000
        assert metrics.operational_expenses == 3000
        assert metrics.cash_expenses == 3000
        assert metrics.operational_profit == 12000
        assert metrics.expected_cash == 27000

    response = client.get("/jornadas/")

    assert response.status_code == 200
    for amount in (b"$20.000", b"$15.000", b"$3.000", b"$12.000", b"$27.000"):
        assert amount in response.data
    assert b"$7.000" not in response.data
    assert b"Efectivo inicial" in response.data
    assert b"Efectivo esperado al cierre" in response.data
    assert b"Efectivo contado" in response.data
    assert b"Diferencia de caja" in response.data


def test_transfer_sale_does_not_increase_physical_cash(app):
    with app.app_context():
        session = make_session(opening_cash=30000)
        add_sale(session, 45000, "transfer")
        db_session.commit()

        metrics = calculate_work_session_metrics(session)

        assert metrics.total_sales == 45000
        assert metrics.cash_sales == 0
        assert metrics.expected_cash == 30000


def test_cash_expense_decreases_cash_and_investment_is_excluded(app):
    with app.app_context():
        session = make_session(opening_cash=30000)
        add_expense(session, 5000, "cash")
        add_expense(session, 100000, "cash", expense_type="investment")
        db_session.commit()

        metrics = calculate_work_session_metrics(session)

        assert metrics.operational_expenses == 5000
        assert metrics.cash_expenses == 5000
        assert metrics.expected_cash == 25000


@pytest.mark.parametrize(
    ("counted_cash", "difference", "status_key"),
    [(40000, 0, "balanced"), (41000, 1000, "surplus"), (39000, -1000, "shortage")],
)
def test_closed_session_balance_states(app, counted_cash, difference, status_key):
    with app.app_context():
        session = make_session(
            opening_cash=30000,
            closed_at=datetime(2026, 7, 10, 20),
            counted_cash=counted_cash,
        )
        add_sale(session, 10000, "cash")
        db_session.commit()

        metrics = calculate_work_session_metrics(session)

        assert metrics.cash_difference == difference
        assert session_balance_status(session, metrics)[0] == status_key


def test_duration_crosses_midnight(app):
    with app.app_context():
        session = make_session(
            opened_at=datetime(2026, 7, 10, 23, 30),
            closed_at=datetime(2026, 7, 11, 1, 15),
            counted_cash=0,
        )
        db_session.commit()

        assert calculate_work_session_metrics(session).duration_minutes == 105


def test_archived_and_deleted_movements_are_excluded(app):
    with app.app_context():
        session = make_session()
        add_sale(session, 10000, status="archived")
        add_sale(session, 20000, deleted_at=now_santiago())
        add_expense(session, 3000, status="archived")
        add_expense(session, 4000, deleted_at=now_santiago())
        db_session.commit()

        metrics = calculate_work_session_metrics(session)

        assert metrics.total_sales == 0
        assert metrics.operational_expenses == 0


def test_sale_and_operational_expense_are_associated_but_investment_is_not(client, app, csrf):
    with app.app_context():
        session = make_session()
        db_session.commit()
        session_id = session.id

    sale_response = client.post("/ventas/", data={
        **csrf,
        "amount": "10000",
        "occurred_at_date": "10-07-2026",
        "occurred_at_time": "12:00",
        "payment_method": "cash",
        "channel": "food_truck",
    })
    expense_response = client.post("/gastos/", data={
        **csrf,
        "amount": "5000",
        "occurred_at_date": "10-07-2026",
        "occurred_at_time": "13:00",
        "category": "Insumos",
        "expense_type": "operational",
        "payment_method": "cash",
        "description": "Insumos",
    })
    investment_response = client.post("/gastos/", data={
        **csrf,
        "amount": "90000",
        "occurred_at_date": "10-07-2026",
        "occurred_at_time": "14:00",
        "category": "Equipamiento",
        "expense_type": "investment",
        "payment_method": "cash",
        "description": "Equipo",
    })

    assert sale_response.status_code == 302
    assert expense_response.status_code == 302
    assert investment_response.status_code == 302
    with app.app_context():
        assert db_session.query(Sale).one().work_session_id == session_id
        operational, investment = db_session.query(Expense).order_by(Expense.id).all()
        assert operational.work_session_id == session_id
        assert investment.work_session_id is None


def test_edit_closed_session_updates_values_without_moving_movements(client, app, csrf):
    with app.app_context():
        session = make_session(
            opening_cash=10000,
            closed_at=datetime(2026, 7, 10, 18),
            counted_cash=15000,
        )
        sale = add_sale(session, 5000)
        db_session.commit()
        session_id = session.id
        sale_id = sale.id

    response = client.post(f"/jornadas/{session_id}/editar", data={
        **csrf,
        "opened_at_date": "10-07-2026",
        "opened_at_time": "09:30",
        "closed_at_date": "11-07-2026",
        "closed_at_time": "00:15",
        "opening_cash": "30000",
        "closing_cash_counted": "35000",
        "notes": "Apertura corregida",
        "closing_notes": "Cierre corregido",
    })

    assert response.status_code == 302
    with app.app_context():
        session = db_session.get(WorkSession, session_id)
        assert session.business_date.isoformat() == "2026-07-10"
        assert session.opening_cash == 30000
        assert session.closing_cash_counted == 35000
        assert session.closing_notes == "Cierre corregido"
        assert db_session.get(Sale, sale_id).work_session_id == session_id
        assert db_session.query(AuditLog).filter(AuditLog.action == "edit_work_session").count() == 1


def test_historical_preview_and_association_are_safe(app):
    with app.app_context():
        target = make_session(
            opened_at=datetime(2026, 7, 10, 10),
            closed_at=datetime(2026, 7, 10, 20),
            counted_cash=0,
        )
        other = make_session(
            opened_at=datetime(2026, 7, 11, 10),
            closed_at=datetime(2026, 7, 11, 20),
            counted_cash=0,
        )
        eligible_sale = add_sale(None, 10000, occurred_at=datetime(2026, 7, 10, 12))
        eligible_expense = add_expense(None, 3000, occurred_at=datetime(2026, 7, 10, 13))
        assigned_sale = add_sale(other, 5000, occurred_at=datetime(2026, 7, 10, 14))
        add_expense(None, 80000, expense_type="investment", occurred_at=datetime(2026, 7, 10, 15))
        add_sale(None, 9000, occurred_at=datetime(2026, 7, 10, 21))
        db_session.commit()

        preview = historical_movement_preview(target)
        associated = associate_historical_movements(target)
        db_session.commit()

        assert [sale.id for sale in preview["sales"]] == [eligible_sale.id]
        assert [expense.id for expense in preview["expenses"]] == [eligible_expense.id]
        assert associated == 2
        assert eligible_sale.work_session_id == target.id
        assert eligible_expense.work_session_id == target.id
        assert assigned_sale.work_session_id == other.id
        assert db_session.query(AuditLog).filter(AuditLog.action == "associate_historical_movement").count() == 2


def _tenant_world():
    """Org A (branches A1, A2) and org B (B1); returns {name: (organization_id, branch_id)}."""
    from models.branch import Branch
    from models.organization import Organization
    a = Organization(name="A", slug="a", entity_type="company")
    b = Organization(name="B", slug="b", entity_type="company")
    db_session.add_all([a, b]); db_session.flush()
    branches = [Branch(organization_id=a.id, name="A1", slug="a1"), Branch(organization_id=a.id, name="A2", slug="a2"),
                Branch(organization_id=b.id, name="B1", slug="b1")]
    db_session.add_all(branches); db_session.flush()
    return {"A": (a.id, branches[0].id), "A2": (a.id, branches[1].id), "B": (b.id, branches[2].id)}


def _unassociated(tenant, hour=12, amount=1000):
    org, branch = tenant
    sale = Sale(organization_id=org, branch_id=branch, occurred_at=datetime(2026, 7, 10, hour), amount=amount,
                payment_method="cash", channel="food_truck")
    expense = Expense(organization_id=org, branch_id=branch, occurred_at=datetime(2026, 7, 10, hour), amount=amount // 2,
                      category="Insumos", expense_type="operational", payment_method="cash", description="x")
    db_session.add_all([sale, expense]); db_session.flush()
    return sale, expense


def _closed_session(tenant):
    org, branch = tenant
    work_session = WorkSession(organization_id=org, branch_id=branch, business_date=datetime(2026, 7, 10).date(),
                               opened_at=datetime(2026, 7, 10, 10), closed_at=datetime(2026, 7, 10, 20),
                               opening_cash=0, closing_cash_counted=0, status="closed")
    db_session.add(work_session); db_session.flush()
    return work_session


def test_historical_preview_and_association_never_cross_organizations(app):
    with app.app_context():
        tenants = _tenant_world()
        a_sale, a_expense = _unassociated(tenants["A"])
        b_sale, b_expense = _unassociated(tenants["B"], amount=777000)
        session_a = _closed_session(tenants["A"])
        db_session.commit()

        preview = historical_movement_preview(session_a)
        assert [s.id for s in preview["sales"]] == [a_sale.id] and [e.id for e in preview["expenses"]] == [a_expense.id]
        assert preview["sales_total"] == 1000 and preview["expenses_total"] == 500   # none of B's money is visible

        assert associate_historical_movements(session_a) == 2
        db_session.commit()
        assert (a_sale.work_session_id, a_expense.work_session_id) == (session_a.id, session_a.id)
        assert (b_sale.work_session_id, b_expense.work_session_id) == (None, None)
        logs = db_session.query(AuditLog).filter(AuditLog.action == "associate_historical_movement").all()
        assert sorted((log.entity_type, log.entity_id) for log in logs) == sorted([("sale", a_sale.id), ("expense", a_expense.id)])

        # Tenant B is symmetric: its own session sees only B's movements.
        session_b = _closed_session(tenants["B"])
        db_session.commit()
        assert [s.id for s in historical_movement_preview(session_b)["sales"]] == [b_sale.id]
        assert associate_historical_movements(session_b) == 2
        db_session.commit()
        assert (a_sale.work_session_id, a_expense.work_session_id) == (session_a.id, session_a.id)  # untouched by B


def test_historical_preview_and_association_never_cross_branches_of_one_organization(app):
    with app.app_context():
        tenants = _tenant_world()
        a1_sale, a1_expense = _unassociated(tenants["A"])
        a2_sale, a2_expense = _unassociated(tenants["A2"], amount=555000)
        session_a1 = _closed_session(tenants["A"])
        db_session.commit()

        preview = historical_movement_preview(session_a1)
        assert [s.id for s in preview["sales"]] == [a1_sale.id] and [e.id for e in preview["expenses"]] == [a1_expense.id]
        assert associate_historical_movements(session_a1) == 2
        db_session.commit()
        assert (a2_sale.work_session_id, a2_expense.work_session_id) == (None, None)
        assert db_session.query(AuditLog).filter(AuditLog.action == "associate_historical_movement").count() == 2


def test_association_keeps_every_existing_historical_rule_inside_the_tenant(app):
    with app.app_context():
        tenants = _tenant_world()
        org, branch = tenants["A"]
        session_a = _closed_session(tenants["A"])
        other_session = _closed_session(tenants["A"])
        eligible_sale, eligible_expense = _unassociated(tenants["A"])
        ineligible = [
            Sale(organization_id=org, branch_id=branch, occurred_at=datetime(2026, 7, 10, 11), amount=10, payment_method="cash", channel="food_truck", status="archived"),
            Sale(organization_id=org, branch_id=branch, occurred_at=datetime(2026, 7, 10, 11), amount=10, payment_method="cash", channel="food_truck", deleted_at=datetime(2026, 7, 11)),
            Sale(organization_id=org, branch_id=branch, occurred_at=datetime(2026, 7, 10, 21), amount=10, payment_method="cash", channel="food_truck"),  # after closing
            Sale(organization_id=org, branch_id=branch, occurred_at=datetime(2026, 7, 10, 11), amount=10, payment_method="cash", channel="food_truck", work_session_id=other_session.id),
            Expense(organization_id=org, branch_id=branch, occurred_at=datetime(2026, 7, 10, 11), amount=10, category="Equipamiento", expense_type="investment", payment_method="cash", description="inv"),
        ]
        db_session.add_all(ineligible); db_session.commit()
        preview = historical_movement_preview(session_a)
        assert [s.id for s in preview["sales"]] == [eligible_sale.id] and [e.id for e in preview["expenses"]] == [eligible_expense.id]
        assert associate_historical_movements(session_a) == 2
        db_session.commit()
        assert ineligible[3].work_session_id == other_session.id
        assert all(item.work_session_id is None for item in ineligible[:3] + ineligible[4:])


def test_untenanted_legacy_session_only_matches_untenanted_movements(app):
    """Pre-tenant rows (no organization/branch) never mix with real tenants' movements."""
    with app.app_context():
        tenants = _tenant_world()
        _unassociated(tenants["A"], amount=999000)
        legacy_sale = add_sale(None, 4000, occurred_at=datetime(2026, 7, 10, 12))
        legacy = make_session(opened_at=datetime(2026, 7, 10, 10), closed_at=datetime(2026, 7, 10, 20), counted_cash=0)
        db_session.commit()
        assert [s.id for s in historical_movement_preview(legacy)["sales"]] == [legacy_sale.id]
        assert historical_movement_preview(legacy)["sales_total"] == 4000


def test_preview_has_no_way_to_skip_the_tenant_scope():
    import inspect
    assert list(inspect.signature(historical_movement_preview).parameters) == ["work_session"]
    assert list(inspect.signature(associate_historical_movements).parameters) == ["work_session"]


def test_open_form_derives_business_date_and_accepts_zero_cash(client, app, csrf):
    response = client.post("/jornadas/", data={
        **csrf,
        "opened_at_date": "11-07-2026",
        "opened_at_time": "00:05",
        "opening_cash": "0",
        "notes": "Turno nocturno",
    })

    assert response.status_code == 302
    with app.app_context():
        session = db_session.query(WorkSession).one()
        assert session.business_date.isoformat() == "2026-07-11"
        assert session.opening_cash == 0


def test_close_requires_counted_cash_and_persists_closing_notes(client, app, csrf):
    with app.app_context():
        session = make_session(opened_at=datetime(2026, 7, 10, 10))
        db_session.commit()
        session_id = session.id

    response = client.post(f"/jornadas/{session_id}/cerrar", data={
        **csrf,
        "closed_at_date": "10-07-2026",
        "closed_at_time": "20:00",
        "closing_cash_counted": "0",
        "closing_notes": "Sin efectivo",
    })

    assert response.status_code == 302
    with app.app_context():
        session = db_session.get(WorkSession, session_id)
        assert session.status == "closed"
        assert session.closing_cash_counted == 0
        assert session.closing_notes == "Sin efectivo"


def test_close_must_be_after_opening(client, app, csrf):
    with app.app_context():
        session = make_session(opened_at=datetime(2026, 7, 10, 10))
        db_session.commit()
        session_id = session.id

    response = client.post(f"/jornadas/{session_id}/cerrar", data={
        **csrf,
        "closed_at_date": "10-07-2026",
        "closed_at_time": "10:00",
        "closing_cash_counted": "0",
    })

    assert response.status_code == 200
    with app.app_context():
        assert db_session.get(WorkSession, session_id).status == "open"

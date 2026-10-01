from datetime import datetime

import pytest

from models import db_session
from models.expense import Expense
from models.sale import Sale


def expense_form(category, expense_type):
    return {
        "amount": "8000",
        "occurred_at_date": "11-07-2026",
        "occurred_at_time": "12:00",
        "category": category,
        "expense_type": expense_type,
        "payment_method": "cash",
        "description": f"Movimiento {category}",
    }


@pytest.mark.parametrize("category", ["Gasto operacional", "Gastos operacionales", "Proveedores"])
def test_new_expense_rejects_obsolete_categories(client, app, csrf, category):
    response = client.post("/gastos/", data={**csrf, **expense_form(category, "operational")})

    assert response.status_code == 200
    assert b"categor\xc3\xada v\xc3\xa1lida para el tipo de movimiento" in response.data
    with app.app_context():
        assert db_session.query(Expense).count() == 0


@pytest.mark.parametrize(
    ("category", "expense_type"),
    [("Insumos", "operational"), ("Equipamiento", "investment")],
)
def test_new_expense_accepts_category_for_its_type(client, app, csrf, category, expense_type):
    response = client.post("/gastos/", data={**csrf, **expense_form(category, expense_type)})

    assert response.status_code == 302
    with app.app_context():
        expense = db_session.query(Expense).one()
        assert expense.category == category
        assert expense.expense_type == expense_type


@pytest.mark.parametrize(
    ("category", "expense_type"),
    [("Equipamiento", "operational"), ("Insumos", "investment")],
)
def test_new_expense_rejects_category_from_other_type(client, app, csrf, category, expense_type):
    response = client.post("/gastos/", data={**csrf, **expense_form(category, expense_type)})

    assert response.status_code == 200
    with app.app_context():
        assert db_session.query(Expense).count() == 0


def seed_history_movements():
    db_session.add(Sale(
        occurred_at=datetime(2026, 7, 11, 10),
        amount=12000,
        payment_method="cash",
        channel="food_truck",
        description="Venta visible",
    ))
    db_session.add_all([
        Expense(
            occurred_at=datetime(2026, 7, 11, 11),
            amount=3000,
            category="Luz",
            expense_type="operational",
            payment_method="cash",
            description="Gasto operacional visible",
        ),
        Expense(
            occurred_at=datetime(2026, 7, 11, 12),
            amount=7000,
            category="Equipamiento",
            expense_type="investment",
            payment_method="transfer",
            description="Inversión visible",
        ),
    ])
    db_session.commit()


def test_financial_history_filters_operational_expenses(client, app):
    with app.app_context():
        seed_history_movements()

    response = client.get("/historial/?type=expense")

    assert response.status_code == 200
    assert b"Gasto operacional visible" in response.data
    assert "Inversión visible".encode() not in response.data
    assert b"Venta visible" not in response.data


def test_financial_history_filters_investments(client, app):
    with app.app_context():
        seed_history_movements()

    response = client.get("/historial/?type=investment")

    assert response.status_code == 200
    assert "Inversión visible".encode() in response.data
    assert b"Gasto operacional visible" not in response.data
    assert b"Venta visible" not in response.data


def test_legacy_category_renders_and_can_be_preserved_on_edit(client, app, csrf):
    with app.app_context():
        expense = Expense(
            occurred_at=datetime(2026, 7, 10, 12),
            amount=12000,
            category="Proveedores",
            expense_type="operational",
            payment_method="cash",
            description="Registro histórico",
        )
        db_session.add(expense)
        db_session.commit()
        expense_id = expense.id

    edit_response = client.get(f"/gastos/{expense_id}/editar")
    update_response = client.post(
        f"/gastos/{expense_id}/editar",
        data={**csrf, **expense_form("Proveedores", "operational")},
    )

    assert edit_response.status_code == 200
    assert b"Proveedores (categor\xc3\xada hist\xc3\xb3rica)" in edit_response.data
    assert update_response.status_code == 302
    with app.app_context():
        assert db_session.get(Expense, expense_id).category == "Proveedores"


def test_category_filter_is_hidden_but_old_query_parameter_remains_compatible(client, app):
    with app.app_context():
        db_session.add(Expense(
            occurred_at=datetime(2026, 7, 10, 12),
            amount=9000,
            category="Proveedores",
            expense_type="operational",
            payment_method="cash",
            description="Categoría heredada",
        ))
        db_session.commit()

    expenses_response = client.get("/gastos/?category=Proveedores")
    history_response = client.get("/historial/?category=Proveedores&type=expense")

    assert expenses_response.status_code == 200
    assert "Categoría heredada".encode() in expenses_response.data
    assert b"Todas las categor\xc3\xadas" not in expenses_response.data
    assert history_response.status_code == 200
    assert "Categoría heredada".encode() in history_response.data
    assert b'name="category"' not in history_response.data

from datetime import datetime

from models import db_session
from models.expense import Expense
from models.sale import Sale
from models.work_session import WorkSession


def test_create_sale_from_form(client, app, csrf):
    response = client.post("/ventas/", data={
        **csrf,
        "amount": "12500",
        "payment_method": "cash",
        "channel": "food_truck",
        "description": "Combo test",
    }, follow_redirects=True)

    assert response.status_code == 200
    with app.app_context():
        sale = db_session.query(Sale).one()
        assert sale.amount == 12500
        assert sale.status == "active"


def test_create_expense_from_form(client, app, csrf):
    response = client.post("/gastos/", data={
        **csrf,
        "amount": "8000",
        "category": "Insumos",
        "expense_type": "operational",
        "payment_method": "debit",
        "description": "Compra test",
    }, follow_redirects=True)

    assert response.status_code == 200
    with app.app_context():
        expense = db_session.query(Expense).one()
        assert expense.amount == 8000
        assert expense.expense_type == "operational"


def test_only_one_open_work_session(client, app, csrf):
    first = client.post("/jornadas/", data={
        **csrf,
        "business_date": "2026-07-09",
        "opened_at": "2026-07-09T10:00",
        "opening_cash": "20000",
    }, follow_redirects=True)
    second = client.post("/jornadas/", data={
        **csrf,
        "business_date": "2026-07-10",
        "opened_at": "2026-07-10T10:00",
        "opening_cash": "10000",
    }, follow_redirects=True)

    assert first.status_code == 200
    assert second.status_code == 200
    with app.app_context():
        assert db_session.query(WorkSession).filter(WorkSession.status == "open").count() == 1


def test_archive_sale_without_physical_delete(client, app, csrf):
    with app.app_context():
        sale = Sale(occurred_at=datetime(2026, 7, 9, 12), amount=9000, payment_method="cash", channel="food_truck")
        db_session.add(sale)
        db_session.commit()
        sale_id = sale.id

    response = client.post(f"/ventas/{sale_id}/archivar", data=csrf, follow_redirects=True)

    assert response.status_code == 200
    with app.app_context():
        assert db_session.query(Sale).count() == 1
        assert db_session.get(Sale, sale_id).status == "archived"


def test_archive_expense_without_physical_delete(client, app, csrf):
    with app.app_context():
        expense = Expense(
            occurred_at=datetime(2026, 7, 9, 12),
            amount=12000,
            category="Gas",
            expense_type="operational",
            payment_method="cash",
            description="Gas test",
        )
        db_session.add(expense)
        db_session.commit()
        expense_id = expense.id

    response = client.post(f"/gastos/{expense_id}/archivar", data=csrf, follow_redirects=True)

    assert response.status_code == 200
    with app.app_context():
        assert db_session.query(Expense).count() == 1
        assert db_session.get(Expense, expense_id).status == "archived"

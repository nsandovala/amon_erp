from datetime import datetime

from models import db_session
from models.expense import Expense
from models.sale import Sale
from services.metrics import calculate_metrics, expenses_by_category, sales_expenses_by_day


def test_delete_sale_soft_deletes_and_excludes_metrics(client, app, csrf):
    with app.app_context():
        sale = Sale(occurred_at=datetime(2026, 7, 9, 12), amount=15000, payment_method="cash", channel="food_truck")
        db_session.add(sale)
        db_session.commit()
        sale_id = sale.id

    response = client.post(f"/ventas/{sale_id}/eliminar", data=csrf, follow_redirects=True)

    assert response.status_code == 200
    with app.app_context():
        sale = db_session.get(Sale, sale_id)
        assert sale is not None
        assert sale.deleted_at is not None
        metrics = calculate_metrics(datetime(2026, 7, 9), datetime(2026, 7, 9, 23, 59, 59))
        assert metrics["total_sales"] == 0


def test_delete_expense_soft_deletes_and_can_restore(client, app, csrf):
    with app.app_context():
        expense = Expense(
            occurred_at=datetime(2026, 7, 9, 13),
            amount=9000,
            category="Insumos",
            expense_type="operational",
            payment_method="cash",
            description="Panes",
        )
        db_session.add(expense)
        db_session.commit()
        expense_id = expense.id

    deleted = client.post(f"/gastos/{expense_id}/eliminar", data=csrf, follow_redirects=True)
    restored = client.post(f"/gastos/{expense_id}/restaurar", data=csrf, follow_redirects=True)

    assert deleted.status_code == 200
    assert restored.status_code == 200
    with app.app_context():
        expense = db_session.get(Expense, expense_id)
        assert expense is not None
        assert expense.deleted_at is None
        metrics = calculate_metrics(datetime(2026, 7, 9), datetime(2026, 7, 9, 23, 59, 59))
        assert metrics["operational_expenses"] == 9000


def test_investments_are_excluded_from_operational_charts(app):
    with app.app_context():
        db_session.add_all([
            Expense(
                occurred_at=datetime(2026, 7, 9, 10),
                amount=10000,
                category="Insumos",
                expense_type="operational",
                payment_method="cash",
                description="Insumos",
            ),
            Expense(
                occurred_at=datetime(2026, 7, 9, 11),
                amount=1000000,
                category="Equipamiento",
                expense_type="investment",
                payment_method="transfer",
                description="Plancha",
            ),
        ])
        db_session.commit()

        categories = expenses_by_category(datetime(2026, 7, 9), datetime(2026, 7, 9, 23, 59, 59))
        daily = sales_expenses_by_day(datetime(2026, 7, 9).date(), datetime(2026, 7, 9).date())

        assert categories == [{"category": "Insumos", "amount": 10000}]
        assert daily[0]["expenses"] == 10000


def test_cash_balance_excludes_cash_investments(app):
    with app.app_context():
        db_session.add_all([
            Sale(occurred_at=datetime(2026, 7, 9, 12), amount=50000, payment_method="cash", channel="food_truck"),
            Sale(occurred_at=datetime(2026, 7, 9, 13), amount=30000, payment_method="debit", channel="food_truck"),
            Expense(
                occurred_at=datetime(2026, 7, 9, 14),
                amount=12000,
                category="Gas",
                expense_type="operational",
                payment_method="cash",
                description="Gas",
            ),
            Expense(
                occurred_at=datetime(2026, 7, 9, 15),
                amount=100000,
                category="Equipamiento",
                expense_type="investment",
                payment_method="cash",
                description="Equipo",
            ),
        ])
        db_session.commit()

        metrics = calculate_metrics(datetime(2026, 7, 9), datetime(2026, 7, 9, 23, 59, 59))

        assert metrics["cash_balance"] == 38000
        assert metrics["total_flow"] == -32000

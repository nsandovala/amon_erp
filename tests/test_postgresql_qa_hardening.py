from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from models import db_session
from models.expense import Expense
from models.sale import Sale
from routes import apply_datetime_range


def test_postgresql_date_filter_binds_python_datetimes():
    statement = apply_datetime_range(
        select(Sale),
        Sale.occurred_at,
        "2026-07-09",
        "2026-07-09",
    )

    parameters = statement.compile(dialect=postgresql.dialect()).params

    assert list(parameters.values()) == [
        datetime(2026, 7, 9, 0, 0),
        datetime(2026, 7, 10, 0, 0),
    ]


def test_sale_date_filter_uses_full_day_boundaries(client, app):
    with app.app_context():
        db_session.add_all([
            Sale(occurred_at=datetime(2026, 7, 8, 23, 59, 59), amount=1000, payment_method="cash", channel="food_truck", description="before-range"),
            Sale(occurred_at=datetime(2026, 7, 9, 0, 0), amount=2000, payment_method="cash", channel="food_truck", description="range-start"),
            Sale(occurred_at=datetime(2026, 7, 9, 23, 59, 59, 999999), amount=3000, payment_method="cash", channel="food_truck", description="range-end"),
            Sale(occurred_at=datetime(2026, 7, 10, 0, 0), amount=4000, payment_method="cash", channel="food_truck", description="after-range"),
        ])
        db_session.commit()

    response = client.get("/ventas/?start=2026-07-09&end=2026-07-09")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "range-start" in html
    assert "range-end" in html
    assert "before-range" not in html
    assert "after-range" not in html


def test_expense_date_filter_uses_full_day_boundaries(client, app):
    with app.app_context():
        db_session.add_all([
            Expense(occurred_at=datetime(2026, 7, 8, 23, 59, 59), amount=1000, category="Insumos", expense_type="operational", payment_method="cash", description="before-range"),
            Expense(occurred_at=datetime(2026, 7, 9, 0, 0), amount=2000, category="Insumos", expense_type="operational", payment_method="cash", description="range-start"),
            Expense(occurred_at=datetime(2026, 7, 9, 23, 59, 59, 999999), amount=3000, category="Insumos", expense_type="operational", payment_method="cash", description="range-end"),
            Expense(occurred_at=datetime(2026, 7, 10, 0, 0), amount=4000, category="Insumos", expense_type="operational", payment_method="cash", description="after-range"),
        ])
        db_session.commit()

    response = client.get("/gastos/?start=2026-07-09&end=2026-07-09")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "range-start" in html
    assert "range-end" in html
    assert "before-range" not in html
    assert "after-range" not in html


def test_invalid_list_date_filter_does_not_reach_database(client):
    assert client.get("/ventas/?start=not-a-date").status_code == 200
    assert client.get("/gastos/?end=not-a-date").status_code == 200

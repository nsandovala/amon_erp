from datetime import datetime

from models import db_session
from models.expense import Expense
from models.sale import Sale
from models.work_session import WorkSession
from services.metrics import calculate_metrics, monthly_summary


def test_operating_profit_and_investments_are_separate(app):
    with app.app_context():
        db_session.add_all([
            Sale(occurred_at=datetime(2026, 7, 9, 12), amount=100000, payment_method="cash", channel="food_truck"),
            Expense(occurred_at=datetime(2026, 7, 9, 13), amount=30000, category="Insumos", expense_type="operational", payment_method="cash", description="Insumos"),
            Expense(occurred_at=datetime(2026, 7, 9, 14), amount=20000, category="Equipamiento", expense_type="investment", payment_method="transfer", description="Plancha"),
        ])
        db_session.commit()

        metrics = calculate_metrics(datetime(2026, 7, 9), datetime(2026, 7, 9, 23, 59, 59))

        assert metrics["total_sales"] == 100000
        assert metrics["operational_expenses"] == 30000
        assert metrics["operating_profit"] == 70000
        assert metrics["investments"] == 20000
        assert metrics["total_result"] == 50000


def test_margin_is_zero_when_sales_are_zero(app):
    with app.app_context():
        metrics = calculate_metrics(datetime(2026, 7, 9), datetime(2026, 7, 9, 23, 59, 59))
        assert metrics["operating_margin"] == 0
        assert metrics["average_ticket"] == 0


def test_monthly_summary_is_calculated_from_movements(app):
    with app.app_context():
        work_session = WorkSession(
            business_date=datetime(2026, 7, 9).date(),
            opened_at=datetime(2026, 7, 9, 10),
            closed_at=datetime(2026, 7, 9, 18),
            opening_cash=10000,
            closing_cash=50000,
            status="closed",
        )
        db_session.add(work_session)
        db_session.flush()
        db_session.add_all([
            Sale(work_session_id=work_session.id, occurred_at=datetime(2026, 7, 9, 12), amount=70000, payment_method="debit", channel="food_truck"),
            Expense(work_session_id=work_session.id, occurred_at=datetime(2026, 7, 9, 13), amount=15000, category="Insumos", expense_type="operational", payment_method="cash", description="Panes"),
            Expense(work_session_id=work_session.id, occurred_at=datetime(2026, 7, 9, 14), amount=5000, category="Gas", expense_type="operational", payment_method="cash", description="Gas"),
            Expense(occurred_at=datetime(2026, 7, 10, 14), amount=100000, category="Inversión food truck", expense_type="investment", payment_method="transfer", description="Carro"),
        ])
        db_session.commit()

        rows = monthly_summary(2026)

        assert rows[0]["month"] == "2026-07"
        assert rows[0]["worked_days"] == 1
        assert rows[0]["income"] == 70000
        assert rows[0]["supplies"] == 15000
        assert rows[0]["energy"] == 5000
        assert rows[0]["investments"] == 100000
        assert rows[0]["operating_profit"] == 50000
        assert rows[0]["total_result"] == -50000

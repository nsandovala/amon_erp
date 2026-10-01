from datetime import datetime, timedelta

import pytest

from app import format_duration
from models import db_session, now_santiago
from models.expense import Expense
from models.sale import Sale
from models.work_session import WorkSession
from services.metrics import calculate_return_estimate
from services.work_sessions import (
    associate_historical_movements,
    calculate_work_session_metrics,
    count_unassociated_active_movements,
    historical_movement_preview,
)


def make_closed_session(business_date, opening_cash=10000, counted_cash=10000):
    session = WorkSession(
        business_date=business_date,
        opened_at=datetime.combine(business_date, datetime.min.time()).replace(hour=10),
        closed_at=datetime.combine(business_date, datetime.min.time()).replace(hour=18),
        opening_cash=opening_cash,
        closing_cash=counted_cash,
        closing_cash_counted=counted_cash,
        status="closed",
    )
    db_session.add(session)
    db_session.flush()
    return session


def test_format_duration_seconds_only():
    assert format_duration(8) == "8 s"


def test_format_duration_minutes_and_seconds():
    assert format_duration(12 * 60 + 8) == "12 min 8 s"


def test_format_duration_hours_and_minutes_omits_zero_seconds():
    assert format_duration(15 * 3600 + 28 * 60) == "15 h 28 min"


def test_format_duration_hours_minutes_and_seconds():
    assert format_duration(15 * 3600 + 28 * 60 + 8) == "15 h 28 min 8 s"


def test_format_duration_days_hours_minutes():
    assert format_duration(2 * 86400 + 3 * 3600 + 12 * 60) == "2 d 3 h 12 min"


def test_format_duration_zero_returns_zero_seconds():
    assert format_duration(0) == "0 s"
    assert format_duration(None) == "0 s"


def test_anomalous_duration_is_flagged(app):
    with app.app_context():
        session = WorkSession(
            business_date=datetime(2026, 5, 1).date(),
            opened_at=datetime(2026, 5, 1, 10, 0),
            closed_at=datetime(2026, 7, 3, 10, 0),
            opening_cash=0,
            closing_cash=0,
            closing_cash_counted=0,
            status="closed",
        )
        db_session.add(session)
        db_session.commit()

        metrics = calculate_work_session_metrics(session)
        assert metrics.is_anomalous_duration is True


def test_cross_day_close_renders_full_date(client, app):
    with app.app_context():
        session = WorkSession(
            business_date=datetime(2026, 7, 10).date(),
            opened_at=datetime(2026, 7, 10, 23, 30),
            closed_at=datetime(2026, 7, 11, 2, 15),
            opening_cash=0,
            closing_cash=0,
            closing_cash_counted=0,
            status="closed",
        )
        db_session.add(session)
        db_session.commit()

    response = client.get("/jornadas/")

    assert response.status_code == 200
    assert b"11-07-2026 02:15" in response.data


def test_anomalous_duration_shows_warning(client, app):
    with app.app_context():
        session = WorkSession(
            business_date=datetime(2026, 5, 1).date(),
            opened_at=datetime(2026, 5, 1, 10, 0),
            closed_at=datetime(2026, 7, 3, 10, 0),
            opening_cash=0,
            closing_cash=0,
            closing_cash_counted=0,
            status="closed",
        )
        db_session.add(session)
        db_session.commit()

    response = client.get("/jornadas/")

    assert response.status_code == 200
    assert "Revisar fechas de apertura y cierre".encode() in response.data


def test_unassociated_movements_alert_visible(client, app):
    with app.app_context():
        db_session.add(Sale(
            occurred_at=datetime(2026, 7, 10, 12),
            amount=15000,
            payment_method="cash",
            channel="food_truck",
        ))
        db_session.add(Expense(
            occurred_at=datetime(2026, 7, 10, 13),
            amount=5000,
            category="Insumos",
            expense_type="operational",
            payment_method="cash",
            description="Insumos",
        ))
        db_session.commit()

    response = client.get("/jornadas/")

    assert response.status_code == 200
    assert b"2 movimientos sin jornada asociada" in response.data
    assert b"Revisar asociaci\xc3\xb3n hist\xc3\xb3rica" in response.data


def test_unassociated_alert_absent_when_all_associated(client, app):
    with app.app_context():
        session = make_closed_session(datetime(2026, 7, 10).date())
        db_session.add(Sale(
            work_session_id=session.id,
            occurred_at=datetime(2026, 7, 10, 12),
            amount=15000,
            payment_method="cash",
            channel="food_truck",
        ))
        db_session.commit()

    response = client.get("/jornadas/")

    assert response.status_code == 200
    assert b"sin jornada asociada" not in response.data


def test_no_automatic_association_without_open_session(client, app, csrf):
    with app.app_context():
        make_closed_session(datetime(2026, 7, 10).date())
        db_session.commit()

    response = client.post("/ventas/", data={
        **csrf,
        "amount": "10000",
        "occurred_at_date": "10-07-2026",
        "occurred_at_time": "14:00",
        "payment_method": "cash",
        "channel": "food_truck",
    })

    assert response.status_code == 302
    with app.app_context():
        sale = db_session.query(Sale).one()
        assert sale.work_session_id is None


def test_explicit_association_updates_metrics(app):
    with app.app_context():
        session = make_closed_session(datetime(2026, 7, 10).date())
        db_session.add(Sale(
            occurred_at=datetime(2026, 7, 10, 12),
            amount=25000,
            payment_method="cash",
            channel="food_truck",
        ))
        db_session.add(Expense(
            occurred_at=datetime(2026, 7, 10, 13),
            amount=5000,
            category="Insumos",
            expense_type="operational",
            payment_method="cash",
            description="Insumos",
        ))
        db_session.commit()

        assert count_unassociated_active_movements() == 2
        preview = historical_movement_preview(session)
        assert len(preview["sales"]) == 1
        assert len(preview["expenses"]) == 1

        associated = associate_historical_movements(session)
        db_session.commit()

        assert associated == 2
        assert count_unassociated_active_movements() == 0
        metrics = calculate_work_session_metrics(session)
        assert metrics.total_sales == 25000
        assert metrics.operational_expenses == 5000
        assert metrics.operational_profit == 20000


def test_return_estimate_unavailable_when_no_investment(app):
    with app.app_context():
        for day_offset in range(3):
            session = make_closed_session(
                datetime(2026, 7, 1 + day_offset).date(),
                opening_cash=0,
                counted_cash=10000,
            )
            db_session.add(Sale(
                work_session_id=session.id,
                occurred_at=session.opened_at,
                amount=10000,
                payment_method="cash",
                channel="food_truck",
            ))
        db_session.commit()

        estimate = calculate_return_estimate()

        assert estimate["can_estimate"] is False
        assert estimate["investment_total"] == 0
        assert estimate["recovery_percentage"] == 0.0


def test_return_estimate_unavailable_when_profit_zero_or_negative(app):
    with app.app_context():
        db_session.add(Expense(
            occurred_at=datetime(2026, 6, 1, 12),
            amount=500000,
            category="Equipamiento",
            expense_type="investment",
            payment_method="transfer",
            description="Inversión inicial",
        ))
        for day_offset in range(3):
            business_date = datetime(2026, 7, 1 + day_offset).date()
            session = make_closed_session(business_date, opening_cash=0, counted_cash=0)
            db_session.add(Expense(
                work_session_id=session.id,
                occurred_at=session.opened_at,
                amount=5000,
                category="Insumos",
                expense_type="operational",
                payment_method="cash",
                description="Insumos",
            ))
        db_session.commit()

        estimate = calculate_return_estimate()

        assert estimate["can_estimate"] is False
        assert estimate["capital_recovered"] == 0
        assert estimate["capital_pending"] == 500000


def test_return_estimate_unavailable_with_insufficient_sessions(app):
    with app.app_context():
        db_session.add(Expense(
            occurred_at=datetime(2026, 6, 1, 12),
            amount=200000,
            category="Equipamiento",
            expense_type="investment",
            payment_method="transfer",
            description="Inversión inicial",
        ))
        for day_offset in range(2):
            session = make_closed_session(
                datetime(2026, 7, 1 + day_offset).date(),
                opening_cash=0,
                counted_cash=50000,
            )
            db_session.add(Sale(
                work_session_id=session.id,
                occurred_at=session.opened_at,
                amount=50000,
                payment_method="cash",
                channel="food_truck",
            ))
        db_session.commit()

        estimate = calculate_return_estimate()

        assert estimate["can_estimate"] is False
        assert estimate["valid_sessions_count"] == 2


def test_return_estimate_computes_days_when_data_sufficient(app):
    with app.app_context():
        db_session.add(Expense(
            occurred_at=datetime(2026, 6, 1, 12),
            amount=300000,
            category="Equipamiento",
            expense_type="investment",
            payment_method="transfer",
            description="Inversión inicial",
        ))
        for day_offset in range(4):
            session = make_closed_session(
                datetime(2026, 7, 1 + day_offset).date(),
                opening_cash=0,
                counted_cash=50000,
            )
            db_session.add(Sale(
                work_session_id=session.id,
                occurred_at=session.opened_at,
                amount=50000,
                payment_method="cash",
                channel="food_truck",
            ))
        db_session.commit()

        estimate = calculate_return_estimate()

        assert estimate["can_estimate"] is True
        assert estimate["investment_total"] == 300000
        assert estimate["capital_recovered"] == 200000
        assert estimate["capital_pending"] == 100000
        assert estimate["valid_sessions_count"] == 4
        assert estimate["valid_days"] == 4
        assert estimate["daily_average"] == 50000
        assert estimate["estimated_days_remaining"] == 2


def test_investments_do_not_reduce_operational_profit(app):
    with app.app_context():
        for day_offset in range(3):
            session = make_closed_session(
                datetime(2026, 7, 1 + day_offset).date(),
                opening_cash=0,
                counted_cash=50000,
            )
            db_session.add(Sale(
                work_session_id=session.id,
                occurred_at=session.opened_at,
                amount=50000,
                payment_method="cash",
                channel="food_truck",
            ))
        db_session.add(Expense(
            occurred_at=datetime(2026, 7, 1, 8),
            amount=999999999,
            category="Equipamiento",
            expense_type="investment",
            payment_method="transfer",
            description="Inversión masiva",
        ))
        db_session.commit()

        estimate = calculate_return_estimate()

        assert estimate["capital_recovered"] == 150000


def test_recovery_percentage_capped_at_100(app):
    with app.app_context():
        db_session.add(Expense(
            occurred_at=datetime(2026, 6, 1, 12),
            amount=100000,
            category="Equipamiento",
            expense_type="investment",
            payment_method="transfer",
            description="Inversión inicial",
        ))
        for day_offset in range(3):
            session = make_closed_session(
                datetime(2026, 7, 1 + day_offset).date(),
                opening_cash=0,
                counted_cash=1000000,
            )
            db_session.add(Sale(
                work_session_id=session.id,
                occurred_at=session.opened_at,
                amount=1000000,
                payment_method="cash",
                channel="food_truck",
            ))
        db_session.commit()

        estimate = calculate_return_estimate()

        assert estimate["recovery_percentage"] == 100.0
        assert estimate["capital_pending"] == 0
        assert estimate["estimated_days_remaining"] == 0


def test_sale_form_prefills_current_santiago_date(client):
    response = client.get("/ventas/")
    today = now_santiago().date().isoformat()
    current_time = now_santiago().strftime("%H:%M")

    assert response.status_code == 200
    assert today.encode() in response.data
    assert current_time.encode() in response.data


def test_expense_form_prefills_current_santiago_date(client):
    response = client.get("/gastos/")
    today = now_santiago().date().isoformat()

    assert response.status_code == 200
    assert today.encode() in response.data


def test_sale_validation_error_preserves_submitted_date_time(client, app, csrf):
    response = client.post("/ventas/", data={
        **csrf,
        "amount": "abc",
        "occurred_at_date": "2025-06-05",
        "occurred_at_time": "07:45",
        "payment_method": "cash",
        "channel": "food_truck",
    })

    assert response.status_code == 200
    assert b"2025-06-05" in response.data
    assert b"07:45" in response.data


def test_sale_edit_keeps_original_date_time(client, app, csrf):
    with app.app_context():
        sale = Sale(
            occurred_at=datetime(2025, 3, 15, 9, 20),
            amount=15000,
            payment_method="cash",
            channel="food_truck",
            description="Histórica",
        )
        db_session.add(sale)
        db_session.commit()
        sale_id = sale.id

    response = client.get(f"/ventas/{sale_id}/editar")

    assert response.status_code == 200
    assert b"2025-03-15" in response.data
    assert b"09:20" in response.data


def test_history_csv_uses_semicolon_delimiter(client):
    response = client.get("/historial/exportar.csv")

    header_line = response.data.split(b"\n", 1)[0]

    assert b";" in header_line
    assert b"Fecha;Hora;Tipo" in header_line

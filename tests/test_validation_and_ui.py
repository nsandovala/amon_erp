from datetime import datetime

from models import db_session
from models.sale import Sale


def test_dashboard_defaults_to_current_month(client):
    response = client.get("/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'period=&#39;month&#39;' in html or "Este mes" in html
    assert 'class="chip active" href="/?period=month"' in html


def test_status_labels_are_translated(client, app):
    with app.app_context():
        sale = Sale(occurred_at=datetime(2026, 7, 9, 12), amount=10000, payment_method="cash", channel="food_truck")
        db_session.add(sale)
        db_session.commit()

    response = client.get("/ventas/")
    html = response.get_data(as_text=True)

    assert "Activo" in html
    assert ">active<" not in html


def test_rejects_five_digit_year_and_keeps_value(client, app, csrf):
    response = client.post("/ventas/", data={
        **csrf,
        "amount": "12500",
        "occurred_at_date": "09-07-20266",
        "occurred_at_time": "12:00",
        "payment_method": "cash",
        "channel": "food_truck",
        "description": "Fecha inválida",
    })
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "año de cuatro dígitos" in html
    assert "09-07-20266" in html
    with app.app_context():
        assert db_session.query(Sale).count() == 0


def test_rejects_ampm_time(client, app, csrf):
    response = client.post("/ventas/", data={
        **csrf,
        "amount": "12500",
        "occurred_at_date": "09-07-2026",
        "occurred_at_time": "12:00 PM",
        "payment_method": "cash",
        "channel": "food_truck",
    })

    assert response.status_code == 200
    assert "formato 24 horas" in response.get_data(as_text=True)
    with app.app_context():
        assert db_session.query(Sale).count() == 0


def test_rejects_time_after_2359(client, app, csrf):
    response = client.post("/ventas/", data={
        **csrf,
        "amount": "12500",
        "occurred_at_date": "09-07-2026",
        "occurred_at_time": "24:00",
        "payment_method": "cash",
        "channel": "food_truck",
    })

    assert response.status_code == 200
    assert "formato 24 horas" in response.get_data(as_text=True)
    with app.app_context():
        assert db_session.query(Sale).count() == 0

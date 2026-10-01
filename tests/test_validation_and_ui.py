from datetime import datetime

from models import db_session
from models.sale import Sale
from models.work_session import WorkSession


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


def test_create_forms_use_native_date_and_deterministic_time_controls(client):
    response = client.get("/ventas/")
    html = response.get_data(as_text=True)

    assert 'name="occurred_at_date"' in html
    assert 'type="date"' in html
    assert 'name="occurred_at_time"' in html
    assert 'type="text"' in html
    assert 'inputmode="numeric"' in html
    assert 'maxlength="5"' in html
    assert 'placeholder="HH:mm"' in html
    assert 'pattern="([01]\\d|2[0-3]):[0-5]\\d"' in html
    assert "type=\"time\"" not in html


def test_native_iso_date_value_is_saved(client, app, csrf):
    response = client.post("/ventas/", data={
        **csrf,
        "amount": "12500",
        "occurred_at_date": "2026-07-09",
        "occurred_at_time": "12:34",
        "payment_method": "cash",
        "channel": "food_truck",
    })

    assert response.status_code == 302
    with app.app_context():
        assert db_session.query(Sale).one().occurred_at == datetime(2026, 7, 9, 12, 34)


def test_24_hour_value_is_preserved_in_edit_form(client, app, csrf):
    response = client.post("/ventas/", data={
        **csrf,
        "amount": "12500",
        "occurred_at_date": "2026-07-09",
        "occurred_at_time": "22:22",
        "payment_method": "cash",
        "channel": "food_truck",
    })
    assert response.status_code == 302

    with app.app_context():
        sale = db_session.query(Sale).one()
        sale_id = sale.id
        assert sale.occurred_at == datetime(2026, 7, 9, 22, 22)

    edit_response = client.get(f"/ventas/{sale_id}/editar")

    assert b'value="22:22"' in edit_response.data


def test_read_only_dates_keep_chilean_format(client, app):
    with app.app_context():
        db_session.add(Sale(
            occurred_at=datetime(2026, 7, 9, 12, 34),
            amount=12500,
            payment_method="cash",
            channel="food_truck",
        ))
        db_session.commit()

    response = client.get("/ventas/")

    assert b"09-07-2026 12:34" in response.data


def test_open_session_has_direct_close_action(client, app):
    with app.app_context():
        db_session.add(WorkSession(
            business_date=datetime(2026, 7, 9).date(),
            opened_at=datetime(2026, 7, 9, 10),
            opening_cash=0,
            status="open",
        ))
        db_session.commit()

    response = client.get("/jornadas/")
    html = response.get_data(as_text=True)

    assert 'href="#current-session-action">Cerrar jornada</a>' in html

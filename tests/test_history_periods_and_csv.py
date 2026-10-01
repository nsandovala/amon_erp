import csv
from datetime import datetime, time, timedelta

from models import db_session, now_santiago
from models.expense import Expense
from models.sale import Sale


CSV_HEADERS = [
    "Fecha",
    "Hora",
    "Tipo",
    "Descripción",
    "Categoría / canal",
    "Medio de pago",
    "Monto CLP",
    "Estado",
    "ID de jornada",
]


def add_sale(occurred_at, description="Venta del filtro", amount=10000):
    db_session.add(Sale(
        occurred_at=occurred_at,
        amount=amount,
        payment_method="cash",
        channel="food_truck",
        description=description,
    ))


def add_expense(
    occurred_at,
    description="Gasto del filtro",
    amount=3000,
    expense_type="operational",
    category=None,
):
    db_session.add(Expense(
        occurred_at=occurred_at,
        amount=amount,
        category=category or ("Equipamiento" if expense_type == "investment" else "Insumos"),
        expense_type=expense_type,
        payment_method="cash",
        description=description,
    ))


def seed_all_types(occurred_at=None):
    occurred_at = occurred_at or datetime(2026, 7, 13, 12)
    add_sale(occurred_at, "Venta única", 10000)
    add_expense(occurred_at, "Gasto único", 3000)
    add_expense(occurred_at, "Inversión única", 7000, "investment")
    db_session.commit()


def csv_rows(response):
    return list(csv.reader(response.data.decode("utf-8-sig").splitlines(), delimiter=";"))


def test_history_type_selector_contains_sales(client):
    response = client.get("/historial/")

    assert response.status_code == 200
    assert b'<option value="sale"' in response.data
    assert b">Ventas</option>" in response.data
    assert b'name="category"' not in response.data


def test_history_type_sale_returns_only_sales(client, app):
    with app.app_context():
        seed_all_types()

    response = client.get("/historial/?type=sale")

    assert b"Venta \xc3\xbanica" in response.data
    assert b"Gasto \xc3\xbanico" not in response.data
    assert b"Inversi\xc3\xb3n \xc3\xbanica" not in response.data


def test_history_type_expense_returns_only_operational_expenses(client, app):
    with app.app_context():
        seed_all_types()

    response = client.get("/historial/?type=expense")

    assert b"Gasto \xc3\xbanico" in response.data
    assert b"Venta \xc3\xbanica" not in response.data
    assert b"Inversi\xc3\xb3n \xc3\xbanica" not in response.data


def test_history_type_investment_returns_only_investments(client, app):
    with app.app_context():
        seed_all_types()

    response = client.get("/historial/?type=investment")

    assert b"Inversi\xc3\xb3n \xc3\xbanica" in response.data
    assert b"Venta \xc3\xbanica" not in response.data
    assert b"Gasto \xc3\xbanico" not in response.data


def test_history_period_today_filters_dates(client, app):
    today = now_santiago().date()
    with app.app_context():
        add_sale(datetime.combine(today, time(23, 59)), "Venta hoy")
        add_sale(datetime.combine(today - timedelta(days=1), time(23, 59)), "Venta ayer")
        db_session.commit()

    response = client.get("/historial/?period=today")

    assert b"Venta hoy" in response.data
    assert b"Venta ayer" not in response.data


def test_history_period_current_week_filters_dates(client, app):
    today = now_santiago().date()
    week_start = today - timedelta(days=today.weekday())
    with app.app_context():
        add_sale(datetime.combine(week_start, time.min), "Venta semana actual")
        add_sale(datetime.combine(week_start - timedelta(days=1), time(23, 59)), "Venta semana anterior")
        db_session.commit()

    response = client.get("/historial/?period=current_week")

    assert b"Venta semana actual" in response.data
    assert b"Venta semana anterior" not in response.data


def test_history_period_current_month_filters_dates(client, app):
    today = now_santiago().date()
    month_start = today.replace(day=1)
    with app.app_context():
        add_sale(datetime.combine(month_start, time.min), "Venta mes actual")
        add_sale(datetime.combine(month_start - timedelta(days=1), time(23, 59)), "Venta mes anterior")
        db_session.commit()

    response = client.get("/historial/?period=current_month")

    assert b"Venta mes actual" in response.data
    assert b"Venta mes anterior" not in response.data


def test_history_period_previous_month_filters_dates(client, app):
    today = now_santiago().date()
    current_month_start = today.replace(day=1)
    previous_month_end = current_month_start - timedelta(days=1)
    previous_month_start = previous_month_end.replace(day=1)
    with app.app_context():
        add_sale(datetime.combine(previous_month_start, time.min), "Venta dentro mes anterior")
        add_sale(datetime.combine(current_month_start, time.min), "Venta fuera mes anterior")
        db_session.commit()

    response = client.get("/historial/?period=previous_month")

    assert b"Venta dentro mes anterior" in response.data
    assert b"Venta fuera mes anterior" not in response.data


def test_history_custom_range_includes_both_dates(client, app):
    with app.app_context():
        add_sale(datetime(2026, 7, 1, 0, 0), "Venta límite inicial")
        add_sale(datetime(2026, 7, 31, 23, 59), "Venta límite final")
        add_sale(datetime(2026, 8, 1, 0, 0), "Venta posterior")
        db_session.commit()

    response = client.get("/historial/?period=custom&start=2026-07-01&end=2026-07-31")

    assert "Venta límite inicial".encode() in response.data
    assert "Venta límite final".encode() in response.data
    assert b"Venta posterior" not in response.data


def test_history_custom_range_rejects_start_after_end(client, app):
    with app.app_context():
        add_sale(datetime(2026, 7, 15, 12), "No consultar rango ambiguo")
        db_session.commit()

    response = client.get("/historial/?period=custom&start=2026-07-31&end=2026-07-01")

    assert response.status_code == 200
    assert "Desde no puede ser posterior a Hasta.".encode() in response.data
    assert b"No consultar rango ambiguo" not in response.data


def test_history_csv_responds_200(client):
    response = client.get("/historial/exportar.csv")

    assert response.status_code == 200


def test_history_csv_content_type_is_csv(client):
    response = client.get("/historial/exportar.csv")

    assert response.headers["Content-Type"] == "text/csv; charset=utf-8"


def test_history_csv_content_disposition_has_filename(client):
    response = client.get("/historial/exportar.csv")

    disposition = response.headers["Content-Disposition"]
    assert disposition.startswith("attachment;")
    assert 'filename="amon-erp-historial_inicio_fin.csv"' in disposition


def test_history_csv_starts_with_utf8_bom(client):
    response = client.get("/historial/exportar.csv")

    assert response.data.startswith(b"\xef\xbb\xbf")


def test_history_csv_contains_expected_headers(client):
    response = client.get("/historial/exportar.csv")

    assert csv_rows(response)[0] == CSV_HEADERS


def test_history_csv_type_sale_exports_only_sales(client, app):
    with app.app_context():
        seed_all_types()

    response = client.get("/historial/exportar.csv?type=sale")
    rows = csv_rows(response)

    assert [row[3] for row in rows[1:]] == ["Venta única"]


def test_history_csv_respects_custom_date_range(client, app):
    with app.app_context():
        add_sale(datetime(2026, 7, 1, 0, 0), "Venta primera fecha")
        add_sale(datetime(2026, 7, 31, 23, 59), "Venta última fecha")
        add_sale(datetime(2026, 8, 1, 0, 0), "Venta fuera del CSV")
        db_session.commit()

    response = client.get(
        "/historial/exportar.csv?period=custom&start=2026-07-01&end=2026-07-31"
    )
    descriptions = [row[3] for row in csv_rows(response)[1:]]

    assert descriptions == ["Venta última fecha", "Venta primera fecha"]
    assert "Venta fuera del CSV" not in descriptions


def test_history_csv_keeps_signed_integer_amounts(client, app):
    with app.app_context():
        seed_all_types()

    amounts = {row[6] for row in csv_rows(client.get("/historial/exportar.csv"))[1:]}

    assert amounts == {"10000", "-3000", "-7000"}


def test_history_csv_empty_result_still_has_headers(client):
    response = client.get("/historial/exportar.csv?q=resultado-inexistente")

    assert csv_rows(response) == [CSV_HEADERS]


def test_history_csv_sanitizes_spreadsheet_formula_fields(client, app):
    with app.app_context():
        add_expense(
            datetime(2026, 7, 13, 12),
            description="=SUMA(1;1)",
            category="+categoría peligrosa",
        )
        db_session.commit()

    row = csv_rows(client.get("/historial/exportar.csv?type=expense"))[1]

    assert row[3] == "'=SUMA(1;1)"
    assert row[4] == "'+categoría peligrosa"

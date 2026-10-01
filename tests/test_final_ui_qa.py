from datetime import datetime
from pathlib import Path

import pytest

from models import db_session
from models.sale import Sale


def test_dashboard_uses_amon_erp_metadata_and_requested_heading(client):
    response = client.get("/")
    html = response.get_data(as_text=True)

    assert "<title>Resumen financiero · AMON ERP</title>" in html
    assert '<p class="eyebrow">Finanzas</p>' in html
    assert "<h1>Resumen financiero</h1>" in html
    assert "Vista consolidada de ventas, gastos, caja y resultado del período seleccionado." in html
    assert "AMON ERP" in html
    assert "The Best Burger" in html


@pytest.mark.parametrize("path,title", [
    ("/ventas/", "Ventas · AMON ERP"),
    ("/gastos/", "Gastos e inversiones · AMON ERP"),
    ("/jornadas/", "Jornadas · AMON ERP"),
    ("/historial/", "Historial financiero · AMON ERP"),
    ("/papelera/", "Papelera · AMON ERP"),
])
def test_primary_pages_use_standardized_amon_erp_titles(client, path, title):
    response = client.get(path)

    assert f"<title>{title}</title>".encode() in response.data


def test_history_keeps_edit_visible_and_secondary_actions_in_floating_menu(client, app):
    with app.app_context():
        db_session.add(Sale(
            occurred_at=datetime(2026, 7, 9, 22, 22),
            amount=12500,
            payment_method="cash",
            channel="food_truck",
            description="Venta nocturna",
        ))
        db_session.commit()

    response = client.get("/historial/")
    html = response.get_data(as_text=True)

    assert '>Editar</a>' in html
    assert html.index('>Editar</a>') < html.index("data-action-menu-trigger")
    assert "data-action-menu-popover hidden" in html
    assert ">Ver detalle</a>" in html
    assert ">Archivar</button>" in html
    assert ">Eliminar</button>" in html
    assert 'name="csrf_token"' in html
    assert '<details class="action-menu">' not in html


def test_action_menu_popover_is_portaled_and_viewport_bounded():
    javascript = (Path(__file__).parents[1] / "static/js/app.js").read_text(encoding="utf-8")

    assert "document.body.append(popover)" in javascript
    assert "window.innerWidth" in javascript
    assert "window.innerHeight" in javascript
    assert "placeholder.replaceWith(popover)" in javascript

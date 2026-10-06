"""F3.1 Business Cockpit UX: the dashboard renders only F3.0's deterministic data."""
import html as htmllib
import json
import re
import shutil
import subprocess
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from flask import g, template_rendered

from models import db_session
from models.membership import Membership
from routes import CHANNEL_LABELS, PAYMENT_LABELS
from services.metrics import calculate_metrics
from services.tenancy import resolve_request_tenant

from test_f30_cockpit import D, expense, sale, seed_two_months, tenants, work_session  # noqa: F401  (shared fixtures/helpers)

ROOT = Path(__file__).parents[1]
NOW = datetime(2026, 7, 15, 12)


def render(app, tenants, tenant="A", query="period=month", now=NOW):
    """GET the dashboard as a member of `tenant`; returns (html, template context)."""
    org, branch = tenants[tenant]
    db_session.add(Membership(organization_id=org, clerk_user_id="user_cockpit", role="owner"))
    db_session.commit()
    captured = []
    template_rendered.connect(lambda sender, template, context, **_: captured.append((template.name, context)), app, weak=False)

    @app.before_request
    def install_tenant():
        g.user_id = "user_cockpit"
        resolve_request_tenant(g.user_id)
        g.tenant_enforced = True

    client = app.test_client()
    with client.session_transaction() as session:
        session["active_organization_id"], session["active_branch_id"] = org, branch
    with patch("services.metrics.now_santiago", return_value=now), patch("services.work_sessions.now_santiago", return_value=now):
        response = client.get(f"/?{query}")
    assert response.status_code == 200
    context = next(ctx for name, ctx in captured if name == "dashboard.html")
    return response.get_data(as_text=True), context


def card(html, css_class):
    """The <article> of one primary KPI card."""
    return re.search(rf'<article class="kpi-primary {css_class}">.*?</article>', html, re.S).group(0)


def chart_rows(html, canvas_id):
    raw = re.search(rf'<canvas id="{canvas_id}" data-chart=\'(.*?)\'', html, re.S).group(1)
    return json.loads(htmllib.unescape(raw))


def text(fragment):
    """Visible text only: screen-reader-only spans are removed (their wording is asserted separately)."""
    visible = re.sub(r'<span class="visually-hidden">.*?</span>', "", fragment, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", visible)).strip()


# --------------------------------------------------------------- hierarchy

def test_cockpit_sections_follow_the_requested_hierarchy(app, tenants):
    seed_two_months(tenants["A"]); db_session.commit()
    html, _ = render(app, tenants)
    titles = ["Estado del negocio", "Tendencia y atención", "Composición", "Actividad y capital"]
    positions = [html.index(f'<h2 class="cockpit-section-title">{title}</h2>') for title in titles]
    assert positions == sorted(positions)
    trend = html[positions[1]:positions[2]]
    assert 'id="dailyChart"' in trend and 'id="attention-title"' in trend           # trend + attention together
    assert html.index('id="dailyChart"') < html.index('id="channelChart"') < html.index('id="paymentChart"')
    assert 'class="kpi-primary-grid"' in html[positions[0]:positions[1]] and "kpi-secondary-strip" in html[positions[0]:positions[1]]
    assert "Últimos movimientos" in html[positions[3]:] and "Resumen mensual" in html[positions[3]:]


def test_existing_features_and_actions_are_retained(app, tenants):
    seed_two_months(tenants["A"]); db_session.commit()
    html, _ = render(app, tenants)
    for expected in ("Agregar venta", "Agregar gasto", "Gestionar jornada", "Retorno estimado simple", "Últimos movimientos",
                     "Resumen mensual", "Gastos por categoría", "Diferencias de caja", "data-custom-filter", "Exportar CSV",
                     "Ventas versus gastos operacionales", 'id="dailyChart"'):
        assert expected in html, expected


# ------------------------------------------------------------ KPIs / deltas

def test_primary_kpis_show_value_and_comparison_against_previous_period(app, tenants):
    seed_two_months(tenants["A"]); db_session.commit()
    html, _ = render(app, tenants)
    kpis = {key: text(card(html, key)) for key in ("kpi-sales", "kpi-profit", "kpi-margin", "kpi-ticket")}
    assert kpis["kpi-sales"].startswith("Ventas $300.000") and "↑ 200,0% vs período anterior" in kpis["kpi-sales"]
    assert kpis["kpi-profit"].startswith("Ganancia operativa $150.000") and "↑ 275,0% vs período anterior" in kpis["kpi-profit"]
    assert kpis["kpi-ticket"].startswith("Ticket promedio $100.000") and "↑ 100,0% vs período anterior" in kpis["kpi-ticket"]
    assert "Margen operacional 50,0%" in kpis["kpi-margin"]
    assert "Comparado con 01-06-2026 – 30-06-2026" in html
    # the four requested KPIs are the primary ones; expenses moved into the trend card
    assert len(re.findall(r'<article class="kpi-primary ', html)) == 4


def test_margin_is_shown_in_percentage_points_never_as_a_relative_percentage(app, tenants):
    seed_two_months(tenants["A"]); db_session.commit()
    html, _ = render(app, tenants)
    margin = text(card(html, "kpi-margin"))
    assert "+10,0 pp vs período anterior" in margin
    assert "%" in margin and "↑" not in margin and not re.search(r"\d%\s+vs", margin)   # no "25,0% vs" ratio-of-ratios


def test_positive_negative_and_neutral_visual_direction(app, tenants):
    # previous: sales 300k / expenses 150k (margin 50.0); current: sales 100k / expenses 60k (margin 40.0)
    tenant = tenants["A"]
    for day, amount in [(3, 100000), (4, 120000), (5, 80000)]:
        sale(tenant, datetime(2026, 6, day, 12), amount)
    expense(tenant, datetime(2026, 6, 6, 12), 150000)
    sale(tenant, datetime(2026, 7, 3, 12), 100000); expense(tenant, datetime(2026, 7, 4, 12), 60000)
    db_session.commit()
    html, _ = render(app, tenants)
    sales_card, margin_card = card(html, "kpi-sales"), card(html, "kpi-margin")
    assert "delta-negative" in sales_card and "↓ 66,7%" in text(sales_card)
    assert "delta-negative" in margin_card and "−10,0 pp" in text(margin_card)
    expenses = re.search(r'<p class="trend-expenses">.*?</p>', html, re.S).group(0)
    assert "delta-positive" in expenses and "↓ 60,0%" in text(expenses)   # lower expenses are favourable (inverse)


def test_equal_periods_are_neutral(app, tenants):
    for month in (6, 7):
        sale(tenants["A"], datetime(2026, month, 3, 12), 50000)
    db_session.commit()
    html, _ = render(app, tenants)
    sales_card = card(html, "kpi-sales")
    assert "delta-neutral" in sales_card and "→ 0,0%" in text(sales_card)


def test_rising_expenses_are_flagged_as_unfavourable(app, tenants):
    seed_two_months(tenants["A"]); db_session.commit()
    html, _ = render(app, tenants)
    expenses = re.search(r'<p class="trend-expenses">.*?</p>', html, re.S).group(0)
    assert "delta-negative" in expenses and "↑ 150,0%" in text(expenses)


def test_no_base_is_neutral_and_never_a_made_up_percentage(app, tenants):
    sale(tenants["A"], datetime(2026, 7, 3, 12), 100000); expense(tenants["A"], datetime(2026, 7, 4, 12), 30000)
    db_session.commit()
    html, context = render(app, tenants)
    assert context["comparison"]["has_previous_data"] is False
    for key in ("kpi-sales", "kpi-profit", "kpi-margin", "kpi-ticket"):
        fragment = card(html, key)
        assert "Sin período anterior comparable" in fragment and "delta-neutral" in fragment
        assert not re.search(r"[↑↓→]|\d,\d\s*%\s*<small>|\bpp\b", fragment), key
    lowered = html.lower()
    for artefact in ("infinity", "nan%", "inf%", "none%"):
        assert artefact not in lowered


def test_margin_without_sales_is_a_dash_not_zero_percent(app, tenants):
    expense(tenants["A"], datetime(2026, 7, 4, 12), 30000); db_session.commit()
    html, _ = render(app, tenants)
    margin = text(card(html, "kpi-margin"))
    assert margin.startswith("Margen operacional —") and "0,0%" not in margin


def test_kpi_deltas_have_text_alternatives_for_screen_readers(app, tenants):
    seed_two_months(tenants["A"]); db_session.commit()
    html, _ = render(app, tenants)
    assert '<span aria-hidden="true">↑</span><span class="visually-hidden">Aumentó</span>' in card(html, "kpi-sales")
    assert '<span class="visually-hidden">Subió:</span>' in card(html, "kpi-margin")


@pytest.mark.parametrize("value,signed,expected", [
    (12.4, False, "12,4"), (-2.1, False, "−2,1"), (2.1, True, "+2,1"), (0, True, "0,0"), (0.0, False, "0,0"),
    (-0.04, False, "0,0"), (92.7, False, "92,7"), (-10.0, True, "−10,0"), (None, False, "—"),
])
def test_pct_es_filter_formats_es_cl_decimals(app, value, signed, expected):
    assert app.jinja_env.filters["pct_es"](value, signed) == expected


# --------------------------------------------------------------------- cash

def test_cash_is_never_labelled_caja_de_jornada_and_legacy_balance_is_not_shown(app, tenants):
    tenant = tenants["A"]
    for day in (2, 3, 4):                                  # three openings of 20.000 pile up in the legacy figure
        ws = work_session(tenant, D(2026, 7, day), opening=20000, counted=20000)
        sale(tenant, datetime(2026, 7, day, 12), 10000, "cash", work_session_id=ws.id)
    db_session.commit()
    html, context = render(app, tenants)
    legacy = calculate_metrics(datetime(2026, 7, 1), datetime(2026, 7, 31, 23, 59, 59), *tenants["A"])["cash_balance"]
    assert legacy == 90000 and "$90.000" not in html and "Caja de jornada" not in html
    strip = text(re.search(r'<section class="kpi-secondary-strip".*?</section>', html, re.S).group(0))
    assert "Caja esperada" in strip and "Efectivo neto del período" in strip
    assert context["cash_net_period"] == 30000 and "$30.000" in strip


def test_cash_copy_for_an_open_session(app, tenants):
    ws = work_session(tenants["A"], D(2026, 7, 14), status="open", opening=20000)
    sale(tenants["A"], datetime(2026, 7, 14, 12), 30000, "cash", work_session_id=ws.id)
    expense(tenants["A"], datetime(2026, 7, 14, 13), 5000, "cash", work_session_id=ws.id)
    db_session.commit()
    html, _ = render(app, tenants)
    strip = text(re.search(r'<section class="kpi-secondary-strip".*?</section>', html, re.S).group(0))
    assert "Caja esperada $45.000 Jornada abierta · 14-07-2026" in strip
    assert "Efectivo neto del período $25.000 Ventas menos gastos en efectivo" in strip


def test_cash_copy_for_the_last_closed_session(app, tenants):
    ws = work_session(tenants["A"], D(2026, 7, 9), opening=10000, counted=14000)
    sale(tenants["A"], datetime(2026, 7, 9, 12), 5000, "cash", work_session_id=ws.id)
    db_session.commit()
    html, _ = render(app, tenants)
    strip = text(re.search(r'<section class="kpi-secondary-strip".*?</section>', html, re.S).group(0))
    assert "Caja esperada $15.000 Última jornada cerrada · 09-07-2026 · contado $14.000" in strip


def test_cash_copy_without_any_session(app, tenants):
    html, _ = render(app, tenants)
    strip = text(re.search(r'<section class="kpi-secondary-strip".*?</section>', html, re.S).group(0))
    assert "Caja esperada — Sin posición de caja disponible" in strip
    assert "Jornada abierta" not in strip and "Última jornada" not in strip


def test_secondary_strip_has_the_five_requested_indicators(app, tenants):
    seed_two_months(tenants["A"]); db_session.commit()
    html, _ = render(app, tenants)
    strip = re.search(r'<section class="kpi-secondary-strip".*?</section>', html, re.S).group(0)
    labels = re.findall(r"<span>(.*?)</span>", strip)
    assert labels == ["Cantidad de ventas", "Tiempo trabajado", "Caja esperada", "Efectivo neto del período", "Inversión acumulada"]


# ---------------------------------------------------------------- attention

def test_attention_panel_lists_exactly_the_f30_signals_with_existing_destinations(app, tenants):
    tenant = tenants["A"]
    work_session(tenant, D(2026, 7, 2), opening=10000, counted=9000)
    work_session(tenant, D(2026, 7, 3), opening=10000, counted=10300)
    sale(tenant, datetime(2026, 7, 2, 12), 1000)
    db_session.commit()
    html, context = render(app, tenants)
    panel = re.search(r'<article class="section-card attention-panel".*?</article>', html, re.S).group(0)
    items = re.findall(r'<li class="attention-item" data-signal="(\w+)" data-severity="(\w+)">', panel)
    assert items == [(s["code"], s["severity"]) for s in context["attention_signals"]]
    assert {code for code, _ in items} == {"cash_shortage", "cash_surplus", "unassociated_movements"}
    for signal in context["attention_signals"]:
        assert signal["title"] in panel
    assert text(panel).count("Revisar") == len(items) and 'href="/jornadas/"' in panel
    assert "Atención" in panel and "Informativa" in panel
    shortage = re.search(r'data-signal="cash_shortage".*?</li>', panel, re.S).group(0)
    assert "1 caso" in text(shortage) and "$1.000" in text(shortage)
    assert 'class="attention-count"' in panel and 'aria-labelledby="attention-title"' in html


def test_attention_panel_empty_state_copy(app, tenants):
    html, context = render(app, tenants)
    assert context["attention_signals"] == []
    assert "Sin alertas operativas" in html and "Los controles del período no requieren atención." in html
    assert 'class="attention-list"' not in html and 'class="attention-count"' not in html


def test_attention_panel_adds_no_rules_of_its_own(app, tenants):
    """Everything in the panel comes from attention_signals: with data that triggers nothing, nothing shows."""
    seed_two_months(tenants["A"])
    ws = work_session(tenants["A"], D(2026, 7, 6), counted=20000)  # balanced, normal duration
    db_session.commit()
    html, context = render(app, tenants)
    assert [s["code"] for s in context["attention_signals"]] == ["unassociated_movements"]   # sales were seeded without a session
    assert html.count('class="attention-item"') == 1


# ---------------------------------------------------------------- doughnuts

def seed_sales_mix(tenant):
    sale(tenant, datetime(2026, 7, 2, 12), 50000, "cash", "food_truck"); sale(tenant, datetime(2026, 7, 3, 12), 30000, "debit", "food_truck")
    sale(tenant, datetime(2026, 7, 4, 12), 15000, "credit", "pickup"); sale(tenant, datetime(2026, 7, 5, 12), 5000, "transfer", "delivery")
    sale(tenant, datetime(2026, 7, 6, 12), 5000, "other", "other")
    db_session.commit()


def test_sales_by_channel_doughnut_uses_translated_labels_amounts_and_percentages(app, tenants):
    seed_sales_mix(tenants["A"])
    html, _ = render(app, tenants)
    rows = chart_rows(html, "channelChart")
    assert rows == [{"label": "Food truck", "amount": 80000, "percentage": 76.2}, {"label": "Retiro", "amount": 15000, "percentage": 14.3},
                    {"label": "Delivery", "amount": 5000, "percentage": 4.8}, {"label": "Otro", "amount": 5000, "percentage": 4.8}]
    assert {row["label"] for row in rows} <= set(CHANNEL_LABELS.values())
    legend = text(re.search(r'<canvas id="channelChart".*?</ul>', html, re.S).group(0))
    for fragment in ("Food truck $80.000 76,2%", "Retiro $15.000 14,3%", "Delivery $5.000 4,8%"):
        assert fragment in legend


def test_sales_by_payment_doughnut_uses_translated_labels_amounts_and_percentages(app, tenants):
    seed_sales_mix(tenants["A"])
    html, _ = render(app, tenants)
    rows = chart_rows(html, "paymentChart")
    assert [(r["label"], r["amount"], r["percentage"]) for r in rows] == [
        ("Efectivo", 50000, 47.6), ("Débito", 30000, 28.6), ("Crédito", 15000, 14.3), ("Transferencia", 5000, 4.8), ("Otro", 5000, 4.8)]
    assert {row["label"] for row in rows} <= set(PAYMENT_LABELS.values())
    assert 'role="img" aria-label="Ventas por medio de pago: Efectivo 47,6%' in html


def test_doughnut_empty_states_are_elegant_and_have_no_canvas(app, tenants):
    html, _ = render(app, tenants)
    assert html.count("Sin ventas en el período") == 2
    assert "Los canales aparecerán cuando registres ventas." in html and "Los medios de pago aparecerán cuando registres ventas." in html
    assert 'id="channelChart"' not in html and 'id="paymentChart"' not in html
    assert 'id="dailyChart"' in html  # the main chart keeps its own empty state


def test_expenses_by_category_stays_in_the_composition_section(app, tenants):
    seed_two_months(tenants["A"])
    expense(tenants["A"], datetime(2026, 7, 8, 12), 20000, category="Gas"); db_session.commit()
    html, _ = render(app, tenants)
    composition = html[html.index(">Composición</h2>"):html.index(">Actividad y capital</h2>")]
    assert 'id="categoryChart"' in composition and "Gastos por categoría" in composition
    assert composition.count('class="section-card chart-card composition-card"') == 3


def test_templates_only_know_channels_and_payment_methods_the_model_has(app, tenants):
    seed_sales_mix(tenants["A"])
    html, _ = render(app, tenants)
    source = (ROOT / "templates/dashboard.html").read_text(encoding="utf-8")
    for haystack in (html.lower(), source.lower()):
        for foreign in ("uber", "mercado libre", "mercadolibre", "amon shop", "compraqu", "bancoestado", "rappi", "pedidosya", "justo"):
            assert foreign not in haystack, foreign


# ------------------------------------------------------------ tenant scope

def test_dashboard_never_renders_other_tenants_or_branches(app, tenants):
    seed_two_months(tenants["A"]); seed_sales_mix(tenants["A"])
    for other, amount in ((tenants["B"], 7_777_000), (tenants["A2"], 6_666_000)):
        for month in (6, 7):
            sale(other, datetime(2026, month, 9, 12), amount, "transfer", "delivery")
        work_session(other, D(2026, 7, 2), opening=1, counted=999)   # a cash-difference signal for the others
    db_session.commit()
    html, context = render(app, tenants)
    for foreign in ("7.777.000", "6.666.000"):
        assert foreign not in html
    assert all(s["code"] != "cash_shortage" for s in context["attention_signals"])
    assert sum(row["amount"] for row in chart_rows(html, "channelChart")) == context["metrics"]["total_sales"]


# ------------------------------------------------------------ themes / JS / CSS

def test_chart_script_is_theme_aware_and_respects_reduced_motion():
    js = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    body = js[js.index("function buildCompositionChart"):js.index("function rebuildCharts")]
    assert "cssToken(" in body and not re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(", body)          # colours come from theme tokens
    assert 'buildCompositionChart("channelChart"' in js and 'buildCompositionChart("paymentChart"' in js
    assert "prefers-reduced-motion: reduce" in js and "Chart.defaults.animation" in js
    assert "rebuildCharts();" in js[js.index("function bindThemeControl"):js.index("function parseChartData")]   # theme switch rebuilds
    assert 'legend: { display: false }' in body                                                      # legend is server-rendered
    assert "setChartEmpty(element, true)" in body and "chartInstances.push" in body


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_app_js_still_parses():
    subprocess.run(["node", "--check", str(ROOT / "static/js/app.js")], check=True)


def test_cockpit_css_uses_theme_tokens_and_has_responsive_rules():
    css = (ROOT / "static/css/app.css").read_text(encoding="utf-8")
    block = css[css.index("/* F3.1 Business Cockpit */"):css.index("@layer print")]
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(", block)                                      # no hardcoded colours: light and dark both work
    for token in ("--chart-cyan", "--chart-green", "--chart-amber", "--chart-sand", "--chart-muted", "--amber-soft", "--cyan-soft"):
        assert css.count(f"{token}:") >= 2, token                                                    # defined in light and dark themes
    assert ".dashboard-grid-composition { grid-template-columns: repeat(3, minmax(0, 1fr)); }" in block
    assert re.search(r"@media \(max-width: 1240px\) \{ \.dashboard-grid-composition \{ grid-template-columns: repeat\(2", block)
    assert re.search(r"@media \(max-width: 760px\) \{\s*\.dashboard-grid-composition \{ grid-template-columns: 1fr; \}", block)
    assert ".visually-hidden" in block and "gradient" not in block and "animation" not in block      # calm: no gradients/animations added
    assert not re.search(r"overflow(-y)?:\s*(auto|scroll)", block)                                   # no new inner scroll regions
    for kept in ("@media (prefers-reduced-motion: reduce)", ".movement-list-scroll { max-height: 260px;"):
        assert kept in css


def test_existing_theme_controls_and_shell_are_untouched(app, tenants):
    html, _ = render(app, tenants)
    assert 'role="group" aria-label="Apariencia" data-theme-control' in html
    for value in ("auto", "light", "dark"):
        assert f'data-theme-value="{value}"' in html
    assert "<title>Resumen financiero · AMON ERP</title>" in html and "<h1>Resumen financiero</h1>" in html

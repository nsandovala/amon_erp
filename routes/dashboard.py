from datetime import datetime

from flask import Blueprint, render_template, request

from models import db_session
from models.work_session import WorkSession
from services.metrics import (
    calculate_metrics,
    date_bounds,
    expenses_by_category,
    investments_by_category,
    latest_movements,
    monthly_summary,
    sales_expenses_by_day,
)


dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def index():
    period = request.args.get("period", "month")
    start = _parse_date(request.args.get("start"))
    end = _parse_date(request.args.get("end"))
    start_dt, end_dt, start_date, end_date = date_bounds(period, start, end)
    sessions = (
        db_session.query(WorkSession)
        .filter(WorkSession.status.in_(["open", "closed"]))
        .order_by(WorkSession.opened_at.desc())
        .limit(8)
        .all()
    )
    return render_template(
        "dashboard.html",
        period=period,
        start_date=start_date,
        end_date=end_date,
        metrics=calculate_metrics(start_dt, end_dt),
        daily_chart=sales_expenses_by_day(start_date, end_date),
        category_chart=expenses_by_category(start_dt, end_dt),
        investment_chart=investments_by_category(start_dt, end_dt),
        latest_movements=latest_movements(),
        monthly_rows=monthly_summary(start_date.year),
        recent_sessions=sessions,
    )


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None

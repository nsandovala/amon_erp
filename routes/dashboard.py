from datetime import datetime

from flask import Blueprint, g, render_template, request

from models import db_session
from models.work_session import WorkSession
from services.metrics import (
    calculate_metrics,
    calculate_return_estimate,
    date_bounds,
    expenses_by_category,
    investments_by_category,
    latest_movements,
    monthly_summary,
    sales_expenses_by_day,
)
from services.work_sessions import calculate_work_session_metrics
from services.tenancy import scope_query


dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def index():
    organization_id = getattr(g, "organization_id", None)
    branch_id = getattr(g, "branch_id", None)
    period = request.args.get("period", "month")
    start = _parse_date(request.args.get("start"))
    end = _parse_date(request.args.get("end"))
    start_dt, end_dt, start_date, end_date = date_bounds(period, start, end)
    sessions = (
        scope_query(db_session.query(WorkSession), WorkSession, required=True)
        .filter(WorkSession.status.in_(["open", "closed"]), WorkSession.deleted_at.is_(None))
        .order_by(WorkSession.opened_at.desc())
        .limit(8)
        .all()
    )
    cash_differences = []
    for work_session in sessions:
        session_metrics = calculate_work_session_metrics(work_session)
        if work_session.status == "closed" and session_metrics.cash_difference:
            cash_differences.append({"session": work_session, "metrics": session_metrics})
    return render_template(
        "dashboard.html",
        period=period,
        start_date=start_date,
        end_date=end_date,
        metrics=calculate_metrics(start_dt, end_dt, organization_id, branch_id),
        daily_chart=sales_expenses_by_day(start_date, end_date, organization_id, branch_id),
        category_chart=expenses_by_category(start_dt, end_dt, organization_id, branch_id),
        investment_chart=investments_by_category(start_dt, end_dt, organization_id, branch_id),
        latest_movements=latest_movements(organization_id=organization_id, branch_id=branch_id),
        monthly_rows=monthly_summary(start_date.year, organization_id, branch_id),
        recent_sessions=sessions,
        cash_differences=cash_differences,
        return_estimate=calculate_return_estimate(organization_id, branch_id),
    )


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None

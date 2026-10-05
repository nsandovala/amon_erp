from flask import Blueprint, abort, g, redirect, render_template, request, session, url_for

from services.tenancy import TenantResolutionError, TenantSelectionRequired, branches_for, resolve_request_tenant, select_tenant_context, tenant_options


tenant_context_bp = Blueprint("tenant_context", __name__, url_prefix="/contexto")


@tenant_context_bp.route("/", methods=["GET", "POST"])
def selector():
    user_id = getattr(g, "user_id", None)
    if not user_id:
        abort(403)
    memberships = tenant_options(user_id)
    if not memberships:
        abort(403)
    selected_org_id = request.form.get("organization_id", type=int) if request.method == "POST" else None
    if request.method == "POST":
        selected_branch_id = request.form.get("branch_id", type=int)
        try:
            select_tenant_context(user_id, selected_org_id, selected_branch_id)
        except (TenantResolutionError, TenantSelectionRequired):
            abort(403)
        return redirect(url_for("dashboard.index"))
    try:
        resolve_request_tenant(user_id)
        # An explicit request (?force=1) opens the selector instead of auto-resolving.
        # It only changes what is shown: every POST is still validated server-side.
        if request.args.get("force") != "1":
            return redirect(url_for("dashboard.index"))
    except TenantSelectionRequired:
        pass
    except TenantResolutionError:
        abort(403)
    return render_template(
        "tenant_context/select.html",
        memberships=memberships,
        branches_by_organization={item.organization_id: [{"id": branch.id, "name": branch.name} for branch in branches_for(item.organization_id)] for item in memberships},
        selected_organization_id=session.get("active_organization_id") or getattr(g, "organization_id", None),
        selected_branch_id=session.get("active_branch_id") or getattr(g, "branch_id", None),
    )

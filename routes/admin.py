from flask import Blueprint, abort, flash, g, redirect, render_template, request, session, url_for
from sqlalchemy.exc import IntegrityError

from models import db_session
from models.branch import Branch
from models.membership import MEMBERSHIP_ROLES, Membership
from models.organization import ORGANIZATION_ENTITY_TYPES, Organization
from services.audit import create_audit_log
from services.authorization import require_admin_view, require_owner
from services.tenant_admin import change_membership_role, change_membership_status, create_branch, create_membership
from services.tenancy import branches_for


admin_bp = Blueprint("admin", __name__, url_prefix="/administracion")


def _organization_or_404():
    organization = getattr(g, "organization", None)
    return organization or abort(403)


def _commit(message):
    try:
        db_session.commit()
        flash(message, "success")
    except IntegrityError:
        db_session.rollback()
        flash("No se pudo guardar: el slug o la membresía ya existe.", "error")
    return redirect(url_for("admin.index"))


@admin_bp.get("/")
@require_admin_view
def index():
    organization = _organization_or_404()
    return render_template(
        "admin/index.html", organization=organization, branches=branches_for(organization.id),
        memberships=db_session.query(Membership).filter(Membership.organization_id == organization.id).order_by(Membership.clerk_user_id).all(),
        roles=MEMBERSHIP_ROLES, entity_types=ORGANIZATION_ENTITY_TYPES,
    )


@admin_bp.post("/organizacion")
@require_owner
def update_organization():
    organization = _organization_or_404()
    old = {"name": organization.name, "legal_name": organization.legal_name, "tax_id": organization.tax_id, "entity_type": organization.entity_type}
    entity_type = request.form.get("entity_type")
    if entity_type not in ORGANIZATION_ENTITY_TYPES or not (request.form.get("name") or "").strip():
        abort(400)
    organization.name = request.form["name"].strip()
    organization.legal_name = (request.form.get("legal_name") or "").strip() or None
    organization.tax_id = (request.form.get("tax_id") or "").strip() or None
    organization.entity_type = entity_type
    db_session.add(create_audit_log("organization.updated", "organization", organization.id, old, {"name": organization.name, "legal_name": organization.legal_name, "tax_id": organization.tax_id, "entity_type": entity_type}))
    return _commit("Organización actualizada.")


@admin_bp.post("/sucursales")
@require_owner
def add_branch():
    organization = _organization_or_404()
    try:
        branch = create_branch(organization.id, request.form.get("name"), request.form.get("slug"))
        db_session.flush()
    except ValueError:
        db_session.rollback(); abort(400)
    db_session.add(create_audit_log("branch.created", "branch", branch.id, None, {"name": branch.name, "slug": branch.slug, "status": branch.status}))
    return _commit("Sucursal creada.")


def _branch_or_404(branch_id):
    return db_session.query(Branch).filter(Branch.id == branch_id, Branch.organization_id == _organization_or_404().id).one_or_none() or abort(404)


@admin_bp.post("/sucursales/<int:branch_id>")
@require_owner
def update_branch(branch_id):
    branch = _branch_or_404(branch_id)
    old = {"name": branch.name, "slug": branch.slug}
    name, slug = (request.form.get("name") or "").strip(), (request.form.get("slug") or "").strip()
    if not name or not slug: abort(400)
    branch.name, branch.slug = name, slug
    db_session.add(create_audit_log("branch.updated", "branch", branch.id, old, {"name": name, "slug": slug}))
    return _commit("Sucursal actualizada.")


@admin_bp.post("/sucursales/<int:branch_id>/archivar")
@require_owner
def archive_branch(branch_id):
    branch = _branch_or_404(branch_id)
    branch.status = "archived"
    db_session.add(create_audit_log("branch.archived", "branch", branch.id, {"status": "active"}, {"status": "archived"}))
    response = _commit("Sucursal archivada.")
    if branch.id == getattr(g, "branch_id", None):
        session.pop("active_branch_id", None)
        return redirect(url_for("tenant_context.selector"))
    return response


def _membership_or_404(membership_id):
    organization = _organization_or_404()
    return db_session.query(Membership).filter(Membership.id == membership_id, Membership.organization_id == organization.id).one_or_none() or abort(404)


@admin_bp.post("/accesos")
@require_owner
def add_membership():
    organization = _organization_or_404()
    try:
        membership = create_membership(organization.id, request.form.get("clerk_user_id"), request.form.get("role"))
        db_session.flush()
    except ValueError:
        db_session.rollback(); abort(400)
    db_session.add(create_audit_log("membership.created", "membership", membership.id, None, {"clerk_user_id": membership.clerk_user_id, "role": membership.role, "status": membership.status}))
    return _commit("Acceso creado.")


@admin_bp.post("/accesos/<int:membership_id>/rol")
@require_owner
def update_membership_role(membership_id):
    membership = _membership_or_404(membership_id)
    old = {"role": membership.role}
    try: change_membership_role(membership, request.form.get("role"))
    except ValueError: abort(400)
    db_session.add(create_audit_log("membership.role_changed", "membership", membership.id, old, {"role": membership.role}))
    return _commit("Rol actualizado.")


@admin_bp.post("/accesos/<int:membership_id>/estado")
@require_owner
def update_membership_status(membership_id):
    membership = _membership_or_404(membership_id)
    old = {"status": membership.status}
    try: change_membership_status(membership, request.form.get("status"))
    except ValueError: abort(400)
    action = "membership.reactivated" if membership.status == "active" else "membership.deactivated"
    db_session.add(create_audit_log(action, "membership", membership.id, old, {"status": membership.status}))
    return _commit("Estado de acceso actualizado.")

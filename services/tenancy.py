"""Validated request tenant context and server-side query scoping."""

from flask import abort, g, has_request_context, session

from models import db_session
from models.branch import Branch
from models.membership import Membership
from models.organization import Organization


class TenantResolutionError(Exception):
    pass


class TenantSelectionRequired(TenantResolutionError):
    pass


def tenant_options(user_id):
    """Return only active local tenants available to an authenticated identity."""
    memberships = (
        db_session.query(Membership)
        .join(Organization)
        .filter(
            Membership.clerk_user_id == user_id,
            Membership.status == "active",
            Organization.status == "active",
        )
        .all()
    )
    return memberships


def branches_for(organization_id):
    return db_session.query(Branch).filter(
        Branch.organization_id == organization_id, Branch.status == "active"
    ).order_by(Branch.name).all()


def clear_tenant_selection():
    session.pop("active_organization_id", None)
    session.pop("active_branch_id", None)


def resolve_request_tenant(user_id):
    """Resolve a validated local tenant context; never authorize raw session IDs."""
    memberships = tenant_options(user_id)
    if not memberships:
        clear_tenant_selection()
        raise TenantResolutionError("Esta cuenta no tiene una organización activa.")

    requested_org_id = session.get("active_organization_id")
    if requested_org_id is None:
        if len(memberships) != 1:
            raise TenantSelectionRequired("Selecciona una organización.")
        membership = memberships[0]
    else:
        membership = next((item for item in memberships if item.organization_id == requested_org_id), None)
        if membership is None:
            clear_tenant_selection()
            raise TenantSelectionRequired("La organización seleccionada ya no está disponible.")

    branches = branches_for(membership.organization_id)
    if not branches:
        clear_tenant_selection()
        raise TenantResolutionError("La organización no tiene sucursales activas.")
    requested_branch_id = session.get("active_branch_id")
    if requested_branch_id is None:
        if len(branches) != 1:
            raise TenantSelectionRequired("Selecciona una sucursal.")
        branch = branches[0]
    else:
        branch = next((item for item in branches if item.id == requested_branch_id), None)
        if branch is None:
            session.pop("active_branch_id", None)
            raise TenantSelectionRequired("La sucursal seleccionada ya no está disponible.")

    g.membership = membership
    g.erp_role = membership.role
    g.organization = membership.organization
    g.organization_id = membership.organization_id
    g.branch = branch
    g.branch_id = branch.id
    return membership


def select_tenant_context(user_id, organization_id, branch_id=None):
    """Validate a selector POST before persisting it in the signed server session."""
    membership = next((item for item in tenant_options(user_id) if item.organization_id == organization_id), None)
    if membership is None:
        clear_tenant_selection()
        raise TenantResolutionError("Organización no autorizada.")
    branches = branches_for(organization_id)
    if not branches:
        raise TenantResolutionError("La organización no tiene sucursales activas.")
    if branch_id is None:
        if len(branches) != 1:
            raise TenantSelectionRequired("Selecciona una sucursal.")
        branch_id = branches[0].id
    if not any(branch.id == branch_id for branch in branches):
        raise TenantResolutionError("Sucursal no autorizada.")
    session["active_organization_id"] = organization_id
    session["active_branch_id"] = branch_id
    return resolve_request_tenant(user_id)


def current_tenant_ids(required=False):
    organization_id = getattr(g, "organization_id", None) if has_request_context() else None
    branch_id = getattr(g, "branch_id", None) if has_request_context() else None
    if required and getattr(g, "tenant_enforced", True) and (organization_id is None or branch_id is None):
        abort(403)
    return organization_id, branch_id


def scope_query(query, model, required=False):
    organization_id, branch_id = current_tenant_ids(required=required)
    if organization_id is None:
        return query
    return query.filter(model.organization_id == organization_id, model.branch_id == branch_id)


def scoped_resource_or_404(model, resource_id, include_deleted=True):
    query = scope_query(db_session.query(model), model, required=True).filter(model.id == resource_id)
    if not include_deleted:
        query = query.filter(model.deleted_at.is_(None))
    return query.one_or_none() or abort(404)


def apply_tenant_fields(entity):
    organization_id, branch_id = current_tenant_ids(required=True)
    entity.organization_id = organization_id
    entity.branch_id = branch_id
    return entity


def same_tenant(left, right):
    return (
        left.organization_id == right.organization_id
        and left.branch_id == right.branch_id
    )

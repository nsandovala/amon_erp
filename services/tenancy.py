"""Validated request tenant context and server-side query scoping."""

from flask import abort, g, has_request_context, session

from models import db_session
from models.branch import Branch
from models.membership import Membership
from models.organization import Organization


class TenantResolutionError(Exception):
    pass


def resolve_request_tenant(user_id):
    """Resolve membership and branch without trusting browser-provided IDs."""
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
    requested_org_id = session.get("active_organization_id")
    if requested_org_id is not None:
        memberships = [item for item in memberships if item.organization_id == requested_org_id]
    if len(memberships) != 1:
        raise TenantResolutionError("No se pudo resolver una organización activa.")

    membership = memberships[0]
    branches = (
        db_session.query(Branch)
        .filter(Branch.organization_id == membership.organization_id, Branch.status == "active")
        .all()
    )
    requested_branch_id = session.get("active_branch_id")
    if requested_branch_id is not None:
        branches = [item for item in branches if item.id == requested_branch_id]
    if len(branches) != 1:
        raise TenantResolutionError("No se pudo resolver una sucursal activa.")

    g.membership = membership
    g.erp_role = membership.role
    g.organization = membership.organization
    g.organization_id = membership.organization_id
    g.branch = branches[0]
    g.branch_id = branches[0].id
    return membership


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

"""Validated mutations for local tenant administration."""
from models import db_session
from models.branch import Branch
from models.membership import MEMBERSHIP_ROLES, Membership


def active_owner_count(organization_id):
    return db_session.query(Membership).filter(
        Membership.organization_id == organization_id,
        Membership.role == "owner",
        Membership.status == "active",
    ).count()


def ensure_owner_can_change(membership, role=None, status=None):
    removes_active_owner = (
        membership.role == "owner" and membership.status == "active"
        and ((role is not None and role != "owner") or status == "inactive")
    )
    if removes_active_owner and active_owner_count(membership.organization_id) <= 1:
        raise ValueError("La organización debe conservar al menos un owner activo.")


def create_membership(organization_id, clerk_user_id, role):
    if role not in MEMBERSHIP_ROLES:
        raise ValueError("Rol inválido.")
    user_id = (clerk_user_id or "").strip()
    if not user_id:
        raise ValueError("El Clerk user ID es obligatorio.")
    if db_session.query(Membership).filter(
        Membership.organization_id == organization_id, Membership.clerk_user_id == user_id,
    ).first():
        raise ValueError("La membresía ya existe.")
    membership = Membership(organization_id=organization_id, clerk_user_id=user_id, role=role, status="active")
    db_session.add(membership)
    return membership


def change_membership_role(membership, role):
    if role not in MEMBERSHIP_ROLES:
        raise ValueError("Rol inválido.")
    ensure_owner_can_change(membership, role=role)
    membership.role = role
    return membership


def change_membership_status(membership, status):
    if status not in ("active", "inactive"):
        raise ValueError("Estado inválido.")
    ensure_owner_can_change(membership, status=status)
    membership.status = status
    return membership


def create_branch(organization_id, name, slug):
    branch = Branch(organization_id=organization_id, name=(name or "").strip(), slug=(slug or "").strip())
    if not branch.name or not branch.slug:
        raise ValueError("Nombre y slug son obligatorios.")
    db_session.add(branch)
    return branch

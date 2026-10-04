import pytest
from flask import g, session

from models import db_session
from models.branch import Branch
from models.membership import Membership
from models.organization import Organization
from services.tenant_admin import change_membership_role, change_membership_status, create_membership
from services.tenancy import TenantResolutionError, TenantSelectionRequired, resolve_request_tenant, select_tenant_context


def _tenant(name, slug, user_id):
    organization = Organization(name=name, slug=slug, entity_type="company")
    db_session.add(organization); db_session.flush()
    branch = Branch(organization_id=organization.id, name="Principal", slug="principal")
    db_session.add(branch); db_session.add(Membership(organization_id=organization.id, clerk_user_id=user_id, role="owner")); db_session.flush()
    return organization, branch


def test_context_auto_resolves_one_org_and_branch(app):
    with app.app_context(), app.test_request_context("/"):
        organization, branch = _tenant("The Best Burger", "tbb", "user_a"); db_session.commit()
        resolve_request_tenant("user_a")
        assert (g.organization_id, g.branch_id) == (organization.id, branch.id)


def test_context_requires_selection_and_rejects_foreign_branch(app):
    with app.app_context(), app.test_request_context("/"):
        first, first_branch = _tenant("The Best Burger", "tbb", "user_a")
        second, second_branch = _tenant("2MUCH", "2much", "user_a")
        db_session.commit()
        with pytest.raises(TenantSelectionRequired): resolve_request_tenant("user_a")
        with pytest.raises(TenantResolutionError): select_tenant_context("user_a", first.id, second_branch.id)
        select_tenant_context("user_a", first.id, first_branch.id)
        assert session["active_organization_id"] == first.id


def test_archived_context_and_last_owner_are_rejected(app):
    with app.app_context(), app.test_request_context("/"):
        organization, branch = _tenant("The Best Burger", "tbb", "user_a"); db_session.commit()
        owner = db_session.query(Membership).one()
        with pytest.raises(ValueError): change_membership_status(owner, "inactive")
        with pytest.raises(ValueError): change_membership_role(owner, "operator")
        organization.status = "archived"; db_session.commit()
        with pytest.raises(TenantResolutionError): resolve_request_tenant("user_a")


def test_memberships_are_unique_and_second_owner_allows_change(app):
    with app.app_context():
        organization, _branch = _tenant("The Best Burger", "tbb", "user_a")
        db_session.commit()
        with pytest.raises(ValueError): create_membership(organization.id, "user_a", "owner")
        second = create_membership(organization.id, "user_b", "owner"); db_session.commit()
        owner = db_session.query(Membership).filter(Membership.clerk_user_id == "user_a").one()
        change_membership_role(owner, "manager")
        assert second.role == "owner"

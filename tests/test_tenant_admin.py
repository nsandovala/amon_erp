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


def _org_with_branches(slug, count):
    organization = Organization(name=slug, slug=slug, entity_type="company")
    db_session.add(organization); db_session.flush()
    branches = [Branch(organization_id=organization.id, name=f"{slug}-{i}", slug=f"b{i}") for i in range(count)]
    db_session.add_all(branches); db_session.flush()
    return organization, branches


def test_last_active_branch_cannot_be_archived(app):
    from services.tenant_admin import archive_branch
    _org, (only,) = _org_with_branches("solo", 1)
    with pytest.raises(ValueError, match="al menos una sucursal activa"):
        archive_branch(only)
    assert only.status == "active"


def test_branch_can_be_archived_until_one_remains(app):
    from services.tenant_admin import archive_branch
    _org, (first, second) = _org_with_branches("dos", 2)
    archive_branch(first)
    assert first.status == "archived"
    with pytest.raises(ValueError):
        archive_branch(second)
    assert second.status == "active"


def test_other_organizations_branches_never_count_for_the_invariant(app):
    from services.tenant_admin import active_branch_count, archive_branch
    _org_a, (only_a,) = _org_with_branches("a", 1)
    _org_b, _branches_b = _org_with_branches("b", 3)
    assert active_branch_count(only_a.organization_id) == 1
    with pytest.raises(ValueError):
        archive_branch(only_a)
    assert only_a.status == "active"


def test_archived_branches_do_not_count_and_cannot_be_archived_twice(app):
    from services.tenant_admin import archive_branch
    _org, (first, second, third) = _org_with_branches("tres", 3)
    archive_branch(first)
    with pytest.raises(ValueError, match="ya no está activa"):
        archive_branch(first)
    archive_branch(second)
    with pytest.raises(ValueError, match="al menos una"):
        archive_branch(third)

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateTable

from models import db_session
from models.branch import Branch
from models.membership import MEMBERSHIP_ROLES, Membership
from models.organization import Organization
from models.sale import Sale
from services.organizations import (
    PRINCIPAL_BRANCH_SLUG,
    THE_BEST_BURGER_SLUG,
    bootstrap_the_best_burger,
)


def create_organization(slug="example"):
    organization = Organization(name="Example", slug=slug, entity_type="company")
    db_session.add(organization)
    db_session.commit()
    return organization


def test_organization_creation(app):
    organization = create_organization()

    assert organization.id is not None
    assert organization.status == "active"
    assert organization.entity_type == "company"


def test_branch_belongs_to_organization(app):
    organization = create_organization()
    branch = Branch(organization_id=organization.id, name="Centro", slug="centro")
    db_session.add(branch)
    db_session.commit()

    assert branch.organization == organization
    assert organization.branches == [branch]


def test_branch_slug_is_unique_within_its_organization(app):
    first = create_organization("first")
    second = create_organization("second")
    db_session.add_all([
        Branch(organization_id=first.id, name="Principal", slug="principal"),
        Branch(organization_id=second.id, name="Principal", slug="principal"),
    ])
    db_session.commit()

    db_session.add(Branch(organization_id=first.id, name="Duplicada", slug="principal"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_membership_belongs_to_organization_and_accepts_valid_roles(app):
    organization = create_organization()
    membership = Membership(
        organization_id=organization.id,
        clerk_user_id="user_123",
        role="owner",
    )
    db_session.add(membership)
    db_session.commit()

    assert membership.organization == organization
    assert membership.role in MEMBERSHIP_ROLES


def test_invalid_membership_role_is_rejected_by_database(app):
    organization = create_organization()
    db_session.add(Membership(
        organization_id=organization.id,
        clerk_user_id="user_123",
        role="untrusted_clerk_role",
    ))

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_membership_is_unique_per_clerk_user_and_organization(app):
    organization = create_organization()
    db_session.add(Membership(organization_id=organization.id, clerk_user_id="user_123", role="operator"))
    db_session.commit()

    db_session.add(Membership(organization_id=organization.id, clerk_user_id="user_123", role="manager"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_tbb_bootstrap_is_idempotent_and_does_not_modify_financial_rows(app):
    sale = Sale(amount=15000, payment_method="cash", channel="food_truck", description="Histórica")
    db_session.add(sale)
    db_session.commit()

    organization, branch = bootstrap_the_best_burger()
    db_session.commit()
    repeated_organization, repeated_branch = bootstrap_the_best_burger()
    db_session.commit()

    assert organization.id == repeated_organization.id
    assert branch.id == repeated_branch.id
    assert organization.slug == THE_BEST_BURGER_SLUG
    assert branch.slug == PRINCIPAL_BRANCH_SLUG
    assert db_session.get(Sale, sale.id).amount == 15000
    assert db_session.query(Organization).count() == 1
    assert db_session.query(Branch).count() == 1


def test_tenant_tables_compile_for_postgresql_and_use_foreign_keys(app):
    postgres_sql = str(CreateTable(Branch.__table__).compile(dialect=postgresql.dialect()))
    sqlite_engine = create_engine("sqlite:///:memory:")

    assert "FOREIGN KEY(organization_id) REFERENCES organizations (id)" in postgres_sql
    assert "UNIQUE (organization_id, slug)" in postgres_sql
    assert sqlite_engine.dialect.name == "sqlite"

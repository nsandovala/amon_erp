"""Local organization bootstrap helpers.

Clerk authenticates users only. Tenant membership and ERP roles stay in this
database and are intentionally not inferred from Clerk claims.
"""

from models import db_session
from models.branch import Branch
from models.organization import Organization


THE_BEST_BURGER_SLUG = "the-best-burger"
PRINCIPAL_BRANCH_SLUG = "principal"


def bootstrap_the_best_burger():
    """Create the legacy tenant root exactly once without touching finance rows.

    Financial records gain explicit tenant foreign keys in the dedicated F2.1
    migration. Keeping this bootstrap separate prevents a partial, unsafe
    tenant-isolation rollout.
    """
    organization = (
        db_session.query(Organization)
        .filter(Organization.slug == THE_BEST_BURGER_SLUG)
        .one_or_none()
    )
    if organization is None:
        organization = Organization(
            name="The Best Burger",
            slug=THE_BEST_BURGER_SLUG,
            entity_type="company",
            status="active",
        )
        db_session.add(organization)
        db_session.flush()

    branch = (
        db_session.query(Branch)
        .filter(
            Branch.organization_id == organization.id,
            Branch.slug == PRINCIPAL_BRANCH_SLUG,
        )
        .one_or_none()
    )
    if branch is None:
        branch = Branch(
            organization_id=organization.id,
            name="Principal",
            slug=PRINCIPAL_BRANCH_SLUG,
            status="active",
        )
        db_session.add(branch)
        db_session.flush()

    return organization, branch

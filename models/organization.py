from sqlalchemy import CheckConstraint, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from models import Base, now_santiago


ORGANIZATION_ENTITY_TYPES = ("natural_person", "company")
TENANT_STATUSES = ("active", "archived")


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    slug = Column(String(120), nullable=False, unique=True, index=True)
    legal_name = Column(String(180), nullable=True)
    tax_id = Column(String(40), nullable=True)
    entity_type = Column(String(20), nullable=False, default="company")
    status = Column(String(20), nullable=False, default="active", index=True)
    created_at = Column(DateTime, nullable=False, default=now_santiago)
    updated_at = Column(DateTime, nullable=False, default=now_santiago, onupdate=now_santiago)

    branches = relationship("Branch", back_populates="organization")
    memberships = relationship("Membership", back_populates="organization")

    __table_args__ = (
        CheckConstraint(
            "entity_type IN ('natural_person', 'company')",
            name="ck_organization_entity_type",
        ),
        CheckConstraint("status IN ('active', 'archived')", name="ck_organization_status"),
    )

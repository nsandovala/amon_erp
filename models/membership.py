from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from models import Base, now_santiago


MEMBERSHIP_ROLES = ("owner", "manager", "operator", "accountant_readonly")
MEMBERSHIP_STATUSES = ("active", "inactive")


class Membership(Base):
    __tablename__ = "memberships"

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    clerk_user_id = Column(String(128), nullable=False)
    role = Column(String(32), nullable=False)
    status = Column(String(20), nullable=False, default="active", index=True)
    created_at = Column(DateTime, nullable=False, default=now_santiago)
    updated_at = Column(DateTime, nullable=False, default=now_santiago, onupdate=now_santiago)

    organization = relationship("Organization", back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("organization_id", "clerk_user_id", name="uq_membership_organization_clerk_user"),
        CheckConstraint(
            "role IN ('owner', 'manager', 'operator', 'accountant_readonly')",
            name="ck_membership_role",
        ),
        CheckConstraint("status IN ('active', 'inactive')", name="ck_membership_status"),
    )

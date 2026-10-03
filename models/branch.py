from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from models import Base, now_santiago


class Branch(Base):
    __tablename__ = "branches"

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    slug = Column(String(120), nullable=False)
    status = Column(String(20), nullable=False, default="active", index=True)
    created_at = Column(DateTime, nullable=False, default=now_santiago)
    updated_at = Column(DateTime, nullable=False, default=now_santiago, onupdate=now_santiago)

    organization = relationship("Organization", back_populates="branches")

    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_branch_organization_slug"),
        CheckConstraint("status IN ('active', 'archived')", name="ck_branch_status"),
    )

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from models import Base, now_santiago


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True, index=True)
    actor_user_id = Column(String(128), nullable=True, index=True)
    action = Column(String(80), nullable=False, index=True)
    entity_type = Column(String(40), nullable=False, index=True)
    entity_id = Column(Integer, nullable=False, index=True)
    old_values = Column(Text, nullable=True)
    new_values = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=now_santiago, index=True)

    organization = relationship("Organization")
    branch = relationship("Branch")

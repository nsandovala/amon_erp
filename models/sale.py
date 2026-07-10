from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from models import Base, now_santiago


PAYMENT_METHODS = ("cash", "debit", "credit", "transfer", "other")
SALE_CHANNELS = ("food_truck", "pickup", "delivery", "other")
MOVEMENT_STATUSES = ("active", "archived")


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True)
    work_session_id = Column(Integer, ForeignKey("work_sessions.id"), nullable=True, index=True)
    occurred_at = Column(DateTime, nullable=False, default=now_santiago, index=True)
    amount = Column(Integer, nullable=False)
    payment_method = Column(String(20), nullable=False, default="cash")
    channel = Column(String(20), nullable=False, default="food_truck")
    description = Column(String(160), nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="active", index=True)
    created_at = Column(DateTime, nullable=False, default=now_santiago)
    updated_at = Column(DateTime, nullable=False, default=now_santiago, onupdate=now_santiago)
    deleted_at = Column(DateTime, nullable=True, index=True)

    work_session = relationship("WorkSession", back_populates="sales")

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_sale_amount_positive"),
        CheckConstraint("payment_method IN ('cash', 'debit', 'credit', 'transfer', 'other')", name="ck_sale_payment_method"),
        CheckConstraint("channel IN ('food_truck', 'pickup', 'delivery', 'other')", name="ck_sale_channel"),
        CheckConstraint("status IN ('active', 'archived')", name="ck_sale_status"),
    )

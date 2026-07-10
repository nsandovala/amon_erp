from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from models import Base, now_santiago
from models.sale import PAYMENT_METHODS, MOVEMENT_STATUSES


EXPENSE_TYPES = ("operational", "investment")
EXPENSE_CATEGORIES = (
    "Inversión food truck",
    "Equipamiento",
    "Insumos",
    "Proveedores",
    "Gas",
    "Luz",
    "Agua",
    "Traslado",
    "Combustible",
    "Trámites",
    "Permisos",
    "Mantención",
    "Reparaciones",
    "Marketing",
    "Comisiones",
    "Gastos operacionales",
    "Otros",
)


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True)
    work_session_id = Column(Integer, ForeignKey("work_sessions.id"), nullable=True, index=True)
    occurred_at = Column(DateTime, nullable=False, default=now_santiago, index=True)
    amount = Column(Integer, nullable=False)
    category = Column(String(80), nullable=False)
    expense_type = Column(String(20), nullable=False, default="operational", index=True)
    supplier = Column(String(120), nullable=True)
    payment_method = Column(String(20), nullable=False, default="cash")
    description = Column(String(160), nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="active", index=True)
    created_at = Column(DateTime, nullable=False, default=now_santiago)
    updated_at = Column(DateTime, nullable=False, default=now_santiago, onupdate=now_santiago)
    deleted_at = Column(DateTime, nullable=True, index=True)

    work_session = relationship("WorkSession", back_populates="expenses")

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_expense_amount_positive"),
        CheckConstraint("expense_type IN ('operational', 'investment')", name="ck_expense_type"),
        CheckConstraint("payment_method IN ('cash', 'debit', 'credit', 'transfer', 'other')", name="ck_expense_payment_method"),
        CheckConstraint("status IN ('active', 'archived')", name="ck_expense_status"),
    )

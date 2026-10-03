from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from models import Base, now_santiago
from models.sale import PAYMENT_METHODS, MOVEMENT_STATUSES


EXPENSE_TYPES = ("operational", "investment")
EXPENSE_CATEGORY_CATALOG = {
    "operational": (
        "Insumos",
        "Luz",
        "Agua",
        "Gas",
        "Internet y telefonía",
        "Packaging",
        "Combustible",
        "Delivery / courier",
        "Comisiones de pago",
        "Arriendo",
        "Personal",
        "Limpieza",
        "Mantención y reparaciones",
        "Marketing recurrente",
        "Otros operacionales",
    ),
    "investment": (
        "Equipamiento",
        "Mobiliario",
        "Infraestructura y adecuaciones",
        "Permisos y habilitación",
        "Traslado y puesta en marcha",
        "Marketing de lanzamiento",
        "Software e implementación",
        "Mantenimiento mayor o mejoras",
        "Otros de inversión",
    ),
}
EXPENSE_CATEGORIES = tuple(
    category
    for expense_type in EXPENSE_TYPES
    for category in EXPENSE_CATEGORY_CATALOG[expense_type]
)
LEGACY_EXPENSE_CATEGORIES = (
    "Inversión food truck",
    "Proveedores",
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
KNOWN_EXPENSE_CATEGORIES = tuple(dict.fromkeys((*EXPENSE_CATEGORIES, *LEGACY_EXPENSE_CATEGORIES)))


def expense_categories_for(expense_type, current_category=None):
    categories = EXPENSE_CATEGORY_CATALOG.get(expense_type, ())
    if current_category and current_category not in categories:
        return (*categories, current_category)
    return categories


def is_expense_category_valid(expense_type, category):
    return category in EXPENSE_CATEGORY_CATALOG.get(expense_type, ())


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True, index=True)
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
    organization = relationship("Organization")
    branch = relationship("Branch")

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_expense_amount_positive"),
        CheckConstraint("expense_type IN ('operational', 'investment')", name="ck_expense_type"),
        CheckConstraint("payment_method IN ('cash', 'debit', 'credit', 'transfer', 'other')", name="ck_expense_payment_method"),
        CheckConstraint("status IN ('active', 'archived')", name="ck_expense_status"),
    )

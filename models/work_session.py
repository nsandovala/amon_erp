from sqlalchemy import CheckConstraint, Column, Date, DateTime, Index, Integer, String, Text, text
from sqlalchemy.orm import relationship

from models import Base, now_santiago


SESSION_STATUSES = ("open", "closed", "archived")


class WorkSession(Base):
    __tablename__ = "work_sessions"

    id = Column(Integer, primary_key=True)
    business_date = Column(Date, nullable=False, index=True)
    opened_at = Column(DateTime, nullable=False, default=now_santiago, index=True)
    closed_at = Column(DateTime, nullable=True)
    opening_cash = Column(Integer, nullable=False, default=0)
    closing_cash = Column(Integer, nullable=True)
    closing_cash_counted = Column(Integer, nullable=True)
    closing_notes = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="open", index=True)
    created_at = Column(DateTime, nullable=False, default=now_santiago)
    updated_at = Column(DateTime, nullable=False, default=now_santiago, onupdate=now_santiago)
    deleted_at = Column(DateTime, nullable=True, index=True)

    sales = relationship("Sale", back_populates="work_session")
    expenses = relationship("Expense", back_populates="work_session")

    __table_args__ = (
        CheckConstraint("opening_cash >= 0", name="ck_work_session_opening_cash_non_negative"),
        CheckConstraint("closing_cash IS NULL OR closing_cash >= 0", name="ck_work_session_closing_cash_non_negative"),
        CheckConstraint(
            "closing_cash_counted IS NULL OR closing_cash_counted >= 0",
            name="ck_work_session_closing_cash_counted_non_negative",
        ),
        CheckConstraint("status IN ('open', 'closed', 'archived')", name="ck_work_session_status"),
        Index(
            "uq_work_sessions_single_open",
            "status",
            unique=True,
            sqlite_where=text("status = 'open'"),
            postgresql_where=text("status = 'open'"),
        ),
    )

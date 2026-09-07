from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.database.database import Base


class Payment(Base):
    __tablename__ = "payments"

    # ==========================================
    # Primary Key
    # ==========================================

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    # ==========================================
    # Order Relationship
    # ==========================================

    order_id: Mapped[int] = mapped_column(
        ForeignKey(
            "orders.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ==========================================
    # User Relationship
    # ==========================================

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ==========================================
    # Payment Provider
    # ==========================================

    provider: Mapped[str] = mapped_column(
        String(50),
        default="paystack",
        nullable=False,
        index=True,
    )

    # ==========================================
    # Payment Reference
    # ==========================================

    reference: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    # ==========================================
    # Amount
    # ==========================================

    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(10),
        default="NGN",
        nullable=False,
    )

    # ==========================================
    # Payment Status
    # ==========================================

    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
        index=True,
    )

    # ==========================================
    # Payment Channel
    # ==========================================

    channel: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # ==========================================
    # Provider Transaction ID
    # ==========================================

    provider_transaction_id: Mapped[str | None] = (
        mapped_column(
            String(255),
            nullable=True,
            index=True,
        )
    )

    # ==========================================
    # Timestamps
    # ==========================================

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ==========================================
    # Relationships
    # ==========================================

    order = relationship(
        "Order",
        back_populates="payments",
    )

    user = relationship(
        "User",
        back_populates="payments",
    )
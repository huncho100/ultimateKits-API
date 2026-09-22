from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


class User(Base):
    __tablename__ = "users"

    # ==========================================
    # Primary Key
    # ==========================================

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    # ==========================================
    # Personal Information
    # ==========================================

    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # ==========================================
    # Authentication
    # ==========================================

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # When the password was last changed. Tokens issued
    # before this moment are rejected, which makes a reset
    # single-use and ends any session an attacker already
    # holds. NULL means the password has never been reset.
    password_changed_at: Mapped[datetime | None] = (
        mapped_column(
            DateTime(timezone=True),
            nullable=True,
        )
    )

    # ==========================================
    # User Status / Role
    # ==========================================

    role: Mapped[str] = mapped_column(
        String(50),
        default="customer",
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
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

    cart = relationship(
        "Cart",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    orders = relationship(
        "Order",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    payments = relationship(
        "Payment",
        back_populates="user",
        cascade="all, delete-orphan",
    )
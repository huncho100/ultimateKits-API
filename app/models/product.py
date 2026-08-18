from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.database import Base


class Product(Base):
    __tablename__ = "products"

    # ==========================================
    # Primary Key
    # ==========================================

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    # ==========================================
    # Product Information
    # ==========================================

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    sport: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    team: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
        index=True,
    )

    league: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
        index=True,
    )

    brand: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # ==========================================
    # Pricing
    # ==========================================

    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    old_price: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    # ==========================================
    # Product Rating
    # ==========================================

    rating: Mapped[float] = mapped_column(
        Numeric(3, 2),
        default=0,
        nullable=False,
    )

    # ==========================================
    # Product Image
    # ==========================================

    image: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # ==========================================
    # Product Status
    # ==========================================

    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    is_new: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    is_best_seller: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    in_stock: Mapped[bool] = mapped_column(
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
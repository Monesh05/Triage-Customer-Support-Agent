# app/models/product.py
# Purpose: SQLAlchemy ORM model for CloudDesk products/features (spec section 5 domain list).
#          Not exposed via a dedicated Phase 1 endpoint, but referenced by plans' `features`.
# Author: CloudDesk Team
# Date: 2026-09-21

from sqlalchemy import String, Text

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from sqlalchemy.orm import Mapped, mapped_column


class Product(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A CloudDesk product/feature that can be included in a plan."""

    __tablename__ = "products"

    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

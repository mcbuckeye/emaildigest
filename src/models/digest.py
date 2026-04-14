"""Digest models."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.user import User


class DigestStatus(str, Enum):
    """Digest status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PAUSED = "paused"


class DeliveryStatus(str, Enum):
    """Delivery status."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class Digest(Base):
    """Digest definition model."""

    __tablename__ = "digests"

    # Fields
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, nullable=True)
    frequency_cron: Mapped[str] = mapped_column(String(50), default="0 9 * * *")
    status: Mapped[DigestStatus] = mapped_column(String(20), default=DigestStatus.ACTIVE)
    recipient_email: Mapped[str] = mapped_column(String(255))

    # Relationships
    owner: Mapped["User"] = relationship(back_populates="digests")
    sources: Mapped[list["DigestSource"]] = relationship(
        back_populates="digest",
        cascade="all, delete-orphan",
    )
    deliveries: Mapped[list["DigestDelivery"]] = relationship(
        back_populates="digest",
        cascade="all, delete-orphan",
    )


class DigestSource(Base):
    """Source for a digest (RSS feed or URL)."""

    __tablename__ = "digest_sources"

    digest_id: Mapped[int] = mapped_column(ForeignKey("digests.id", ondelete="CASCADE"))
    source_type: Mapped[str] = mapped_column(String(20))  # "rss" or "url"
    url: Mapped[str] = mapped_column(String(500))
    last_checked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_scraped_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    digest: Mapped["Digest"] = relationship(back_populates="sources")
    items: Mapped[list["DigestItem"]] = relationship(
        back_populates="source",
        cascade="all, delete-orphan",
    )


class DigestDelivery(Base):
    """Digest delivery record."""

    __tablename__ = "digest_deliveries"

    digest_id: Mapped[int] = mapped_column(ForeignKey("digests.id", ondelete="CASCADE"))
    scheduled_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(nullable=True)
    status: Mapped[DeliveryStatus] = mapped_column(String(20), default=DeliveryStatus.PENDING)
    error_message: Mapped[str | None] = mapped_column(nullable=True)
    delivery_count: Mapped[int] = mapped_column(default=0)

    # Relationships
    digest: Mapped["Digest"] = relationship(back_populates="deliveries")
    items: Mapped[list["DigestItem"]] = relationship(
        back_populates="delivery",
        cascade="all, delete-orphan",
    )


class DigestItem(Base):
    """Individual item in a digest delivery."""

    __tablename__ = "digest_items"

    delivery_id: Mapped[int] = mapped_column(ForeignKey("digest_deliveries.id", ondelete="CASCADE"))
    source_url: Mapped[str] = mapped_column(String(500))
    title: Mapped[str] = mapped_column(String(500))
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(500))
    published_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    delivery: Mapped["DigestDelivery"] = relationship(back_populates="items")
    source: Mapped["DigestSource"] = relationship(
        back_populates="items",
        cascade="all, delete-orphan",
    )


# Add back_populates to User model
from src.models.user import User

User.digests: Mapped[list["Digest"]] = relationship(
    back_populates="owner",
)


__all__ = ["Digest", "DigestSource", "DigestDelivery", "DigestItem", "DigestStatus", "DeliveryStatus"]

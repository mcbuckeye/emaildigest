"""Digest models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.user import User


class DigestStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PAUSED = "paused"


class DeliveryStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SENT = "sent"
    FAILED = "failed"


class SourceType(str, Enum):
    RSS = "rss"
    URL = "url"


class SourceHealth(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    BROKEN = "broken"


class Digest(Base):
    __tablename__ = "digests"

    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    frequency_cron: Mapped[str] = mapped_column(String(50), default="0 9 * * *")
    status: Mapped[str] = mapped_column(String(20), default=DigestStatus.ACTIVE.value)
    recipient_email: Mapped[str] = mapped_column(String(255))
    next_run_at: Mapped[datetime | None] = mapped_column(nullable=True, index=True)
    last_run_at: Mapped[datetime | None] = mapped_column(nullable=True)

    owner: Mapped[User] = relationship(back_populates="digests")
    sources: Mapped[list[DigestSource]] = relationship(
        back_populates="digest",
        cascade="all, delete-orphan",
    )
    deliveries: Mapped[list[DigestDelivery]] = relationship(
        back_populates="digest",
        cascade="all, delete-orphan",
        order_by="DigestDelivery.scheduled_at.desc()",
    )
    recipients: Mapped[list[DigestRecipient]] = relationship(
        back_populates="digest",
        cascade="all, delete-orphan",
    )


class DigestSource(Base):
    __tablename__ = "digest_sources"

    digest_id: Mapped[int] = mapped_column(ForeignKey("digests.id", ondelete="CASCADE"), index=True)
    source_type: Mapped[str] = mapped_column(String(20))
    url: Mapped[str] = mapped_column(String(1000))
    last_checked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_scraped_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(default=0)
    health: Mapped[str] = mapped_column(String(20), default=SourceHealth.HEALTHY.value)

    digest: Mapped[Digest] = relationship(back_populates="sources")
    items: Mapped[list[DigestItem]] = relationship(
        back_populates="source",
        cascade="all, delete-orphan",
    )


class DigestRecipient(Base):
    __tablename__ = "digest_recipients"

    digest_id: Mapped[int] = mapped_column(ForeignKey("digests.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(String(255))
    unsubscribe_token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    unsubscribed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    digest: Mapped[Digest] = relationship(back_populates="recipients")

    __table_args__ = (UniqueConstraint("digest_id", "email", name="uq_digest_recipient"),)


class DigestDelivery(Base):
    __tablename__ = "digest_deliveries"

    digest_id: Mapped[int] = mapped_column(ForeignKey("digests.id", ondelete="CASCADE"), index=True)
    scheduled_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=DeliveryStatus.PENDING.value)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    html_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    delivery_count: Mapped[int] = mapped_column(default=0)
    attempts: Mapped[int] = mapped_column(default=0)
    open_count: Mapped[int] = mapped_column(default=0)
    click_count: Mapped[int] = mapped_column(default=0)
    tracking_token: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)

    digest: Mapped[Digest] = relationship(back_populates="deliveries")
    items: Mapped[list[DigestItem]] = relationship(
        back_populates="delivery",
        cascade="all, delete-orphan",
    )


class DigestItem(Base):
    __tablename__ = "digest_items"

    delivery_id: Mapped[int] = mapped_column(ForeignKey("digest_deliveries.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("digest_sources.id", ondelete="SET NULL"), nullable=True, index=True
    )
    digest_id: Mapped[int | None] = mapped_column(
        ForeignKey("digests.id", ondelete="CASCADE"), nullable=True, index=True
    )
    source_url: Mapped[str] = mapped_column(String(1000))
    title: Mapped[str] = mapped_column(String(500))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(1000))
    fingerprint: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    click_count: Mapped[int] = mapped_column(default=0)
    published_at: Mapped[datetime | None] = mapped_column(nullable=True)

    delivery: Mapped[DigestDelivery] = relationship(back_populates="items")
    source: Mapped[DigestSource | None] = relationship(back_populates="items")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column()
    used_at: Mapped[datetime | None] = mapped_column(nullable=True)

    user: Mapped[User] = relationship(back_populates="password_reset_tokens")


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column()
    used_at: Mapped[datetime | None] = mapped_column(nullable=True)

    user: Mapped[User] = relationship(back_populates="email_verification_tokens")


__all__ = [
    "Digest",
    "DigestSource",
    "DigestRecipient",
    "DigestDelivery",
    "DigestItem",
    "DigestStatus",
    "DeliveryStatus",
    "SourceType",
    "SourceHealth",
    "PasswordResetToken",
    "EmailVerificationToken",
]

"""User model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from passlib.context import CryptContext
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.digest import Digest, PasswordResetToken


_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(Base):
    """User account model."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))

    digests: Mapped[list[Digest]] = relationship(
        "Digest",
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    password_reset_tokens: Mapped[list[PasswordResetToken]] = relationship(
        "PasswordResetToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def set_password(self, password: str) -> None:
        self.password_hash = _pwd_context.hash(password)

    def verify_password(self, password: str) -> bool:
        return _pwd_context.verify(password, self.password_hash)

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    openid: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    nickname: Mapped[str] = mapped_column(String(80), default="微信用户")
    avatar_url: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    risk_cases: Mapped[list["RiskCase"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class RiskCase(Base):
    __tablename__ = "risk_cases"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    source_text: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(String(255))
    risk_level: Mapped[str] = mapped_column(String(16), index=True)
    risk_label: Mapped[str] = mapped_column(String(16))
    summary: Mapped[str] = mapped_column(Text)
    field_items: Mapped[list[dict[str, str]]] = mapped_column("fields", JSON)
    reasons: Mapped[list[str]] = mapped_column(JSON)
    missing_evidence: Mapped[list[str]] = mapped_column(JSON)
    before_dispatch: Mapped[list[str]] = mapped_column(JSON)
    confirmation_message: Mapped[str] = mapped_column(Text)
    internal_note: Mapped[str] = mapped_column(Text)
    refusal_action: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped[User] = relationship(back_populates="risk_cases")

"""Database models for the CryptoKnight application."""
from __future__ import annotations

from datetime import datetime

from flask_login import UserMixin
from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .extensions import db, bcrypt


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    preferences: Mapped["UserPreference"] = relationship(
        "UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    predictions: Mapped[list["Prediction"]] = relationship(
        "Prediction", back_populates="user", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["PriceAlert"]] = relationship(
        "PriceAlert", back_populates="user", cascade="all, delete-orphan"
    )

    def set_password(self, password: str) -> None:
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password: str) -> bool:
        return bcrypt.check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User {self.username}>"


class UserPreference(TimestampMixin, db.Model):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    preferred_pairs: Mapped[str] = mapped_column(String(255), default="BTC/USDT,ETH/USDT")
    theme: Mapped[str] = mapped_column(String(20), default="dark")
    notifications_enabled: Mapped[bool] = mapped_column(Integer, default=1)

    user: Mapped[User] = relationship("User", back_populates="preferences")

    def as_dict(self) -> dict[str, str | bool]:
        return {
            "preferred_pairs": self.preferred_pairs,
            "theme": self.theme,
            "notifications_enabled": bool(self.notifications_enabled),
        }


class Prediction(TimestampMixin, db.Model):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), default="15m")
    prediction: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship("User", back_populates="predictions")

    def as_dict(self) -> dict[str, str | float | dict]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "prediction": self.prediction,
            "confidence": self.confidence,
            "metrics": self.metrics,
            "created_at": self.created_at.isoformat(),
        }


class PriceAlert(TimestampMixin, db.Model):
    __tablename__ = "price_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    triggered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped[User] = relationship("User", back_populates="alerts")

    def mark_triggered(self) -> None:
        self.is_active = False
        self.triggered_at = datetime.utcnow()

    def __repr__(self) -> str:
        return f"<PriceAlert {self.symbol} {self.direction} {self.threshold}>"

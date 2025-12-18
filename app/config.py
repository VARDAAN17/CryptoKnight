"""Configuration settings for the CryptoKnight application."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Type

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


@dataclass
class Config:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-key")
    SQLALCHEMY_DATABASE_URI: str = os.getenv(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'cryptoknight.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    COINGECKO_API_URL: str = "https://api.coingecko.com/api/v3"
    MARKET_COINS: str = "bitcoin,ethereum,solana,binancecoin,cardano"
    PREFERRED_CURRENCY: str = "usd"
    CACHE_TIMEOUT: int = 300
    PREDICTION_RETENTION: int = 50
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    MAIL_FROM_EMAIL: str | None = os.getenv("MAIL_FROM_EMAIL")
    SENDGRID_API_KEY: str | None = os.getenv("SENDGRID_API_KEY")
    ALERT_MONITOR_ENABLED: bool = os.getenv("ALERT_MONITOR_ENABLED", "true").lower() == "true"
    ALERT_MONITOR_INTERVAL: int = int(os.getenv("ALERT_MONITOR_INTERVAL", "60"))


class DevelopmentConfig(Config):
    DEBUG: bool = True


class TestingConfig(Config):
    TESTING: bool = True
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///:memory:"
    WTF_CSRF_ENABLED: bool = False
    ALERT_MONITOR_ENABLED: bool = False


class ProductionConfig(Config):
    DEBUG: bool = False


config_by_name: Dict[str, Type[Config]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}

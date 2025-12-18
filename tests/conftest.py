from __future__ import annotations

from typing import Any, Generator

import pytest
from flask import Flask

from app import create_app
from app.extensions import db
from app.models import User, UserPreference


@pytest.fixture()
def app(monkeypatch: pytest.MonkeyPatch) -> Generator[Flask, None, None]:
    monkeypatch.setenv("FLASK_ENV", "testing")
    application = create_app("testing")

    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app: Flask):
    return app.test_client()


@pytest.fixture()
def authenticated_client(app: Flask, client):
    with app.app_context():
        user = User(username="tester", email="tester@example.com")
        user.set_password("password123")
        preference = UserPreference(user=user)
        db.session.add_all([user, preference])
        db.session.commit()

    login_data = {"username": "tester", "password": "password123"}
    client.post("/login", data=login_data, follow_redirects=True)
    return client


@pytest.fixture()
def sample_market_payload() -> list[dict[str, Any]]:
    base_prices = [50000 + i * 10 for i in range(200)]
    return [
        {
            "id": "bitcoin",
            "symbol": "btc",
            "name": "Bitcoin",
            "current_price": 52000,
            "price_change_percentage_24h": 2.5,
            "market_cap": 1_000_000_000_000,
            "total_volume": 35_000_000_000,
            "sparkline_in_7d": {"price": base_prices},
        },
        {
            "id": "ethereum",
            "symbol": "eth",
            "name": "Ethereum",
            "current_price": 3500,
            "price_change_percentage_24h": -1.2,
            "market_cap": 450_000_000_000,
            "total_volume": 18_000_000_000,
            "sparkline_in_7d": {"price": [3500 + i * 2 for i in range(200)]},
        },
    ]


@pytest.fixture(autouse=True)
def mock_coin_service(monkeypatch: pytest.MonkeyPatch, sample_market_payload):
    lookup = {entry["symbol"].upper(): entry["current_price"] for entry in sample_market_payload}

    def fake_fetch_market_data(*args, **kwargs):
        return sample_market_payload

    monkeypatch.setattr("app.services.coin_service.fetch_market_data", fake_fetch_market_data)
    monkeypatch.setattr(
        "app.services.coin_service.build_price_lookup",
        lambda force_refresh=False: lookup.copy(),
    )
    monkeypatch.setattr(
        "app.services.coin_service.get_price_for_symbol",
        lambda symbol, force_refresh=False: lookup.get(symbol.upper()),
    )
    monkeypatch.setattr(
        "app.services.coin_service.fetch_global_metrics",
        lambda: {
            "total_market_cap": {"usd": 1_500_000_000_000},
            "total_volume": {"usd": 88_000_000_000},
            "market_cap_percentage": {"btc": 48.2, "eth": 19.4},
            "market_cap_change_percentage_24h_usd": 1.8,
        },
    )

from __future__ import annotations

from app.extensions import db
from app.models import Prediction


def test_market_data_endpoint(authenticated_client):
    response = authenticated_client.get("/api/market-data")
    assert response.status_code == 200
    payload = response.get_json()
    assert "tickers" in payload and len(payload["tickers"]) == 2
    assert payload["tickers"][0]["symbol"] == "BTC"


def test_prediction_endpoint(authenticated_client, app):
    response = authenticated_client.post("/api/predict", json={"symbol": "BTC"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["symbol"] == "BTC"
    assert data["prediction"] in {"Bullish", "Bearish", "Neutral"}
    assert data["timeframe"] == "15m"

    with app.app_context():
        record = db.session.query(Prediction).first()
        assert record is not None
        assert record.timeframe == "15m"


def test_prediction_endpoint_custom_timeframe(authenticated_client, app):
    response = authenticated_client.post(
        "/api/predict", json={"symbol": "BTC", "timeframe": "4h"}
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["timeframe"] == "4h"

    with app.app_context():
        record = db.session.query(Prediction).order_by(Prediction.id.desc()).first()
        assert record is not None
        assert record.timeframe == "4h"


def test_analytics_endpoint(authenticated_client):
    response = authenticated_client.get("/api/analytics")
    assert response.status_code == 200
    data = response.get_json()
    assert data["market_cap"] == 1_500_000_000_000
    assert data["btc_dominance"] == 48.2

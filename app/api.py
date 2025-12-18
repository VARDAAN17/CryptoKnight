"""API blueprint to expose market data and AI predictions."""
from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from .extensions import db
from .models import Prediction
from .models import PriceAlert
from .services import coin_service
from .services.prediction_service import generate_prediction, get_predictor

api_bp = Blueprint("api", __name__)


@api_bp.get("/market-data")
@login_required
def market_data():
    data = coin_service.fetch_market_data()
    fetched_at = datetime.now(timezone.utc)
    payload = coin_service.normalize_market_payload(data, fetched_at=fetched_at)
    return jsonify(payload)


@api_bp.get("/analytics")
@login_required
def analytics():
    global_metrics = coin_service.fetch_global_metrics()
    dominance = global_metrics.get("market_cap_percentage", {})
    return jsonify(
        {
            "market_cap": global_metrics.get("total_market_cap", {}).get("usd"),
            "volume_24h": global_metrics.get("total_volume", {}).get("usd"),
            "btc_dominance": dominance.get("btc"),
            "eth_dominance": dominance.get("eth"),
            "market_cap_change_percentage_24h_usd": global_metrics.get(
                "market_cap_change_percentage_24h_usd"
            ),
        }
    )


@api_bp.post("/predict")
@login_required
def predict():
    payload = request.get_json(silent=True) or {}
    symbol = payload.get("symbol", "BTC")
    timeframe = payload.get("timeframe")
    try:
        result = generate_prediction(symbol, timeframe)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    prediction = Prediction(
        user=current_user,
        symbol=result.symbol,
        prediction=result.prediction,
        confidence=result.confidence,
        metrics=result.metrics,
        timeframe=result.timeframe,
        notes=payload.get("notes"),
    )
    db.session.add(prediction)
    db.session.commit()
    return jsonify(
        {
            "symbol": result.symbol,
            "prediction": result.prediction,
            "confidence": result.confidence,
            "metrics": result.metrics,
            "timeframe": result.timeframe,
        }
    )


@api_bp.get("/predictions/history")
@login_required
def prediction_history():
    records = (
        Prediction.query.filter_by(user_id=current_user.id)
        .order_by(Prediction.created_at.desc())
        .limit(5)
        .all()
    )
    return jsonify([record.as_dict() for record in records])


@api_bp.post("/predict/retrain")
@login_required
def retrain():
    predictor = get_predictor()
    metrics = predictor.retrain()
    return jsonify(
        {
            "status": "ok",
            "metrics": metrics,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )


@api_bp.post('/get-alerts/')
@login_required
def get_alerts():
    alerts = (
        PriceAlert.query.filter_by(user_id=current_user.id)
        .order_by(PriceAlert.created_at.desc())
        .all()
    )
    all_data = []
    for alert in alerts:
        all_data.append({
            "symbol": alert.symbol,
            "direction": alert.direction,
            "threshold": alert.threshold,
            "is_active": alert.is_active,
        })
    return jsonify({"status": "ok", "alerts": all_data})


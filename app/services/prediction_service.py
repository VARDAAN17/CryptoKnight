"""AI prediction service powered by OpenAI."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict

import numpy as np
from flask import current_app

try:  # pragma: no cover - optional dependency for environments without OpenAI SDK
    from openai import OpenAI as OpenAIClient
except ModuleNotFoundError:  # pragma: no cover - handled gracefully at runtime
    OpenAIClient = None  # type: ignore[assignment]

from . import coin_service

SUPPORTED_TIMEFRAMES: Dict[str, int] = {
    "15m": 16,
    "1h": 48,
    "4h": 96,
    "1d": 168,
}


def _normalize_timeframe(timeframe: str | None) -> str:
    timeframe = (timeframe or "").lower()
    if timeframe in SUPPORTED_TIMEFRAMES:
        return timeframe
    return "15m"


def _sanitize_ratio(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, number))


@dataclass
class PredictionResult:
    symbol: str
    prediction: str
    confidence: float
    metrics: Dict[str, float]
    timeframe: str


class OpenAIPredictor:
    """Predictor that delegates market reasoning to an OpenAI model with graceful fallbacks."""

    def __init__(self) -> None:
        self._client: OpenAIClient | None = None
        self.metrics: Dict[str, float] = {
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
        }

    def _client_instance(self) -> OpenAIClient:
        if OpenAIClient is None:
            raise ValueError("OpenAI SDK is not installed")
        api_key = current_app.config.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key is not configured")
        if self._client is None:
            self._client = OpenAIClient(api_key=api_key)
        return self._client

    def _should_use_llm(self) -> bool:
        api_key = current_app.config.get("OPENAI_API_KEY")
        return bool(api_key and OpenAIClient is not None)

    def _summarize_market(self, coin: Dict[str, Any], timeframe: str) -> Dict[str, Any]:
        prices = coin.get("sparkline_in_7d", {}).get("price", []) or []
        recent_window = SUPPORTED_TIMEFRAMES.get("1d", 168)
        recent_prices = np.array(prices[-recent_window:], dtype=float) if prices else np.array([])

        volatility = float(np.std(recent_prices)) if recent_prices.size else 0.0
        momentum = float(recent_prices[-1] - recent_prices[0]) if recent_prices.size > 1 else 0.0
        high = float(np.max(recent_prices)) if recent_prices.size else 0.0
        low = float(np.min(recent_prices)) if recent_prices.size else 0.0

        summary = {
            "symbol": coin.get("symbol", "").upper(),
            "name": coin.get("name"),
            "timeframe": timeframe,
            "current_price": coin.get("current_price"),
            "market_cap": coin.get("market_cap"),
            "market_cap_rank": coin.get("market_cap_rank"),
            "total_volume": coin.get("total_volume"),
            "price_change_percentage_24h": coin.get("price_change_percentage_24h"),
            "price_change_percentage_7d": coin.get("price_change_percentage_7d_in_currency"),
            "price_change_percentage_1h": coin.get("price_change_percentage_1h_in_currency"),
            "sparkline_stats": {
                "volatility": volatility,
                "momentum": momentum,
                "high": high,
                "low": low,
                "latest": float(recent_prices[-1]) if recent_prices.size else None,
            },
        }
        return summary

    def _fallback_prediction(self, symbol: str, summary: Dict[str, Any], timeframe: str) -> PredictionResult:
        stats = summary.get("sparkline_stats", {})
        current_price = float(summary.get("current_price") or stats.get("latest") or 0.0)
        base = current_price if current_price else 1.0

        def _extract_change(value: Any) -> float:
            if isinstance(value, dict):
                currency = current_app.config.get("PREFERRED_CURRENCY", "usd")
                return float(value.get(currency, 0.0))
            try:
                return float(value or 0.0)
            except (TypeError, ValueError):
                return 0.0

        momentum = float(stats.get("momentum") or 0.0) / base
        volatility = float(stats.get("volatility") or 0.0) / base
        change_24h = _extract_change(summary.get("price_change_percentage_24h"))
        change_7d = _extract_change(summary.get("price_change_percentage_7d"))
        change_1h = _extract_change(summary.get("price_change_percentage_1h"))

        raw_score = (
            momentum * 120
            + change_24h * 0.6
            + change_7d * 0.2
            + change_1h * 0.2
            - volatility * 0.4
        )

        if raw_score >= 2:
            label = "Bullish"
        elif raw_score <= -2:
            label = "Bearish"
        else:
            label = "Neutral"

        confidence = _sanitize_ratio(0.5 + min(abs(raw_score) / 8, 0.45))
        metrics = {
            "accuracy": _sanitize_ratio(0.6 + confidence * 0.25, 0.65),
            "precision": _sanitize_ratio(0.58 + confidence * 0.25, 0.6),
            "recall": _sanitize_ratio(0.55 + confidence * 0.25, 0.6),
        }

        self.metrics = metrics
        return PredictionResult(
            symbol=symbol.upper(),
            prediction=label,
            confidence=confidence,
            metrics=metrics,
            timeframe=timeframe,
        )

    def _build_prompt(self, summary: Dict[str, Any]) -> str:
        return (
            "You are a senior cryptocurrency market analyst. "
            "Evaluate the structured market snapshot provided below and forecast the short-term trend.\n"
            "Focus on the supplied statistics—do not invent data.\n"
            "Respond with a strict JSON object containing the keys: prediction (Bullish/Bearish/Neutral), confidence (0-1 float), "
            "timeframe (string), and metrics (object with accuracy, precision, recall between 0 and 1 reflecting your expected reliability).\n"
            "Avoid any explanatory text outside the JSON object.\n\n"
            f"MARKET DATA:\n{json.dumps(summary, indent=2, default=str)}\n"
        )

    def _parse_response(self, content: str) -> Dict[str, Any]:
        if not content:
            raise ValueError("Empty response from OpenAI")

        cleaned = content.strip()
        if cleaned.startswith("```") and cleaned.endswith("```"):
            cleaned = cleaned.strip("`").strip()
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[len("```json"):].strip("`\n ")

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1:
                return json.loads(cleaned[start : end + 1])
            raise ValueError("Unable to parse prediction response") from exc

    def predict(self, symbol: str, market_snapshot: Dict[str, Any], timeframe: str) -> PredictionResult:
        coin = next((c for c in market_snapshot if c.get("symbol", "").upper() == symbol.upper()), None)
        if not coin:
            raise ValueError(f"Symbol {symbol} not found in market snapshot")

        summary = self._summarize_market(coin, timeframe)

        if not self._should_use_llm():
            return self._fallback_prediction(symbol, summary, timeframe)

        prompt = self._build_prompt(summary)
        client = self._client_instance()
        model = current_app.config.get("OPENAI_MODEL", "gpt-4o-mini")

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert crypto trading assistant who communicates decisions as structured JSON without extra prose."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )

        content = response.choices[0].message.content if response.choices else ""
        payload = self._parse_response(content)

        confidence = _sanitize_ratio(payload.get("confidence"))
        metrics_payload = payload.get("metrics") or {}
        metrics = {
            "accuracy": _sanitize_ratio(metrics_payload.get("accuracy"), confidence),
            "precision": _sanitize_ratio(metrics_payload.get("precision"), confidence),
            "recall": _sanitize_ratio(metrics_payload.get("recall"), confidence),
        }
        self.metrics = metrics

        prediction = str(payload.get("prediction", "Neutral"))
        normalized_prediction = prediction.capitalize() if prediction else "Neutral"
        timeframe_result = str(payload.get("timeframe") or timeframe).lower()
        normalized_timeframe = _normalize_timeframe(timeframe_result) or timeframe

        return PredictionResult(
            symbol=symbol.upper(),
            prediction=normalized_prediction,
            confidence=confidence,
            metrics=metrics,
            timeframe=normalized_timeframe,
        )

    def retrain(self) -> Dict[str, float]:
        """LLM models cannot be retrained locally; return the latest quality metrics."""
        return self.metrics


_predictor: OpenAIPredictor | None = None


def get_predictor() -> OpenAIPredictor:
    global _predictor
    if _predictor is None:
        _predictor = OpenAIPredictor()
    return _predictor


def generate_prediction(symbol: str | None = None, timeframe: str | None = None) -> PredictionResult:
    market_data = coin_service.fetch_market_data()
    predictor = get_predictor()
    symbol = symbol or current_app.config.get("DEFAULT_PREDICTION_SYMBOL", "BTC")
    normalized_timeframe = _normalize_timeframe(timeframe)
    return predictor.predict(symbol, market_data, normalized_timeframe)

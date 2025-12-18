from __future__ import annotations

from app.extensions import db
from app.models import PriceAlert, User
from app.tasks.alerts import evaluate_price_alerts


def test_create_price_alert(authenticated_client, app):
    response = authenticated_client.post(
        "/alerts",
        data={
            "symbol": "BTC",
            "direction": "above",
            "threshold": "51000",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        alert = db.session.query(PriceAlert).first()
        assert alert is not None
        assert alert.symbol == "BTC"
        assert alert.direction == "above"
        assert alert.threshold == 51000.0
        assert alert.is_active is True


def test_evaluate_price_alerts_triggers(monkeypatch, app, authenticated_client):
    email_calls: list[tuple[str, str, float]] = []

    def fake_send_email(user, alert, price):
        email_calls.append((user.email, alert.symbol, price))
        return True

    monkeypatch.setattr("app.tasks.alerts.send_price_alert_email", fake_send_email)

    with app.app_context():
        user = db.session.query(User).filter_by(username="tester").first()
        alert = PriceAlert(user=user, symbol="BTC", direction="above", threshold=50000)
        db.session.add(alert)
        db.session.commit()

        triggered = evaluate_price_alerts(force_refresh=False)
        assert triggered
        refreshed = db.session.get(PriceAlert, alert.id)
        assert refreshed is not None
        assert refreshed.is_active is False
        assert refreshed.triggered_at is not None

    assert email_calls
    assert email_calls[0][1] == "BTC"

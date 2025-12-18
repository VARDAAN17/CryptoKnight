"""Background worker for monitoring price alerts."""
from __future__ import annotations

import threading
import time
from typing import List

from ..extensions import db
from ..models import PriceAlert
from ..services import coin_service
from ..services.notification_service import send_price_alert_email

_MONITOR_STARTED = False
_MONITOR_LOCK = threading.Lock()


def evaluate_price_alerts(*, force_refresh: bool = True) -> List[PriceAlert]:
    """Evaluate all active alerts and send notifications when triggered."""
    try:
        active_alerts = PriceAlert.query.filter_by(is_active=True).all()
    except:
        return []
    if not active_alerts:
        return []

    price_lookup = coin_service.build_price_lookup(force_refresh=force_refresh)
    triggered: list[PriceAlert] = []

    for alert in active_alerts:
        price = price_lookup.get(alert.symbol.upper())
        if price is None:
            continue

        should_trigger = (
            price >= alert.threshold if alert.direction == "above" else price <= alert.threshold
        )
        if not should_trigger:
            continue

        alert.mark_triggered()
        triggered.append(alert)
        send_price_alert_email(alert.user, alert, price)

    if triggered:
        db.session.commit()

    return triggered


def start_alert_monitor(app) -> None:
    """Start the background thread that periodically checks price alerts."""
    global _MONITOR_STARTED

    if not app.config.get("ALERT_MONITOR_ENABLED", True):
        return

    with _MONITOR_LOCK:
        if _MONITOR_STARTED:
            return

        def _worker():
            with app.app_context():
                interval = int(app.config.get("ALERT_MONITOR_INTERVAL", 60))
                interval = max(30, interval)
                while True:
                    try:
                        evaluate_price_alerts(force_refresh=True)
                    except Exception as exc:  # pragma: no cover - defensive logging
                        app.logger.exception("Price alert monitor error: %s", exc)
                    time.sleep(interval)

        thread = threading.Thread(target=_worker, name="price-alert-monitor", daemon=True)
        thread.start()
        _MONITOR_STARTED = True

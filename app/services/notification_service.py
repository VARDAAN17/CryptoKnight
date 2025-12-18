"""Email notification helpers for CryptoKnight."""
from __future__ import annotations

import requests
from flask import current_app

SENDGRID_MAIL_ENDPOINT = "https://api.sendgrid.com/v3/mail/send"


def _build_email_content(user, alert, current_price: float) -> tuple[str, str]:
    """Return the plain text and HTML bodies for the alert email."""

    body_text = (
        "Hello {name},\n\n"
        "Your price alert for {symbol} has been triggered.\n"
        "Current price: ${price:.2f}.\n"
        "Configured threshold: ${threshold:.2f} ({direction}).\n\n"
        "You are receiving this notification because you created the alert in CryptoKnight.\n"
    ).format(
        name=user.username,
        symbol=alert.symbol,
        price=current_price,
        threshold=alert.threshold,
        direction="upward" if alert.direction == "above" else "downward",
    )

    body_html = (
        "<p>Hello {name},</p>"
        "<p>Your price alert for <strong>{symbol}</strong> has been triggered.</p>"
        "<p>Current price: <strong>${price:.2f}</strong><br/>"
        "Configured threshold: <strong>${threshold:.2f} ({direction} movement)</strong></p>"
        "<p>You are receiving this notification because you created the alert in CryptoKnight.</p>"
    ).format(
        name=user.username,
        symbol=alert.symbol,
        price=current_price,
        threshold=alert.threshold,
        direction="upward" if alert.direction == "above" else "downward",
    )

    return body_text, body_html


def send_price_alert_email(user, alert, current_price: float) -> bool:
    """Send a price alert email using the SendGrid REST API."""

    config = current_app.config
    api_key = config.get("SENDGRID_API_KEY")
    from_email = config.get("MAIL_FROM_EMAIL")

    if not api_key:
        current_app.logger.warning("SendGrid API key is not configured; skipping alert email.")
        return False

    if not from_email:
        current_app.logger.warning("Sender email is not configured; skipping alert email.")
        return False

    subject = f"CryptoKnight Alert · {alert.symbol}"
    body_text, body_html = _build_email_content(user, alert, current_price)

    payload = {
        "personalizations": [
            {
                "to": [{"email": user.email}],
                "subject": subject,
            }
        ],
        "from": {"email": from_email},
        "content": [
            {"type": "text/plain", "value": body_text},
            {"type": "text/html", "value": body_html},
        ],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(SENDGRID_MAIL_ENDPOINT, json=payload, headers=headers, timeout=10)
        if response.status_code in (200, 202):
            return True

        current_app.logger.error(
            "SendGrid returned status %s when sending alert email: %s",
            response.status_code,
            response.text,
        )
        return False
    except requests.RequestException as exc:  # pragma: no cover - logging path
        current_app.logger.exception("Failed to send alert email via SendGrid: %s", exc)
        return False

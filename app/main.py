"""Main blueprint powering the dashboard experience."""
from __future__ import annotations

from flask import Blueprint, current_app, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from .extensions import db
from .forms import PreferenceForm, PriceAlertForm
from .models import PriceAlert, UserPreference

main_bp = Blueprint("main", __name__, template_folder="templates")


def _build_alert_choices() -> list[tuple[str, str]]:
    config = current_app.config
    provided = config.get("ALERT_SYMBOL_CHOICES")
    if provided:
        return [(symbol.upper(), label) for symbol, label in provided]

    fallback_map = {
        "bitcoin": ("BTC", "Bitcoin (BTC)"),
        "ethereum": ("ETH", "Ethereum (ETH)"),
        "solana": ("SOL", "Solana (SOL)"),
        "binancecoin": ("BNB", "Binance Coin (BNB)"),
        "cardano": ("ADA", "Cardano (ADA)"),
    }
    selected: list[tuple[str, str]] = []
    raw_coins = config.get("MARKET_COINS", "")
    for coin_id in [coin.strip().lower() for coin in raw_coins.split(",") if coin.strip()]:
        if coin_id in fallback_map:
            selected.append(fallback_map[coin_id])

    return selected or list(fallback_map.values())


@main_bp.route("/")
@login_required
def dashboard():
    preference = current_user.preferences or UserPreference(user=current_user)
    form = PreferenceForm(obj=preference)
    alert_form = PriceAlertForm()
    alert_form.symbol.choices = _build_alert_choices()
    alerts = (
        PriceAlert.query.filter_by(user_id=current_user.id)
        .order_by(PriceAlert.created_at.desc())
        .all()[:6]
    )
    return render_template(
        "index.html",
        preference=preference,
        form=form,
        alert_form=alert_form,
        alerts=alerts,
    )


@main_bp.route("/preferences", methods=["POST"])
@login_required
def update_preferences():
    form = PreferenceForm()
    if form.validate_on_submit():
        preference = current_user.preferences or UserPreference(user=current_user)
        preference.preferred_pairs = form.preferred_pairs.data
        preference.theme = form.theme.data
        preference.notifications_enabled = 1 if form.notifications_enabled.data else 0
        db.session.add(preference)
        db.session.commit()
        flash("Preferences updated successfully!", "success")
    else:
        flash("Error updating preferences", "danger")
    return redirect(url_for("main.dashboard"))


@main_bp.route("/alerts", methods=["POST"])
@login_required
def create_alert():
    form = PriceAlertForm()
    form.symbol.choices = _build_alert_choices()
    if form.validate_on_submit():
        alert = PriceAlert(
            user=current_user,
            symbol=form.symbol.data.upper(),
            direction=form.direction.data,
            threshold=float(form.threshold.data),
        )
        db.session.add(alert)
        db.session.commit()
        flash("Price alert created successfully!", "success")
    else:
        flash("Unable to create alert. Please check the form inputs.", "danger")
    return redirect(url_for("main.dashboard"))

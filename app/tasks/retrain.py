"""CLI command for retraining the AI model."""
from __future__ import annotations

import click
from flask import current_app
from flask.cli import with_appcontext

from ..extensions import db
from ..models import Prediction
from ..services.prediction_service import get_predictor


@click.command("retrain-model")
@with_appcontext
def retrain_model_command() -> None:
    """Retrain the predictor using synthetic data and prune old predictions."""
    predictor = get_predictor()
    metrics = predictor.retrain()
    click.echo(f"Model retrained with metrics: {metrics}")

    retention = current_app.config.get("PREDICTION_RETENTION", 50)
    if retention:
        ids_to_keep = (
            db.session.query(Prediction.id)
            .order_by(Prediction.created_at.desc())
            .limit(retention)
            .subquery()
        )
        deleted = (
            Prediction.query.filter(~Prediction.id.in_(db.session.query(ids_to_keep.c.id))).delete(
                synchronize_session=False
            )
        )
        if deleted:
            db.session.commit()
            click.echo(f"Pruned {deleted} historical prediction records.")

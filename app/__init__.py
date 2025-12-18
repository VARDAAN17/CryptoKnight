"""Application factory for CryptoKnight dashboard."""
from __future__ import annotations

import os
from pathlib import Path

from flask import Flask
from flask_migrate import Migrate
from flask_login import LoginManager

from .config import config_by_name
from .extensions import db, bcrypt
from .models import User
from .tasks.alerts import start_alert_monitor

migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    return db.session.get(User, int(user_id))


def create_app(config_name: str | None = None) -> Flask:
    """Factory pattern for creating the Flask application."""

    config_name = config_name or os.getenv("FLASK_ENV", "production")
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(config_by_name[config_name])

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    register_extensions(app)
    register_blueprints(app)
    register_cli(app)
    start_alert_monitor(app)

    return app


def register_extensions(app: Flask) -> None:
    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)


def register_blueprints(app: Flask) -> None:
    from .auth import auth_bp
    from .main import main_bp
    from .api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")


def register_cli(app: Flask) -> None:
    from .tasks.retrain import retrain_model_command

    app.cli.add_command(retrain_model_command)

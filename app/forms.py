"""Forms used for user authentication and preferences."""
from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import BooleanField, DecimalField, PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import Email, EqualTo, Length, DataRequired, NumberRange


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember me")
    submit = SubmitField("Login")


class RegistrationForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField(
        "Password", validators=[DataRequired(), Length(min=6), EqualTo("confirm", message="Passwords must match")]
    )
    confirm = PasswordField("Confirm Password", validators=[DataRequired()])
    submit = SubmitField("Register")


class PreferenceForm(FlaskForm):
    preferred_pairs = StringField(
        "Preferred Pairs", validators=[DataRequired(), Length(min=3, max=255)]
    )
    theme = StringField("Theme", validators=[DataRequired()])
    notifications_enabled = BooleanField("Notifications")
    submit = SubmitField("Save Preferences")


class PriceAlertForm(FlaskForm):
    symbol = SelectField("Signal", validators=[DataRequired()], choices=[])
    direction = SelectField(
        "Direction",
        choices=[
            ("above", "Notify when price moves up to threshold"),
            ("below", "Notify when price drops to threshold"),
        ],
        validators=[DataRequired()],
    )
    threshold = DecimalField(
        "Price Threshold (USD)",
        validators=[DataRequired(), NumberRange(min=0)],
        places=2,
    )
    submit = SubmitField("Create Alert")

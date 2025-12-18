# CryptoKnight – Crypto Analytics Dashboard

CryptoKnight is a production-ready Flask application that delivers real-time cryptocurrency market intelligence, interactive analytics, and AI-powered predictions in a cohesive dashboard experience.

## ✨ Features

- **Secure authentication** using Flask-Login, hashed passwords, and user-specific preferences.
- **Live market ticker** and dynamic price charting powered by the CoinGecko API with intelligent caching.
- **AI prediction engine** leveraging scikit-learn logistic regression for short-term trend forecasts with retraining tools.
- **Analytics summary panel** summarizing market cap, volume, dominance ratios, and exportable prediction history (CSV/PDF).
- **Responsive dark UI** built with Bootstrap 5, Plotly.js, and custom styling for a neon-inspired visual identity.
- **Modular Flask architecture** with blueprints, services, and CLI command for model maintenance.
- **PostgreSQL-ready** persistence via SQLAlchemy models (defaults to SQLite for local development/testing).
- **Comprehensive test suite** using pytest with service mocking to ensure deterministic results.

## 🛠️ Tech Stack

- Python 3.11+
- Flask 3
- SQLAlchemy (PostgreSQL or SQLite)
- Flask-Migrate for migrations (optional)
- scikit-learn, numpy for AI predictions
- Bootstrap 5, Plotly.js, jQuery for the frontend

## 🚀 Getting Started

1. **Clone & install dependencies**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure environment**

   Create a `.env` file (optional) to override defaults:

   ```bash
   SECRET_KEY=change-me
   DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/cryptoknight
   MARKET_COINS=bitcoin,ethereum,solana,binancecoin,cardano
   MAIL_FROM_EMAIL=alerts@yourdomain.com
   SENDGRID_API_KEY=your-sendgrid-api-key
   ALERT_MONITOR_ENABLED=true
   ALERT_MONITOR_INTERVAL=60
   ```

   If no database URL is supplied the app stores data in `instance/cryptoknight.db`.

3. **Run database migrations (optional)**

   ```bash
   flask --app manage.py db init
   flask --app manage.py db migrate -m "Initial tables"
   flask --app manage.py db upgrade
   ```

4. **Launch the development server**

   ```bash
   flask --app manage.py --debug run
   ```

   Visit `http://localhost:5000` and register an account to explore the dashboard. After logging in the app automatically pulls market data, performs AI predictions, and allows you to export reports.

5. **Retrain the AI model**

   ```bash
   flask --app manage.py retrain-model
   ```

   This command refreshes the logistic regression model and prunes old predictions based on the `PREDICTION_RETENTION` setting.

### 📧 Email alert configuration

Price alerts are delivered via [SendGrid](https://sendgrid.com/) using the API key supplied in `SENDGRID_API_KEY`.

1. Verify a sender identity (domain or single email) in the SendGrid dashboard.
2. Generate an API key with "Mail Send" permissions and store it as `SENDGRID_API_KEY`.
3. Set `MAIL_FROM_EMAIL` to the verified sender address so recipients see a trusted source.

Keep the API key secret just like any other credential. The alert monitor uses these values to send notifications to each user's registered email whenever thresholds are crossed. Adjust `ALERT_MONITOR_INTERVAL` (in seconds) to control how frequently the background check runs.

## 🧪 Running Tests

```bash
pytest
```

The suite mocks external API calls for deterministic behavior and covers authentication, market endpoints, and prediction workflows.

## 📦 Deployment Notes

- Enable production settings by setting `FLASK_ENV=production`.
- Supply a PostgreSQL `DATABASE_URL` and run migrations to provision tables.
- Configure a WSGI server such as Gunicorn and reverse proxy via Nginx or your preferred platform.
- For Docker-based deployments, create a container image using the included dependencies and expose port 5000.

## 📄 License

This project is provided as-is under the MIT License. Customize and extend as needed for your trading or analytics workflows.

# Payment Service

**Internal payment processing platform**

Payment Service handles payment intents, refunds, and webhook verification for our products. Built as a lightweight Flask API backed by PostgreSQL and Stripe.

## Tech Stack

- **Runtime:** Python 3.11
- **Framework:** Flask
- **Database:** PostgreSQL 15
- **Payments:** Stripe API
- **Testing:** pytest
- **Migrations:** raw SQL (versioned in `migrations/`)

## Quick Start

```bash
# Clone and enter the project
git clone git@github.com:ourorg/payment-service.git
cd payment-service

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your Stripe keys and database URL

# Run migrations
python manage.py migrate

# Start the development server
flask run --debug
```

The API will be available at `http://localhost:5000`.

## Architecture

```
payment-service/
├── src/
│   ├── payments.py      # Core payment logic (charges, refunds, intents)
│   ├── webhooks.py      # Stripe webhook verification & dispatch
│   ├── models.py        # Database models and query helpers
│   ├── styles.css       # Dashboard UI styles
│   └── app.py           # Flask application entry point
├── migrations/
│   └── 001_initial.sql  # Schema: users, payments, api_keys
├── tests/
│   └── test_payments.py # Pytest suite for payment flows
├── manage.py            # CLI tool for migrations and dev tasks
└── README.md
```

All payment operations go through `payments.py`, which validates inputs, talks to Stripe, and persists results atomically. Webhooks from Stripe hit `/webhooks/stripe`, are verified with the endpoint secret, and update local records.

## Contributing

1. Fork the repo and create a feature branch.
2. Write tests for new behavior.
3. Ensure all tests pass: `pytest`
4. Open a pull request.

### Review Requirements

- **PRs touching `payments.py` or any file in `migrations/` require review from a senior engineer on the payments team.** These files handle real money — changes must be carefully audited.
- All other files follow the standard review process (one approval required).

## License

Internal use only. Not for external distribution.

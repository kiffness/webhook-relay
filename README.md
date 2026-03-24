# WebhookRelay

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)
![GitHub release](https://img.shields.io/github/v/release/kiffness/webhook-relay)
![Tests](https://github.com/kiffness/webhook-relay/actions/workflows/tests.yml/badge.svg)

A lightweight, production-ready Python service for receiving, verifying, and forwarding webhooks.

Handles **GitHub → Slack** notifications for pull request and push events, with a generic endpoint for forwarding any payload to any HTTP endpoint.

---

## Features

- **Signature verification** — validates GitHub's HMAC-SHA256 signature on every request
- **Rich Slack notifications** — Slack Block Kit messages for PRs and pushes
- **Generic relay endpoint** — forward any JSON webhook to any URL
- **Retry with exponential backoff** — transient failures retried automatically
- **Async throughout** — FastAPI + httpx
- **Docker support** — single `docker compose up` to run

---

## Getting started

```bash
# 1. Clone and install
git clone https://github.com/your-username/webhook-relay.git
cd webhook-relay
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env — add GITHUB_WEBHOOK_SECRET and SLACK_WEBHOOK_URL

# 3. Run
uvicorn app.main:app --reload
```

Docs available at `http://localhost:8000/docs`

### Docker

```bash
cp .env.example .env  # fill in values
docker compose up --build
```

### Local testing with ngrok

```bash
ngrok http 8000
# Use the https URL as your GitHub webhook payload URL
```

---

## GitHub webhook setup

In your repo: **Settings → Webhooks → Add webhook**

| Field        | Value                                         |
| ------------ | --------------------------------------------- |
| Payload URL  | `https://xxxx.ngrok-free.app/webhooks/github` |
| Content type | `application/json`                            |
| Secret       | Value of `GITHUB_WEBHOOK_SECRET` in .env      |
| Events       | Pull requests, Pushes                         |

---

## Running tests

```bash
pytest tests/ -v
```

---

## Project structure

```
webhook-relay/
├── app/
│   ├── main.py              # FastAPI app and routes
│   ├── config.py            # Settings from environment variables
│   ├── models/
│   │   ├── github.py        # Pydantic models for GitHub payloads
│   │   └── slack.py         # Pydantic models for Slack messages
│   ├── handlers/
│   │   └── github.py        # Transform GitHub events → Slack messages
│   ├── forwarders/
│   │   └── slack.py         # HTTP client with retry logic
│   └── utils/
│       └── security.py      # HMAC-SHA256 signature verification
├── tests/
│   ├── test_security.py
│   └── test_github_handler.py
├── .env.example
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## Tech stack

- [FastAPI](https://fastapi.tiangolo.com/)
- [Pydantic v2](https://docs.pydantic.dev/)
- [httpx](https://www.python-httpx.org/)
- [uvicorn](https://www.uvicorn.org/)
- [pytest](https://pytest.org/)

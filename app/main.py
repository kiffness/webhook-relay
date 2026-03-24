import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.config import settings
from app.forwarders.slack import forward_generic, send_to_slack
from app.handlers.github import handle_pull_request, handle_push
from app.models.github import PullRequestEvent, PushEvent
from app.utils.security import verify_github_signature

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("WebhookRelay starting up")
    yield
    logger.info("WebhookRelay shutting down")

app = FastAPI(
    title="WebhookRelay",
    description=(
        "A lightweight Python service that receives webhooks from GitHub, "
        "verifies their signatures, and forwards formatted notifications to Slack "
        "or any other HTTP endpoint."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

@app.get("/health", tags=["Meta"])
async def health_check():
    """Simple liveness probe — returns 200 OK when the service is running."""
    return {"status": "ok"}

@app.post("/webhooks/github", tags=["GitHub"], status_code=status.HTTP_200_OK)
async def github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
):
    """
    Receive a GitHub webhook, verify the HMAC-SHA256 signature, parse the
    event payload, and forward a formatted notification to Slack.

    Supported event types: pull_request, push.
    All other event types are acknowledged but not forwarded.
    """
    raw_body = await request.body()

    if not verify_github_signature(raw_body, settings.github_webhook_secret, x_hub_signature_256):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    if not x_github_event:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-GitHub-Event header",
        )

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body is not valid JSON",
        )

    logger.info("Received GitHub event: %s", x_github_event)

    slack_message = None

    if x_github_event == "pull_request":
        try:
            event = PullRequestEvent(**payload)
        except ValidationError as exc:
            logger.error("Failed to parse pull_request payload: %s", exc)
            raise HTTPException(status_code=422, detail="Unexpected pull_request payload shape")
        slack_message = handle_pull_request(event)

    elif x_github_event == "push":
        try:
            event = PushEvent(**payload)
        except ValidationError as exc:
            logger.error("Failed to parse push payload: %s", exc)
            raise HTTPException(status_code=422, detail="Unexpected push payload shape")
        slack_message = handle_push(event)

    elif x_github_event == "ping":
        logger.info("Received GitHub ping — webhook configured correctly")
        return {"message": "pong"}

    else:
        logger.info("Ignoring unhandled event type: %s", x_github_event)
        return {"message": f"Event type '{x_github_event}' is not handled"}

    if slack_message is None:
        return {"message": "Event received but no notification sent"}

    delivered = await send_to_slack(slack_message)

    if not delivered:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Event received but Slack delivery failed"},
        )

    return {"message": "Event received and forwarded to Slack"}


@app.post("/webhooks/generic", tags=["Generic"], status_code=status.HTTP_200_OK)
async def generic_webhook(
    request: Request,
    destination_url: str,
):
    """
    Accept any JSON webhook payload and forward it as-is to the given
    destination_url query parameter.

    Example:
        POST /webhooks/generic?destination_url=https://your-endpoint.example.com
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body must be valid JSON",
        )

    logger.info("Generic relay to: %s", destination_url)
    delivered = await forward_generic(payload, destination_url)

    if not delivered:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"message": "Failed to forward payload to destination"},
        )

    return {"message": "Payload forwarded successfully"}
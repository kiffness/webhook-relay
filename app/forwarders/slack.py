import asyncio
import logging

import httpx

from app.config import settings
from app.models.slack import SlackMessage

logger = logging.getLogger(__name__)

async def send_to_slack(message: SlackMessage, webhook_url: str | None = None) -> bool:
    """
    Post a Slack Block Kit message to an incoming webhook URL.

    Retries on transient failures (5xx responses or connection errors) using
    exponential backoff. Returns True if the message was delivered successfully,
    False if all retry attempts were exhausted.
    """

    url = webhook_url or settings.slack_webhook_url

    if not url:
        logger.error("No Slack webhook URL configured - cannot forward message")
        return False

    payload = message.model_dump()
    max_attempts = settings.forward_max_attempts
    backoff = settings.forward_retry_backoff

    async with httpx.AsyncClient(timeout=10.0) as client:
        for attempt in range(1, max_attempts + 1):
            try:
                response = await client.post(url, json=payload)

                if response.status_code == 200:
                    logger.info("Slack message delivered successfully (attempt %d)", attempt)
                    return True

                logger.warning(
                    "Slack returned non-200 status %d on attempt %d: %s",
                    response.status_code,
                    attempt,
                    response.text,
                )

                if 400 <= response.status_code < 500:
                    logger.error("Client error from Slack — aborting retries")
                    return False

            except httpx.RequestError as exc:
                logger.warning("Network error on attempt %d: %s", attempt, exc)

            if attempt < max_attempts:
                wait = backoff * (2 ** (attempt - 1))
                logger.debug("Retrying in %.1fs…", wait)
                await asyncio.sleep(wait)

    logger.error("Failed to deliver Slack message after %d attempts", max_attempts)
    return False

async def forward_generic(payload: dict, destination_url: str) -> bool:
    """
    Forward an arbitrary JSON payload to any HTTP endpoint.
    Uses the same retry logic as send_to_slack.
    """
    max_attempts = settings.forward_retry_attempts
    backoff = settings.forward_retry_backoff

    async with httpx.AsyncClient(timeout=10.0) as client:
        for attempt in range(1, max_attempts + 1):
            try:
                response = await client.post(destination_url, json=payload)

                if response.is_success:
                    logger.info(
                        "Generic forward succeeded (attempt %d) status=%d",
                        attempt,
                        response.status_code,
                    )
                    return True

                logger.warning(
                    "Forward returned status %d on attempt %d",
                    response.status_code,
                    attempt,
                )

                if 400 <= response.status_code < 500:
                    return False

            except httpx.RequestError as exc:
                logger.warning("Network error on attempt %d: %s", attempt, exc)

            if attempt < max_attempts:
                wait = backoff * (2 ** (attempt - 1))
                await asyncio.sleep(wait)

    return False
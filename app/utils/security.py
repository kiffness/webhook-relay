import hashlib
import hmac
import logging

logger = logging.getLogger(__name__)

def verify_github_signature(payload_body: bytes, secret: str, signature_header: str | None) -> bool:
    """
       Verify that an incoming GitHub webhook payload is legitimate by checking
       the HMAC-SHA256 signature GitHub attaches to every request.

       GitHub signs the raw request body using the webhook secret you configure
       in your repo settings, then sends the signature in the X-Hub-Signature-256
       header as 'sha256=<hex_digest>'.

       Args:
           payload_body:      The raw bytes of the request body.
           secret:            The webhook secret configured in GitHub.
           signature_header:  The value of the X-Hub-Signature-256 header.

       Returns:
           True if the signature is valid, False otherwise.
    """
    if not secret:
        # If no secret is configured we skip verification — useful during local
        # development, but should never happen in production.
        logger.warning("No GitHub webhook secret configured — skipping signature verification")
        return True

    if not signature_header:
        logger.warning("Request received with no X-Hub-Signature-256 header")
        return False

    expected_prefix = "sha256="
    if not signature_header.startswith(expected_prefix):
        logger.warning("Signature header has unexpected format: %s", signature_header)
        return False

    expected_signature = hmac.new(
        key=secret.encode("utf-8"),
        msg=payload_body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    received_signature = signature_header[len(expected_prefix):]

    # Use hmac.compare_digest to prevent timing attacks
    is_valid = hmac.compare_digest(expected_signature, received_signature)

    if not is_valid:
        logger.warning("GitHub webhook signature mismatch — possible spoofed request")

    return is_valid
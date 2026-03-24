import hashlib
import hmac

from app.utils.security import verify_github_signature


def _make_signature(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


class TestVerifyGithubSignature:

    def test_valid_signature_returns_true(self):
        body = b'{"action": "opened"}'
        secret = "my-secret"
        sig = _make_signature(body, secret)
        assert verify_github_signature(body, secret, sig) is True

    def test_tampered_body_returns_false(self):
        body = b'{"action": "opened"}'
        secret = "my-secret"
        sig = _make_signature(body, secret)
        tampered = b'{"action": "closed"}'
        assert verify_github_signature(tampered, secret, sig) is False

    def test_wrong_secret_returns_false(self):
        body = b'{"action": "opened"}'
        sig = _make_signature(body, "correct-secret")
        assert verify_github_signature(body, "wrong-secret", sig) is False

    def test_missing_header_returns_false(self):
        assert verify_github_signature(b"body", "secret", None) is False

    def test_malformed_header_returns_false(self):
        assert verify_github_signature(b"body", "secret", "notsha256=abc") is False

    def test_no_secret_configured_skips_verification(self):
        assert verify_github_signature(b"body", "", "sha256=anything") is True

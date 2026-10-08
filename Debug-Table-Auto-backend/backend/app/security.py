"""Password hashing and opaque session token helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

PASSWORD_ALGORITHM = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 600_000
SALT_BYTES = 16
TOKEN_BYTES = 32


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )
    encoder = base64.urlsafe_b64encode
    return "$".join(
        (
            PASSWORD_ALGORITHM,
            str(PASSWORD_ITERATIONS),
            encoder(salt).decode("ascii").rstrip("="),
            encoder(digest).decode("ascii").rstrip("="),
        )
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, digest_text = encoded.split("$", 3)
        if algorithm != PASSWORD_ALGORITHM:
            return False
        iterations = int(iterations_text)
        if iterations < 100_000 or iterations > 2_000_000:
            return False
        padding = "=" * (-len(salt_text) % 4)
        salt = base64.urlsafe_b64decode((salt_text + padding).encode("ascii"))
        padding = "=" * (-len(digest_text) % 4)
        expected = base64.urlsafe_b64decode((digest_text + padding).encode("ascii"))
    except (ValueError, UnicodeError):
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)


def create_session_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(TOKEN_BYTES)
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return token, digest

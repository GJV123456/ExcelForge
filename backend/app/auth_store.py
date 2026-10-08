from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600_000)
    encode = lambda value: base64.urlsafe_b64encode(value).decode().rstrip("=")
    return f"pbkdf2_sha256$600000${encode(salt)}${encode(digest)}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, digest_text = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        padding = "=" * (-len(salt_text) % 4)
        salt = base64.urlsafe_b64decode((salt_text + padding).encode())
        padding = "=" * (-len(digest_text) % 4)
        expected = base64.urlsafe_b64decode((digest_text + padding).encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iterations_text))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


class AuthStore:
    def __init__(self, path: Path | None = None) -> None:
        configured = os.getenv("EXCELFORGE_DATABASE_PATH", "").strip()
        self.path = path or (Path(configured) if configured else (Path(__file__).parents[1] / "data" / "excelforge.sqlite3"))

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS auth_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    password_hash TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    is_enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_login_at TEXT
                );
                CREATE TABLE IF NOT EXISTS auth_sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
                    expires_at TEXT NOT NULL,
                    revoked_at TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def count_users(self) -> int:
        self.ensure_schema()
        with self._connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM auth_users").fetchone()[0])

    def create_user(self, username: str, password: str, display_name: str) -> dict[str, object]:
        self.ensure_schema()
        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    "INSERT INTO auth_users(username, password_hash, display_name) VALUES (?, ?, ?)",
                    (username, _hash_password(password), display_name),
                )
                return {"id": int(cursor.lastrowid), "username": username, "name": display_name}
        except sqlite3.IntegrityError as error:
            raise ValueError("用户名已存在") from error

    def authenticate(self, username: str, password: str) -> dict[str, object] | None:
        self.ensure_schema()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, username, password_hash, display_name FROM auth_users WHERE username = ? COLLATE NOCASE AND is_enabled = 1",
                (username,),
            ).fetchone()
            if row is None or not _verify_password(password, str(row["password_hash"])):
                return None
            connection.execute("UPDATE auth_users SET last_login_at = CURRENT_TIMESTAMP WHERE id = ?", (row["id"],))
        return {"id": int(row["id"]), "username": str(row["username"]), "name": str(row["display_name"])}

    def create_session(self, user_id: int, remember: bool) -> str:
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires = datetime.now(timezone.utc) + timedelta(days=30 if remember else 1)
        self.ensure_schema()
        with self._connect() as connection:
            connection.execute("INSERT INTO auth_sessions(token_hash, user_id, expires_at) VALUES (?, ?, ?)", (token_hash, user_id, expires.isoformat()))
        return token

    def user_by_token(self, token: str) -> dict[str, object] | None:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        self.ensure_schema()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT u.id, u.username, u.display_name, s.expires_at FROM auth_sessions s JOIN auth_users u ON u.id = s.user_id WHERE s.token_hash = ? AND s.revoked_at IS NULL AND u.is_enabled = 1",
                (token_hash,),
            ).fetchone()
        if row is None or datetime.fromisoformat(str(row["expires_at"])) <= datetime.now(timezone.utc):
            return None
        return {"id": int(row["id"]), "username": str(row["username"]), "name": str(row["display_name"])}

    def change_password(self, user_id: int, current: str, new: str) -> bool:
        self.ensure_schema()
        with self._connect() as connection:
            row = connection.execute("SELECT password_hash FROM auth_users WHERE id = ?", (user_id,)).fetchone()
            if row is None or not _verify_password(current, str(row["password_hash"])):
                return False
            connection.execute("UPDATE auth_users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (_hash_password(new), user_id))
            connection.execute("UPDATE auth_sessions SET revoked_at = CURRENT_TIMESTAMP WHERE user_id = ? AND revoked_at IS NULL", (user_id,))
        return True

    def revoke(self, token: str) -> None:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        self.ensure_schema()
        with self._connect() as connection:
            connection.execute("UPDATE auth_sessions SET revoked_at = CURRENT_TIMESTAMP WHERE token_hash = ?", (token_hash,))

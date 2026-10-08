"""SQLite persistence for users and login sessions."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from typing_extensions import TypedDict

from app.db.catalog import CatalogRepository
from app.exceptions import BusinessError
from app.security import create_session_token, hash_password, verify_password


class AuthUser(TypedDict):
    id: int
    username: str
    displayName: str


class AuthRepository:
    def __init__(self, database_path) -> None:  # type: ignore[no-untyped-def]
        self.database = CatalogRepository(database_path)

    def ensure_schema(self) -> None:
        self.database.ensure_schema()

    def count_users(self) -> int:
        self.ensure_schema()
        with closing(self.database._connect()) as connection:
            row = connection.execute("SELECT COUNT(*) FROM auth_users").fetchone()
        return int(row[0])

    def find_user(self, username: str) -> AuthUser | None:
        self.ensure_schema()
        with closing(self.database._connect()) as connection:
            row = connection.execute(
                "SELECT id, username, display_name FROM auth_users "
                "WHERE username = ? COLLATE NOCASE AND is_enabled = 1",
                (username,),
            ).fetchone()
        return self._user(row) if row else None

    def create_user(self, username: str, password: str, display_name: str) -> AuthUser:
        self.ensure_schema()
        try:
            with closing(self.database._connect()) as connection, connection:
                cursor = connection.execute(
                    """
                    INSERT INTO auth_users(username, password_hash, display_name)
                    VALUES (?, ?, ?)
                    """,
                    (username, hash_password(password), display_name),
                )
                user_id = int(cursor.lastrowid)
        except sqlite3.IntegrityError as error:
            raise BusinessError(
                "用户名已存在", "AUTH_USERNAME_EXISTS", path=["username"], status_code=409
            ) from error
        return {"id": user_id, "username": username, "displayName": display_name}

    def authenticate(self, username: str, password: str) -> AuthUser | None:
        self.ensure_schema()
        with closing(self.database._connect()) as connection:
            row = connection.execute(
                "SELECT id, username, password_hash, display_name FROM auth_users "
                "WHERE username = ? COLLATE NOCASE AND is_enabled = 1",
                (username,),
            ).fetchone()
        if row is None or not verify_password(password, str(row["password_hash"])):
            return None
        with closing(self.database._connect()) as connection, connection:
            connection.execute(
                "UPDATE auth_users SET last_login_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
                (int(row["id"]),),
            )
        return self._user(row)

    def create_session(self, user_id: int, remember: bool) -> str:
        self.ensure_schema()
        token, token_hash = create_session_token()
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=30 if remember else 1)
        with closing(self.database._connect()) as connection, connection:
            connection.execute(
                "INSERT INTO auth_sessions(token_hash, user_id, expires_at) VALUES (?, ?, ?)",
                (token_hash, user_id, expires.isoformat()),
            )
        return token

    def get_user_by_token(self, token: str) -> AuthUser | None:
        import hashlib

        self.ensure_schema()
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        with closing(self.database._connect()) as connection:
            row = connection.execute(
                """
                SELECT u.id, u.username, u.display_name, s.expires_at
                FROM auth_sessions AS s JOIN auth_users AS u ON u.id = s.user_id
                WHERE s.token_hash = ? AND s.revoked_at IS NULL AND u.is_enabled = 1
                """,
                (token_hash,),
            ).fetchone()
        if row is None:
            return None
        try:
            expired = datetime.fromisoformat(str(row["expires_at"])) <= datetime.now(timezone.utc)
        except ValueError:
            expired = True
        return None if expired else self._user(row)

    def change_password(self, user_id: int, current_password: str, new_password: str) -> None:
        self.ensure_schema()
        with closing(self.database._connect()) as connection:
            row = connection.execute(
                "SELECT password_hash FROM auth_users WHERE id = ? AND is_enabled = 1",
                (user_id,),
            ).fetchone()
        if row is None or not verify_password(current_password, str(row["password_hash"])):
            raise BusinessError("当前密码错误", "AUTH_CURRENT_PASSWORD_INVALID", status_code=400)
        with closing(self.database._connect()) as connection, connection:
            connection.execute(
                "UPDATE auth_users SET password_hash = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
                (hash_password(new_password), user_id),
            )
            connection.execute(
                "UPDATE auth_sessions SET revoked_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') "
                "WHERE user_id = ? AND revoked_at IS NULL",
                (user_id,),
            )

    def revoke_session(self, token: str) -> None:
        import hashlib

        self.ensure_schema()
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        with closing(self.database._connect()) as connection, connection:
            connection.execute(
                "UPDATE auth_sessions SET revoked_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') "
                "WHERE token_hash = ? AND revoked_at IS NULL",
                (token_hash,),
            )

    @staticmethod
    def _user(row: sqlite3.Row) -> AuthUser:
        return {
            "id": int(row["id"]),
            "username": str(row["username"]),
            "displayName": str(row["display_name"]),
        }

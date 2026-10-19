from __future__ import annotations

from app.config import Settings, apply_packaged_defaults


def test_packaged_app_uses_database_accounts_without_initial_login() -> None:
    settings = apply_packaged_defaults(Settings(), is_frozen=True)

    assert settings.auth_username is None
    assert settings.auth_password is None
    assert settings.auth_display_name is None


def test_source_app_does_not_supply_initial_admin_login() -> None:
    settings = apply_packaged_defaults(Settings(), is_frozen=False)

    assert settings.auth_username is None
    assert settings.auth_password is None
    assert settings.auth_display_name is None


def test_packaged_app_does_not_complete_partial_credentials() -> None:
    original = Settings(auth_username="operator")

    assert apply_packaged_defaults(original, is_frozen=True) is original


def test_packaged_environment_credentials_override_initial_login() -> None:
    original = Settings(
        auth_username="operator",
        auth_password="secret",
        auth_display_name="操作员",
    )

    assert apply_packaged_defaults(original, is_frozen=True) is original


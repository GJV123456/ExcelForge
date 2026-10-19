"""Existing frontend login request contract."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field, StrictBool, StringConstraints

from app.schemas.common import ApiModel

CredentialText = Annotated[
    str,
    StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=256),
]


class LoginRequest(ApiModel):
    username: CredentialText
    password: CredentialText
    agree: StrictBool
    remember: StrictBool = Field(description="Frontend preference; not persisted by backend")


class RegisterRequest(ApiModel):
    username: CredentialText
    password: CredentialText
    confirm_password: CredentialText = Field(alias="confirmPassword")
    display_name: CredentialText = Field(alias="displayName")
    agree: StrictBool


class ChangePasswordRequest(ApiModel):
    current_password: CredentialText = Field(alias="currentPassword")
    new_password: CredentialText = Field(alias="newPassword")
    confirm_password: CredentialText = Field(alias="confirmPassword")

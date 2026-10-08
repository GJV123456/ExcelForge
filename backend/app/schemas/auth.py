from __future__ import annotations

from typing import Annotated

from pydantic import Field, StringConstraints

from app.schemas.excel import ApiModel

CredentialText = Annotated[
    str,
    StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=256),
]


class LoginRequest(ApiModel):
    username: CredentialText
    password: CredentialText
    agree: bool
    remember: bool = False


class RegisterRequest(ApiModel):
    username: CredentialText
    password: CredentialText
    confirmPassword: CredentialText
    displayName: CredentialText
    agree: bool


class ChangePasswordRequest(ApiModel):
    currentPassword: CredentialText
    newPassword: CredentialText
    confirmPassword: CredentialText

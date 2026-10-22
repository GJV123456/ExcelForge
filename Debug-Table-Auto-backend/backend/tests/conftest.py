from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    with TestClient(create_app(Settings(mode="formal"))) as test_client:
        yield test_client

"""Test configuration: isolated database, no demo seed."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from uuid import uuid4

TMP_DIR = Path(tempfile.mkdtemp(prefix="campusconnect-test-"))
os.environ["DATABASE_URL"] = f"sqlite:///{(TMP_DIR / 'test.db').as_posix()}"
os.environ["DATA_DIR"] = str(TMP_DIR / "data")
os.environ["AUTO_SEED"] = "false"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["ADMIN_EMAIL"] = "admin@test.edu"
os.environ["ADMIN_PASSWORD"] = "AdminPass123"
os.environ["ADMIN_NAME"] = "Test Administrator"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def admin_headers(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@test.edu", "password": "AdminPass123"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(scope="session")
def student(client):
    """A student plus auth headers and profile."""
    email = f"student-{uuid4().hex[:8]}@test.edu"
    response = client.post(
        "/api/auth/register",
        json={"name": "Test Student", "email": email, "password": "Password123!"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return {
        "headers": {"Authorization": f"Bearer {body['access_token']}"},
        "user": body["user"],
        "password": "Password123!",
        "email": email,
    }


@pytest.fixture(scope="session")
def other_student(client):
    email = f"other-{uuid4().hex[:8]}@test.edu"
    response = client.post(
        "/api/auth/register",
        json={"name": "Other Student", "email": email, "password": "Password123!"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return {
        "headers": {"Authorization": f"Bearer {body['access_token']}"},
        "user": body["user"],
        "email": email,
    }

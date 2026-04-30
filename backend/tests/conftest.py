"""Pytest fixtures and shared setup for backend tests."""

import pytest


@pytest.fixture(autouse=True)
def reset_settings_cache() -> None:
    """Each test gets a fresh Settings instance from env."""
    from app.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Headers mimicking frontend Clerk session propagation."""
    return {
        "x-user-id": "user_test_123",
        "x-user-email": "tester@example.com",
        "x-org-id": "org_456",
        "x-user-roles": "admin, member",
    }

"""Shared test fixtures for unit tests.

Provides mock Snowflake session factories and utilities for testing
data pipeline logic without requiring actual Snowflake connections.
"""

# pyright: reportAny=false

import uuid
from collections.abc import Callable
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def test_run_id() -> str:
    """Generate unique identifier for test isolation.

    Returns short UUID suffix for creating isolated test schemas.
    """
    return uuid.uuid4().hex[:8]


@pytest.fixture
def mock_session() -> MagicMock:
    """Create a mock Snowflake Snowpark session.

    The mock supports chained calls like `session.sql(...).collect()`.
    Configure return values per test using:
    `mock_session.sql.return_value.collect.return_value`.
    """
    session = MagicMock()
    session.sql.return_value.collect.return_value = []
    return session


@pytest.fixture
def mock_session_factory() -> Callable[[], MagicMock]:
    """Factory fixture for creating mock sessions with different behaviors.

    Usage:
        def test_something(mock_session_factory):
            session = mock_session_factory()
            session.sql.return_value.collect.return_value = [{"COUNT": 100}]
    """

    def _create_mock_session() -> MagicMock:
        session = MagicMock()
        session.sql.return_value.collect.return_value = []
        return session

    return _create_mock_session

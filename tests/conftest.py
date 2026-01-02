"""Pytest configuration and shared fixtures for cabinet tests."""

from __future__ import annotations

import pytest
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cabinets.application.commands import GenerateLayoutCommand


# =============================================================================
# pytest-httpx fixture integration
# =============================================================================

# pytest-httpx provides httpx_mock fixture automatically when imported
# This conftest just ensures it's available


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: tests requiring external services (Ollama, etc.)"
    )
    config.addinivalue_line("markers", "slow: tests that take a long time to run")


# =============================================================================
# Shared fixtures for command creation
# =============================================================================


@pytest.fixture
def generate_command() -> "GenerateLayoutCommand":
    """Create a GenerateLayoutCommand instance using the factory.

    This fixture uses ServiceFactory to create a properly initialized
    GenerateLayoutCommand with all required dependencies.
    """
    from cabinets.application.factory import get_factory

    return get_factory().create_generate_command()

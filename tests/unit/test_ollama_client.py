"""Unit tests for Ollama client.

Tests cover:
- OllamaHealthCheck.is_available() with various HTTP responses
- OllamaHealthCheck.has_model() model detection logic
- OllamaHealthCheck.get_available_models() listing
- OllamaHealthCheck.get_model_info() detailed info
- check_ollama_sync() synchronous wrapper
- Custom base URL configuration
- Error handling for connection issues, timeouts, and bad responses
"""

from __future__ import annotations

import pytest
import httpx
from pytest_httpx import HTTPXMock

from cabinets.infrastructure.llm import OllamaHealthCheck, check_ollama_sync


# =============================================================================
# Test Class: OllamaHealthCheck.is_available()
# =============================================================================


class TestOllamaHealthCheckIsAvailable:
    """Tests for OllamaHealthCheck.is_available() method."""

    @pytest.mark.asyncio
    async def test_is_available_success(self, httpx_mock: HTTPXMock) -> None:
        """Returns True when server responds with 200."""
        httpx_mock.add_response(
            url="http://localhost:11434/api/tags",
            json={"models": []},
        )
        health = OllamaHealthCheck()
        assert await health.is_available() is True

    @pytest.mark.asyncio
    async def test_is_available_connection_error(self, httpx_mock: HTTPXMock) -> None:
        """Returns False on connection error."""
        httpx_mock.add_exception(httpx.ConnectError("Connection refused"))
        health = OllamaHealthCheck()
        assert await health.is_available() is False

    @pytest.mark.asyncio
    async def test_is_available_timeout(self, httpx_mock: HTTPXMock) -> None:
        """Returns False on timeout."""
        httpx_mock.add_exception(httpx.TimeoutException("Timeout"))
        health = OllamaHealthCheck()
        assert await health.is_available() is False

    @pytest.mark.asyncio
    async def test_is_available_non_200(self, httpx_mock: HTTPXMock) -> None:
        """Returns False on non-200 response."""
        httpx_mock.add_response(
            url="http://localhost:11434/api/tags",
            status_code=500,
        )
        health = OllamaHealthCheck()
        assert await health.is_available() is False

    @pytest.mark.asyncio
    async def test_is_available_404(self, httpx_mock: HTTPXMock) -> None:
        """Returns False on 404 response."""
        httpx_mock.add_response(
            url="http://localhost:11434/api/tags",
            status_code=404,
        )
        health = OllamaHealthCheck()
        assert await health.is_available() is False

    @pytest.mark.asyncio
    async def test_is_available_request_error(self, httpx_mock: HTTPXMock) -> None:
        """Returns False on general request error."""
        httpx_mock.add_exception(httpx.RequestError("Network error"))
        health = OllamaHealthCheck()
        assert await health.is_available() is False

    @pytest.mark.asyncio
    async def test_custom_base_url(self, httpx_mock: HTTPXMock) -> None:
        """Uses custom base URL when provided."""
        httpx_mock.add_response(
            url="http://custom:8080/api/tags",
            json={"models": []},
        )
        health = OllamaHealthCheck(base_url="http://custom:8080")
        assert await health.is_available() is True

    @pytest.mark.asyncio
    async def test_base_url_trailing_slash_removed(self, httpx_mock: HTTPXMock) -> None:
        """Trailing slash is removed from base URL."""
        httpx_mock.add_response(
            url="http://custom:8080/api/tags",
            json={"models": []},
        )
        health = OllamaHealthCheck(base_url="http://custom:8080/")
        assert health.base_url == "http://custom:8080"
        assert await health.is_available() is True


# =============================================================================
# Test Class: OllamaHealthCheck.has_model()
# =============================================================================


class TestOllamaHealthCheckHasModel:
    """Tests for OllamaHealthCheck.has_model() method."""

    @pytest.mark.asyncio
    async def test_has_model_found_exact(self, httpx_mock: HTTPXMock) -> None:
        """Returns True when model name matches exactly."""
        httpx_mock.add_response(
            url="http://localhost:11434/api/tags",
            json={"models": [{"name": "llama3.2"}]},
        )
        health = OllamaHealthCheck()
        assert await health.has_model("llama3.2") is True

    @pytest.mark.asyncio
    async def test_has_model_found_with_tag(self, httpx_mock: HTTPXMock) -> None:
        """Returns True when model name is a prefix (e.g., 'llama3.2' matches 'llama3.2:latest')."""
        httpx_mock.add_response(
            url="http://localhost:11434/api/tags",
            json={"models": [{"name": "llama3.2:latest"}]},
        )
        health = OllamaHealthCheck()
        assert await health.has_model("llama3.2") is True

    @pytest.mark.asyncio
    async def test_has_model_not_found(self, httpx_mock: HTTPXMock) -> None:
        """Returns False when model not in list."""
        httpx_mock.add_response(
            url="http://localhost:11434/api/tags",
            json={"models": [{"name": "mistral:7b"}]},
        )
        health = OllamaHealthCheck()
        assert await health.has_model("llama3.2") is False

    @pytest.mark.asyncio
    async def test_has_model_empty_list(self, httpx_mock: HTTPXMock) -> None:
        """Returns False when no models installed."""
        httpx_mock.add_response(
            url="http://localhost:11434/api/tags",
            json={"models": []},
        )
        health = OllamaHealthCheck()
        assert await health.has_model("llama3.2") is False

    @pytest.mark.asyncio
    async def test_has_model_connection_error(self, httpx_mock: HTTPXMock) -> None:
        """Returns False on connection error."""
        httpx_mock.add_exception(httpx.ConnectError("Connection refused"))
        health = OllamaHealthCheck()
        assert await health.has_model("llama3.2") is False

    @pytest.mark.asyncio
    async def test_has_model_timeout(self, httpx_mock: HTTPXMock) -> None:
        """Returns False on timeout."""
        httpx_mock.add_exception(httpx.TimeoutException("Timeout"))
        health = OllamaHealthCheck()
        assert await health.has_model("llama3.2") is False

    @pytest.mark.asyncio
    async def test_has_model_non_200(self, httpx_mock: HTTPXMock) -> None:
        """Returns False on non-200 response."""
        httpx_mock.add_response(
            url="http://localhost:11434/api/tags",
            status_code=500,
        )
        health = OllamaHealthCheck()
        assert await health.has_model("llama3.2") is False

    @pytest.mark.asyncio
    async def test_has_model_partial_match_not_prefix(
        self, httpx_mock: HTTPXMock
    ) -> None:
        """Returns False when model name is partial but not prefix match."""
        httpx_mock.add_response(
            url="http://localhost:11434/api/tags",
            json={"models": [{"name": "my-llama3.2:latest"}]},
        )
        health = OllamaHealthCheck()
        # 'llama3.2' should not match 'my-llama3.2:latest'
        assert await health.has_model("llama3.2") is False

    @pytest.mark.asyncio
    async def test_has_model_multiple_models(self, httpx_mock: HTTPXMock) -> None:
        """Returns True when target model is one of many."""
        httpx_mock.add_response(
            url="http://localhost:11434/api/tags",
            json={
                "models": [
                    {"name": "mistral:7b"},
                    {"name": "llama3.2:latest"},
                    {"name": "codellama:13b"},
                ]
            },
        )
        health = OllamaHealthCheck()
        assert await health.has_model("llama3.2") is True

    @pytest.mark.asyncio
    async def test_has_model_malformed_response(self, httpx_mock: HTTPXMock) -> None:
        """Returns False when response is malformed."""
        httpx_mock.add_response(
            url="http://localhost:11434/api/tags",
            json={"invalid": "response"},
        )
        health = OllamaHealthCheck()
        assert await health.has_model("llama3.2") is False


# =============================================================================
# Test Class: OllamaHealthCheck.get_available_models()
# =============================================================================


class TestOllamaHealthCheckGetAvailableModels:
    """Tests for OllamaHealthCheck.get_available_models() method."""

    @pytest.mark.asyncio
    async def test_get_available_models(self, httpx_mock: HTTPXMock) -> None:
        """Returns list of model names."""
        httpx_mock.add_response(
            url="http://localhost:11434/api/tags",
            json={
                "models": [
                    {"name": "llama3.2:latest"},
                    {"name": "mistral:7b"},
                ]
            },
        )
        health = OllamaHealthCheck()
        models = await health.get_available_models()
        assert "llama3.2:latest" in models
        assert "mistral:7b" in models
        assert len(models) == 2

    @pytest.mark.asyncio
    async def test_get_available_models_empty(self, httpx_mock: HTTPXMock) -> None:
        """Returns empty list when no models."""
        httpx_mock.add_response(
            url="http://localhost:11434/api/tags",
            json={"models": []},
        )
        health = OllamaHealthCheck()
        models = await health.get_available_models()
        assert models == []

    @pytest.mark.asyncio
    async def test_get_available_models_connection_error(
        self, httpx_mock: HTTPXMock
    ) -> None:
        """Returns empty list on connection error."""
        httpx_mock.add_exception(httpx.ConnectError("Connection refused"))
        health = OllamaHealthCheck()
        models = await health.get_available_models()
        assert models == []

    @pytest.mark.asyncio
    async def test_get_available_models_non_200(self, httpx_mock: HTTPXMock) -> None:
        """Returns empty list on non-200 response."""
        httpx_mock.add_response(
            url="http://localhost:11434/api/tags",
            status_code=500,
        )
        health = OllamaHealthCheck()
        models = await health.get_available_models()
        assert models == []

    @pytest.mark.asyncio
    async def test_get_available_models_skips_empty_names(
        self, httpx_mock: HTTPXMock
    ) -> None:
        """Skips models with empty or missing names."""
        httpx_mock.add_response(
            url="http://localhost:11434/api/tags",
            json={
                "models": [
                    {"name": "llama3.2:latest"},
                    {"name": ""},
                    {},  # Missing name
                    {"name": "mistral:7b"},
                ]
            },
        )
        health = OllamaHealthCheck()
        models = await health.get_available_models()
        assert models == ["llama3.2:latest", "mistral:7b"]


# =============================================================================
# Test Class: OllamaHealthCheck.get_model_info()
# =============================================================================


class TestOllamaHealthCheckGetModelInfo:
    """Tests for OllamaHealthCheck.get_model_info() method."""

    @pytest.mark.asyncio
    async def test_get_model_info_success(self, httpx_mock: HTTPXMock) -> None:
        """Returns model info dictionary on success."""
        model_info = {
            "name": "llama3.2:latest",
            "modified_at": "2024-01-01T00:00:00Z",
            "size": 4000000000,
        }
        httpx_mock.add_response(
            url="http://localhost:11434/api/show",
            json=model_info,
        )
        health = OllamaHealthCheck()
        info = await health.get_model_info("llama3.2")
        assert info == model_info

    @pytest.mark.asyncio
    async def test_get_model_info_not_found(self, httpx_mock: HTTPXMock) -> None:
        """Returns None when model not found (404)."""
        httpx_mock.add_response(
            url="http://localhost:11434/api/show",
            status_code=404,
        )
        health = OllamaHealthCheck()
        info = await health.get_model_info("nonexistent")
        assert info is None

    @pytest.mark.asyncio
    async def test_get_model_info_connection_error(self, httpx_mock: HTTPXMock) -> None:
        """Returns None on connection error."""
        httpx_mock.add_exception(httpx.ConnectError("Connection refused"))
        health = OllamaHealthCheck()
        info = await health.get_model_info("llama3.2")
        assert info is None

    @pytest.mark.asyncio
    async def test_get_model_info_non_200(self, httpx_mock: HTTPXMock) -> None:
        """Returns None on non-200 response."""
        httpx_mock.add_response(
            url="http://localhost:11434/api/show",
            status_code=500,
        )
        health = OllamaHealthCheck()
        info = await health.get_model_info("llama3.2")
        assert info is None


# =============================================================================
# Test Class: OllamaHealthCheck Configuration
# =============================================================================


class TestOllamaHealthCheckConfig:
    """Tests for OllamaHealthCheck configuration."""

    def test_default_base_url(self) -> None:
        """Default base URL is localhost:11434."""
        health = OllamaHealthCheck()
        assert health.base_url == "http://localhost:11434"

    def test_custom_base_url(self) -> None:
        """Custom base URL is used when provided."""
        health = OllamaHealthCheck(base_url="http://remote:8080")
        assert health.base_url == "http://remote:8080"

    def test_default_timeout(self) -> None:
        """Default timeout is 5.0 seconds."""
        health = OllamaHealthCheck()
        assert health.timeout == 5.0

    def test_custom_timeout(self) -> None:
        """Custom timeout is used when provided."""
        health = OllamaHealthCheck(timeout=10.0)
        assert health.timeout == 10.0


# =============================================================================
# Test Class: check_ollama_sync Function
# =============================================================================


class TestCheckOllamaSync:
    """Tests for synchronous check_ollama_sync function."""

    def test_unavailable(self, httpx_mock: HTTPXMock) -> None:
        """Returns False with message when unavailable."""
        httpx_mock.add_exception(httpx.ConnectError("Connection refused"))
        available, message = check_ollama_sync()
        assert available is False
        assert "not available" in message

    def test_available_no_model_check(self, httpx_mock: HTTPXMock) -> None:
        """Returns True when server available, no model check."""
        httpx_mock.add_response(
            url="http://localhost:11434/api/tags",
            json={"models": []},
        )
        available, message = check_ollama_sync()
        assert available is True
        assert "ready" in message.lower()

    def test_model_found(self, httpx_mock: HTTPXMock) -> None:
        """Returns True when model is found."""
        # check_ollama_sync makes two requests: is_available() then has_model()
        httpx_mock.add_response(
            url="http://localhost:11434/api/tags",
            json={"models": [{"name": "llama3.2:latest"}]},
        )
        httpx_mock.add_response(
            url="http://localhost:11434/api/tags",
            json={"models": [{"name": "llama3.2:latest"}]},
        )
        available, message = check_ollama_sync(model_name="llama3.2")
        assert available is True
        assert "ready" in message.lower()

    def test_model_not_found(self, httpx_mock: HTTPXMock) -> None:
        """Returns False with message when model not found."""
        # check_ollama_sync makes multiple requests: is_available(), has_model(), get_available_models()
        httpx_mock.add_response(
            url="http://localhost:11434/api/tags",
            json={"models": []},
        )
        httpx_mock.add_response(
            url="http://localhost:11434/api/tags",
            json={"models": []},
        )
        httpx_mock.add_response(
            url="http://localhost:11434/api/tags",
            json={"models": []},
        )
        available, message = check_ollama_sync(model_name="llama3.2")
        assert available is False
        assert "not found" in message
        assert "ollama pull" in message

    def test_model_not_found_lists_available(self, httpx_mock: HTTPXMock) -> None:
        """Lists available models when requested model not found."""
        # check_ollama_sync makes multiple requests: is_available(), has_model(), get_available_models()
        httpx_mock.add_response(
            url="http://localhost:11434/api/tags",
            json={"models": [{"name": "mistral:7b"}, {"name": "codellama:13b"}]},
        )
        httpx_mock.add_response(
            url="http://localhost:11434/api/tags",
            json={"models": [{"name": "mistral:7b"}, {"name": "codellama:13b"}]},
        )
        httpx_mock.add_response(
            url="http://localhost:11434/api/tags",
            json={"models": [{"name": "mistral:7b"}, {"name": "codellama:13b"}]},
        )
        available, message = check_ollama_sync(model_name="llama3.2")
        assert available is False
        assert "llama3.2" in message
        assert "not found" in message
        assert "Available models" in message or "mistral" in message

    def test_custom_base_url(self, httpx_mock: HTTPXMock) -> None:
        """Uses custom base URL when provided."""
        httpx_mock.add_response(
            url="http://custom:8080/api/tags",
            json={"models": []},
        )
        available, message = check_ollama_sync(base_url="http://custom:8080")
        assert available is True

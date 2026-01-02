"""Ollama health check and client utilities.

This module provides utilities for checking Ollama server availability
and model presence before attempting LLM generation.

Classes:
    OllamaHealthCheck: Health check for Ollama server and models
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class OllamaHealthCheck:
    """Check Ollama server availability and model presence.

    Provides methods to verify that the Ollama server is running
    and that the required model is available before attempting
    LLM generation. All methods are async for non-blocking I/O.

    Attributes:
        base_url: Base URL of the Ollama server (default: http://localhost:11434)
        timeout: Request timeout in seconds (default: 5.0)

    Example:
        >>> health = OllamaHealthCheck()
        >>> if await health.is_available():
        ...     if await health.has_model("llama3.2"):
        ...         # Safe to proceed with LLM generation
        ...         pass
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        timeout: float = 5.0,
    ) -> None:
        """Initialize the health check client.

        Args:
            base_url: Ollama server URL. Defaults to localhost.
            timeout: Request timeout in seconds. Defaults to 5.0.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def is_available(self) -> bool:
        """Check if Ollama server is responding.

        Makes a lightweight request to the /api/tags endpoint
        to verify the server is running and accepting connections.

        Returns:
            True if server is available, False otherwise.

        Note:
            This method catches all exceptions and returns False
            rather than raising, making it safe for conditional checks.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=self.timeout,
                )
                available = response.status_code == 200
                if available:
                    logger.debug(f"Ollama server available at {self.base_url}")
                else:
                    logger.debug(
                        f"Ollama server returned status {response.status_code}"
                    )
                return available
        except httpx.ConnectError:
            logger.debug(f"Could not connect to Ollama at {self.base_url}")
            return False
        except httpx.TimeoutException:
            logger.debug(f"Timeout connecting to Ollama at {self.base_url}")
            return False
        except httpx.RequestError as e:
            logger.debug(f"Request error checking Ollama: {e}")
            return False
        except Exception as e:
            logger.warning(f"Unexpected error checking Ollama availability: {e}")
            return False

    async def has_model(self, model_name: str) -> bool:
        """Check if a specific model is available on the server.

        Queries the /api/tags endpoint and checks if the specified
        model (or a model starting with the specified name) is present.

        Args:
            model_name: Name of the model to check (e.g., "llama3.2").
                       Partial matches are supported (e.g., "llama3.2" matches
                       "llama3.2:latest").

        Returns:
            True if model is available, False otherwise.

        Note:
            Returns False if the server is unavailable or any error occurs.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=self.timeout,
                )
                if response.status_code != 200:
                    logger.debug(
                        f"Failed to get model list: status {response.status_code}"
                    )
                    return False

                data = response.json()
                models = data.get("models", [])

                # Check for exact match or prefix match
                for model in models:
                    name = model.get("name", "")
                    if name == model_name or name.startswith(f"{model_name}:"):
                        logger.debug(f"Found model: {name}")
                        return True

                logger.debug(f"Model '{model_name}' not found in available models")
                return False

        except httpx.RequestError as e:
            logger.debug(f"Request error checking model: {e}")
            return False
        except (KeyError, ValueError, TypeError) as e:
            logger.debug(f"Error parsing model response: {e}")
            return False
        except Exception as e:
            logger.warning(f"Unexpected error checking model availability: {e}")
            return False

    async def get_available_models(self) -> list[str]:
        """Get list of all available models on the server.

        Queries the /api/tags endpoint and returns the names of
        all installed models.

        Returns:
            List of model names. Empty list if server unavailable or error.

        Example:
            >>> health = OllamaHealthCheck()
            >>> models = await health.get_available_models()
            >>> print(models)
            ['llama3.2:latest', 'mistral:7b', 'codellama:13b']
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=self.timeout,
                )
                if response.status_code != 200:
                    return []

                data = response.json()
                models = data.get("models", [])
                return [model.get("name", "") for model in models if model.get("name")]

        except Exception as e:
            logger.debug(f"Error getting model list: {e}")
            return []

    async def get_model_info(self, model_name: str) -> dict[str, Any] | None:
        """Get detailed information about a specific model.

        Queries the /api/show endpoint for model details.

        Args:
            model_name: Name of the model to query.

        Returns:
            Dictionary with model information, or None if not found/error.

        Note:
            This is a heavier operation than has_model() and should
            only be used when detailed model info is needed.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/show",
                    json={"name": model_name},
                    timeout=self.timeout,
                )
                if response.status_code != 200:
                    return None

                return response.json()

        except Exception as e:
            logger.debug(f"Error getting model info: {e}")
            return None


def check_ollama_sync(
    base_url: str = "http://localhost:11434",
    model_name: str | None = None,
) -> tuple[bool, str]:
    """Synchronous wrapper for Ollama health check.

    Convenience function for CLI usage where async is not needed.

    Args:
        base_url: Ollama server URL.
        model_name: Optional model name to check.

    Returns:
        Tuple of (success: bool, message: str) describing the result.

    Example:
        >>> available, message = check_ollama_sync(model_name="llama3.2")
        >>> if available:
        ...     print("Ready to generate!")
        ... else:
        ...     print(f"Not ready: {message}")
    """
    import asyncio

    async def _check() -> tuple[bool, str]:
        health = OllamaHealthCheck(base_url=base_url)

        if not await health.is_available():
            return False, f"Ollama server not available at {base_url}"

        if model_name:
            if not await health.has_model(model_name):
                models = await health.get_available_models()
                if models:
                    return False, (
                        f"Model '{model_name}' not found. "
                        f"Available models: {', '.join(models)}. "
                        f"Run: ollama pull {model_name}"
                    )
                return False, (
                    f"Model '{model_name}' not found. Run: ollama pull {model_name}"
                )

        return True, "Ollama ready"

    return asyncio.run(_check())

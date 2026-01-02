"""pydantic-ai agent definition for assembly instruction generation.

This module defines the pydantic-ai agent that generates assembly
instructions using the Ollama backend with structured outputs.

The agent uses:
- AssemblyDeps for dependency injection (cabinet context)
- AssemblyInstructions as the structured output schema
- Dynamic system prompts based on skill level

Example:
    >>> from cabinets.infrastructure.llm import run_assembly_agent, AssemblyDeps
    >>> deps = AssemblyDeps(cabinet=cabinet, cut_list=cut_list, ...)
    >>> result = await run_assembly_agent(deps)
    >>> print(result.title)
"""

from __future__ import annotations

import logging

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from cabinets.infrastructure.llm.models import AssemblyDeps, AssemblyInstructions
from cabinets.infrastructure.llm.prompts import (
    ASSEMBLY_SYSTEM_PROMPT,
    build_user_prompt,
    get_skill_prompt,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Agent Definition
# =============================================================================


def _create_ollama_model(
    model_name: str,
    ollama_url: str,
) -> OpenAIChatModel:
    """Create an Ollama model using OpenAI-compatible API.

    Ollama provides an OpenAI-compatible API at /v1, so we use
    OpenAIChatModel with a custom provider pointing to the Ollama server.

    Args:
        model_name: Model name (e.g., "llama3.2", "qwen3:30b").
            Should NOT include "ollama:" prefix.
        ollama_url: Base URL for Ollama server (without /v1 suffix).

    Returns:
        Configured OpenAIChatModel instance for use with pydantic-ai.
    """
    # Strip "ollama:" prefix if present
    if model_name.startswith("ollama:"):
        model_name = model_name[7:]

    # Ensure URL ends with /v1 for OpenAI-compatible endpoint
    base_url = ollama_url.rstrip("/")
    if not base_url.endswith("/v1"):
        base_url = f"{base_url}/v1"

    # Create OpenAI provider pointing to Ollama's OpenAI-compatible API
    # Use dummy API key since Ollama doesn't require authentication
    provider = OpenAIProvider(base_url=base_url, api_key="ollama")

    return OpenAIChatModel(model_name, provider=provider)


def create_assembly_agent(
    model: str = "ollama:llama3.2",
    ollama_url: str = "http://localhost:11434",
) -> Agent[AssemblyDeps, AssemblyInstructions]:
    """Create a configured assembly instruction agent.

    Creates a pydantic-ai Agent configured for assembly instruction
    generation with the specified Ollama model.

    Args:
        model: Model identifier in pydantic-ai format (e.g., "ollama:llama3.2").
        ollama_url: Base URL for Ollama server.

    Returns:
        Configured Agent ready for instruction generation.

    Note:
        The agent uses dynamic system prompts that adapt based on
        the skill_level in AssemblyDeps.
    """
    # Create model with configured Ollama provider
    model_instance = _create_ollama_model(model, ollama_url)

    agent: Agent[AssemblyDeps, AssemblyInstructions] = Agent(
        model_instance,
        deps_type=AssemblyDeps,
        output_type=AssemblyInstructions,
        system_prompt=ASSEMBLY_SYSTEM_PROMPT,
    )

    # Add dynamic skill-level prompt
    @agent.system_prompt
    def add_skill_prompt(ctx: RunContext[AssemblyDeps]) -> str:
        """Add skill-level-specific prompt additions.

        This decorator method is called by pydantic-ai to append
        skill-appropriate instructions to the system prompt.

        Args:
            ctx: Run context containing AssemblyDeps.

        Returns:
            Skill-level prompt additions.
        """
        return get_skill_prompt(ctx.deps.skill_level)

    return agent


# Default agent instance (can be overridden for testing)
_default_agent: Agent[AssemblyDeps, AssemblyInstructions] | None = None


def get_default_agent(
    model: str = "ollama:llama3.2",
    ollama_url: str = "http://localhost:11434",
) -> Agent[AssemblyDeps, AssemblyInstructions]:
    """Get or create the default assembly agent.

    Uses lazy initialization to avoid creating the agent until needed.
    This is useful for avoiding model loading during imports.

    Args:
        model: Model identifier.
        ollama_url: Ollama server URL.

    Returns:
        The default Agent instance.
    """
    global _default_agent
    if _default_agent is None:
        _default_agent = create_assembly_agent(model=model, ollama_url=ollama_url)
    return _default_agent


def reset_default_agent() -> None:
    """Reset the default agent.

    Useful for testing or when configuration changes.
    """
    global _default_agent
    _default_agent = None


# =============================================================================
# Agent Runner
# =============================================================================


async def run_assembly_agent(
    deps: AssemblyDeps,
    model: str = "ollama:llama3.2",
    ollama_url: str = "http://localhost:11434",
    agent: Agent[AssemblyDeps, AssemblyInstructions] | None = None,
) -> AssemblyInstructions:
    """Run the assembly agent to generate instructions.

    This is the main entry point for generating assembly instructions
    using the LLM. It handles building the user prompt and invoking
    the agent with the provided dependencies.

    Args:
        deps: Assembly dependencies including cabinet, cut list, etc.
        model: Ollama model identifier (default: "ollama:llama3.2").
        ollama_url: Ollama server URL (default: "http://localhost:11434").
        agent: Optional pre-configured agent (for testing).

    Returns:
        AssemblyInstructions with generated content.

    Raises:
        pydantic_ai.exceptions.ModelRetry: On model retry after validation failure.
        pydantic_ai.exceptions.UnexpectedModelBehavior: On unexpected LLM response.
        httpx.RequestError: On network errors to Ollama.

    Example:
        >>> deps = AssemblyDeps(
        ...     cabinet=cabinet,
        ...     cut_list=cut_list,
        ...     joinery=joinery,
        ...     skill_level="beginner",
        ...     material_type=MaterialType.PLYWOOD,
        ... )
        >>> instructions = await run_assembly_agent(deps)
        >>> print(instructions.title)
        "48\"W x 84\"H x 12\"D Cabinet Assembly"
    """
    # Use provided agent or create one
    if agent is None:
        agent = create_assembly_agent(model=model, ollama_url=ollama_url)

    # Build user prompt from dependencies
    user_prompt = build_user_prompt(
        cabinet=deps.cabinet,
        cut_list=deps.cut_list,
        joinery=deps.joinery,
        skill_level=deps.skill_level,
        has_doors=deps.has_doors,
        has_drawers=deps.has_drawers,
        has_decorative=deps.has_decorative_elements,
    )

    logger.debug(f"Running assembly agent with skill_level={deps.skill_level}")
    logger.debug(f"User prompt length: {len(user_prompt)} chars")

    # Run the agent
    result = await agent.run(user_prompt, deps=deps)

    logger.debug(f"Generated {len(result.output.steps)} assembly steps")
    logger.debug(f"Generated {len(result.output.safety_warnings)} safety warnings")

    return result.output


# =============================================================================
# Synchronous Wrapper
# =============================================================================


def run_assembly_agent_sync(
    deps: AssemblyDeps,
    model: str = "ollama:llama3.2",
    ollama_url: str = "http://localhost:11434",
) -> AssemblyInstructions:
    """Synchronous wrapper for run_assembly_agent.

    Convenience function for CLI and non-async contexts.

    Args:
        deps: Assembly dependencies.
        model: Ollama model identifier.
        ollama_url: Ollama server URL.

    Returns:
        AssemblyInstructions with generated content.
    """
    import asyncio

    return asyncio.run(run_assembly_agent(deps, model=model, ollama_url=ollama_url))


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "create_assembly_agent",
    "get_default_agent",
    "reset_default_agent",
    "run_assembly_agent",
    "run_assembly_agent_sync",
]

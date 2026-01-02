"""LLM integration module for enhanced assembly instructions.

This module provides LLM-based generation of assembly instructions
using pydantic-ai with Ollama as the local inference backend.

Submodules:
    models: Pydantic output schemas for LLM responses
    ollama_client: Health check and client utilities for Ollama
    prompts: System prompts and skill-level templates
    assembly_agent: pydantic-ai agent definition for assembly generation
"""

from __future__ import annotations

from .models import (
    AssemblyDeps,
    AssemblyInstructions,
    AssemblyStep,
    SafetyWarning,
    ToolRecommendation,
    TroubleshootingTip,
    WarningSeverity,
)
from .ollama_client import OllamaHealthCheck, check_ollama_sync
from .prompts import (
    ASSEMBLY_SYSTEM_PROMPT,
    BEGINNER_PROMPT_ADDITIONS,
    EXPERT_PROMPT_ADDITIONS,
    INTERMEDIATE_PROMPT_ADDITIONS,
    build_context_prompt,
    build_user_prompt,
    get_skill_prompt,
)
from .assembly_agent import (
    create_assembly_agent,
    get_default_agent,
    reset_default_agent,
    run_assembly_agent,
    run_assembly_agent_sync,
)
from .generator import LLMAssemblyGenerator

__all__ = [
    # LLM output models
    "AssemblyDeps",
    "AssemblyInstructions",
    "AssemblyStep",
    "SafetyWarning",
    "ToolRecommendation",
    "TroubleshootingTip",
    "WarningSeverity",
    # Ollama client
    "OllamaHealthCheck",
    "check_ollama_sync",
    # Prompts
    "ASSEMBLY_SYSTEM_PROMPT",
    "BEGINNER_PROMPT_ADDITIONS",
    "EXPERT_PROMPT_ADDITIONS",
    "INTERMEDIATE_PROMPT_ADDITIONS",
    "build_context_prompt",
    "build_user_prompt",
    "get_skill_prompt",
    # Agent
    "create_assembly_agent",
    "get_default_agent",
    "reset_default_agent",
    "run_assembly_agent",
    "run_assembly_agent_sync",
    # Generator
    "LLMAssemblyGenerator",
]

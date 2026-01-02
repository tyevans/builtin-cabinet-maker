"""Unit tests for assembly LLM configuration schema.

Tests cover:
- AssemblyOutputConfigSchema default values
- AssemblyOutputConfigSchema custom values
- Skill level validation
- Timeout range validation
- Ollama URL validation
- Model name validation
- Extra field validation (forbidden)
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from cabinets.application.config.schemas import AssemblyOutputConfigSchema


# =============================================================================
# Test Class: Default Values
# =============================================================================


class TestAssemblyOutputConfigSchemaDefaults:
    """Tests for AssemblyOutputConfigSchema default values."""

    def test_default_values(self) -> None:
        """Default values are correct."""
        config = AssemblyOutputConfigSchema()
        assert config.use_llm is False
        assert config.skill_level == "intermediate"
        assert config.llm_model == "llama3.2"
        assert config.ollama_url == "http://localhost:11434"
        assert config.timeout_seconds == 30
        assert config.include_troubleshooting is True
        assert config.include_time_estimates is True

    def test_legacy_fields_defaults(self) -> None:
        """Legacy fields have correct defaults."""
        config = AssemblyOutputConfigSchema()
        assert config.include_safety_warnings is True
        assert config.include_timestamps is True


# =============================================================================
# Test Class: Custom Values
# =============================================================================


class TestAssemblyOutputConfigSchemaCustomValues:
    """Tests for custom value assignment."""

    def test_custom_use_llm(self) -> None:
        """Custom use_llm value is accepted."""
        config = AssemblyOutputConfigSchema(use_llm=True)
        assert config.use_llm is True

    def test_custom_skill_level_beginner(self) -> None:
        """Skill level 'beginner' is accepted."""
        config = AssemblyOutputConfigSchema(skill_level="beginner")
        assert config.skill_level == "beginner"

    def test_custom_skill_level_intermediate(self) -> None:
        """Skill level 'intermediate' is accepted."""
        config = AssemblyOutputConfigSchema(skill_level="intermediate")
        assert config.skill_level == "intermediate"

    def test_custom_skill_level_expert(self) -> None:
        """Skill level 'expert' is accepted."""
        config = AssemblyOutputConfigSchema(skill_level="expert")
        assert config.skill_level == "expert"

    def test_custom_llm_model(self) -> None:
        """Custom model name is accepted."""
        config = AssemblyOutputConfigSchema(llm_model="mistral:7b")
        assert config.llm_model == "mistral:7b"

    def test_custom_ollama_url(self) -> None:
        """Custom Ollama URL is accepted."""
        config = AssemblyOutputConfigSchema(ollama_url="http://custom:8080")
        assert config.ollama_url == "http://custom:8080"

    def test_custom_timeout_seconds(self) -> None:
        """Custom timeout value is accepted."""
        config = AssemblyOutputConfigSchema(timeout_seconds=60)
        assert config.timeout_seconds == 60

    def test_custom_include_troubleshooting(self) -> None:
        """Custom include_troubleshooting value is accepted."""
        config = AssemblyOutputConfigSchema(include_troubleshooting=False)
        assert config.include_troubleshooting is False

    def test_custom_include_time_estimates(self) -> None:
        """Custom include_time_estimates value is accepted."""
        config = AssemblyOutputConfigSchema(include_time_estimates=False)
        assert config.include_time_estimates is False

    def test_all_custom_values(self) -> None:
        """All custom values together are accepted."""
        config = AssemblyOutputConfigSchema(
            use_llm=True,
            skill_level="beginner",
            llm_model="codellama:13b",
            ollama_url="http://llm-server:11434",
            timeout_seconds=120,
            include_troubleshooting=False,
            include_time_estimates=False,
            include_safety_warnings=False,
            include_timestamps=False,
        )
        assert config.use_llm is True
        assert config.skill_level == "beginner"
        assert config.llm_model == "codellama:13b"
        assert config.ollama_url == "http://llm-server:11434"
        assert config.timeout_seconds == 120
        assert config.include_troubleshooting is False
        assert config.include_time_estimates is False
        assert config.include_safety_warnings is False
        assert config.include_timestamps is False


# =============================================================================
# Test Class: Skill Level Validation
# =============================================================================


class TestSkillLevelValidation:
    """Tests for skill level validation."""

    def test_valid_skill_levels(self) -> None:
        """All valid skill levels are accepted."""
        for level in ["beginner", "intermediate", "expert"]:
            config = AssemblyOutputConfigSchema(skill_level=level)  # type: ignore[arg-type]
            assert config.skill_level == level

    def test_invalid_skill_level_novice(self) -> None:
        """Skill level 'novice' is rejected."""
        with pytest.raises(ValidationError):
            AssemblyOutputConfigSchema(skill_level="novice")  # type: ignore[arg-type]

    def test_invalid_skill_level_advanced(self) -> None:
        """Skill level 'advanced' is rejected."""
        with pytest.raises(ValidationError):
            AssemblyOutputConfigSchema(skill_level="advanced")  # type: ignore[arg-type]

    def test_invalid_skill_level_empty(self) -> None:
        """Empty skill level is rejected."""
        with pytest.raises(ValidationError):
            AssemblyOutputConfigSchema(skill_level="")  # type: ignore[arg-type]


# =============================================================================
# Test Class: Timeout Validation
# =============================================================================


class TestTimeoutValidation:
    """Tests for timeout_seconds validation."""

    def test_timeout_minimum_valid(self) -> None:
        """Timeout at minimum boundary (5) is accepted."""
        config = AssemblyOutputConfigSchema(timeout_seconds=5)
        assert config.timeout_seconds == 5

    def test_timeout_maximum_valid(self) -> None:
        """Timeout at maximum boundary (300) is accepted."""
        config = AssemblyOutputConfigSchema(timeout_seconds=300)
        assert config.timeout_seconds == 300

    def test_timeout_below_minimum(self) -> None:
        """Timeout below minimum (4) is rejected."""
        with pytest.raises(ValidationError):
            AssemblyOutputConfigSchema(timeout_seconds=4)

    def test_timeout_above_maximum(self) -> None:
        """Timeout above maximum (301) is rejected."""
        with pytest.raises(ValidationError):
            AssemblyOutputConfigSchema(timeout_seconds=301)

    def test_timeout_zero(self) -> None:
        """Timeout of 0 is rejected."""
        with pytest.raises(ValidationError):
            AssemblyOutputConfigSchema(timeout_seconds=0)

    def test_timeout_negative(self) -> None:
        """Negative timeout is rejected."""
        with pytest.raises(ValidationError):
            AssemblyOutputConfigSchema(timeout_seconds=-10)

    def test_timeout_middle_range(self) -> None:
        """Timeout in middle of range is accepted."""
        config = AssemblyOutputConfigSchema(timeout_seconds=150)
        assert config.timeout_seconds == 150


# =============================================================================
# Test Class: Ollama URL Validation
# =============================================================================


class TestOllamaUrlValidation:
    """Tests for ollama_url validation."""

    def test_url_http_valid(self) -> None:
        """HTTP URL is accepted."""
        config = AssemblyOutputConfigSchema(ollama_url="http://localhost:11434")
        assert config.ollama_url == "http://localhost:11434"

    def test_url_https_valid(self) -> None:
        """HTTPS URL is accepted."""
        config = AssemblyOutputConfigSchema(ollama_url="https://secure.server:11434")
        assert config.ollama_url == "https://secure.server:11434"

    def test_url_trailing_slash_removed(self) -> None:
        """Trailing slash is removed from URL."""
        config = AssemblyOutputConfigSchema(ollama_url="http://localhost:11434/")
        assert config.ollama_url == "http://localhost:11434"

    def test_url_no_scheme_rejected(self) -> None:
        """URL without scheme is rejected."""
        with pytest.raises(ValidationError):
            AssemblyOutputConfigSchema(ollama_url="localhost:11434")

    def test_url_invalid_scheme_rejected(self) -> None:
        """URL with invalid scheme is rejected."""
        with pytest.raises(ValidationError):
            AssemblyOutputConfigSchema(ollama_url="ftp://localhost:11434")

    def test_url_with_path(self) -> None:
        """URL with path is accepted."""
        config = AssemblyOutputConfigSchema(ollama_url="http://proxy/ollama")
        assert config.ollama_url == "http://proxy/ollama"


# =============================================================================
# Test Class: Model Name Validation
# =============================================================================


class TestModelNameValidation:
    """Tests for llm_model validation."""

    def test_valid_model_simple(self) -> None:
        """Simple model name is accepted."""
        config = AssemblyOutputConfigSchema(llm_model="llama3.2")
        assert config.llm_model == "llama3.2"

    def test_valid_model_with_tag(self) -> None:
        """Model name with tag is accepted."""
        config = AssemblyOutputConfigSchema(llm_model="llama3.2:latest")
        assert config.llm_model == "llama3.2:latest"

    def test_valid_model_with_size(self) -> None:
        """Model name with size tag is accepted."""
        config = AssemblyOutputConfigSchema(llm_model="mistral:7b")
        assert config.llm_model == "mistral:7b"

    def test_valid_model_with_variant(self) -> None:
        """Model name with variant is accepted."""
        config = AssemblyOutputConfigSchema(llm_model="codellama:13b-instruct")
        assert config.llm_model == "codellama:13b-instruct"

    def test_valid_model_with_dash(self) -> None:
        """Model name with dash is accepted."""
        config = AssemblyOutputConfigSchema(llm_model="phi-2")
        assert config.llm_model == "phi-2"

    def test_valid_model_with_underscore(self) -> None:
        """Model name with underscore is accepted."""
        config = AssemblyOutputConfigSchema(llm_model="my_custom_model")
        assert config.llm_model == "my_custom_model"

    def test_invalid_model_with_spaces(self) -> None:
        """Model name with spaces is rejected."""
        with pytest.raises(ValidationError):
            AssemblyOutputConfigSchema(llm_model="model with spaces")

    def test_invalid_model_with_special_chars(self) -> None:
        """Model name with special characters is rejected."""
        with pytest.raises(ValidationError):
            AssemblyOutputConfigSchema(llm_model="model@server")

    def test_invalid_model_with_slash(self) -> None:
        """Model name with slash is rejected."""
        with pytest.raises(ValidationError):
            AssemblyOutputConfigSchema(llm_model="org/model")


# =============================================================================
# Test Class: Extra Fields Validation
# =============================================================================


class TestExtraFieldsValidation:
    """Tests for extra field validation (should be forbidden)."""

    def test_extra_fields_forbidden(self) -> None:
        """Extra fields are rejected."""
        with pytest.raises(ValidationError):
            AssemblyOutputConfigSchema(unknown_field="value")  # type: ignore[call-arg]

    def test_multiple_extra_fields_forbidden(self) -> None:
        """Multiple extra fields are rejected."""
        with pytest.raises(ValidationError):
            AssemblyOutputConfigSchema(
                extra1="value1",  # type: ignore[call-arg]
                extra2="value2",
            )


# =============================================================================
# Test Class: JSON Serialization
# =============================================================================


class TestJsonSerialization:
    """Tests for JSON serialization/deserialization."""

    def test_model_dump(self) -> None:
        """Config can be dumped to dict."""
        config = AssemblyOutputConfigSchema(
            use_llm=True,
            skill_level="beginner",
        )
        data = config.model_dump()
        assert data["use_llm"] is True
        assert data["skill_level"] == "beginner"
        assert data["llm_model"] == "llama3.2"

    def test_model_dump_json(self) -> None:
        """Config can be dumped to JSON string."""
        config = AssemblyOutputConfigSchema()
        json_str = config.model_dump_json()
        assert isinstance(json_str, str)
        assert '"skill_level":"intermediate"' in json_str

    def test_model_validate_from_dict(self) -> None:
        """Config can be created from dict."""
        data = {
            "use_llm": True,
            "skill_level": "expert",
            "llm_model": "mistral:7b",
        }
        config = AssemblyOutputConfigSchema.model_validate(data)
        assert config.use_llm is True
        assert config.skill_level == "expert"
        assert config.llm_model == "mistral:7b"

    def test_model_validate_json(self) -> None:
        """Config can be created from JSON string."""
        json_str = '{"use_llm": true, "skill_level": "beginner"}'
        config = AssemblyOutputConfigSchema.model_validate_json(json_str)
        assert config.use_llm is True
        assert config.skill_level == "beginner"

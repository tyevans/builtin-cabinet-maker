"""Output format configuration schemas.

This module contains output configuration models including
OutputConfig and format-specific schemas for FRD-16.
"""

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class DxfOutputConfigSchema(BaseModel):
    """DXF export configuration.

    Controls how DXF (Drawing Exchange Format) files are generated for
    CNC machining and CAD software compatibility.

    Attributes:
        mode: Output mode - "per_panel" creates separate files, "combined" creates one file.
        units: Measurement units in the output file.
        hole_pattern: Pattern name for system holes (e.g., "32mm" for European system).
        hole_diameter: Diameter of system holes in inches.
    """

    model_config = ConfigDict(extra="forbid")

    mode: Literal["per_panel", "combined"] = "combined"
    units: Literal["inches", "mm"] = "inches"
    hole_pattern: str = "32mm"
    hole_diameter: float = Field(
        default=0.197, gt=0, description="Hole diameter in inches (5mm default)"
    )


class SvgOutputConfigSchema(BaseModel):
    """SVG export configuration.

    Controls how SVG (Scalable Vector Graphics) files are generated for
    web display, documentation, and 2D visualization.

    Attributes:
        scale: Pixels per inch scaling factor.
        show_dimensions: Whether to display dimension annotations.
        show_labels: Whether to display panel/component labels.
        show_grain: Whether to display grain direction indicators.
        use_panel_colors: Whether to use different colors for panel types.
    """

    model_config = ConfigDict(extra="forbid")

    scale: float = Field(default=10.0, gt=0, description="Pixels per inch")
    show_dimensions: bool = True
    show_labels: bool = True
    show_grain: bool = False
    use_panel_colors: bool = True


class BomOutputConfigSchema(BaseModel):
    """BOM (Bill of Materials) export configuration.

    Controls how the bill of materials is generated, including format
    and optional cost calculations.

    Attributes:
        format: Output format for the BOM.
        include_costs: Whether to include cost calculations (requires pricing data).
        sheet_size: Standard sheet dimensions for material calculations (width, height in inches).
    """

    model_config = ConfigDict(extra="forbid")

    format: Literal["text", "csv", "json"] = "text"
    include_costs: bool = False
    sheet_size: tuple[float, float] = Field(
        default=(48.0, 96.0),
        description="Standard sheet size (width, height) in inches",
    )

    @field_validator("sheet_size")
    @classmethod
    def validate_sheet_size(cls, v: tuple[float, float]) -> tuple[float, float]:
        """Validate that sheet dimensions are positive."""
        if v[0] <= 0 or v[1] <= 0:
            raise ValueError("Sheet dimensions must be positive")
        return v


class AssemblyOutputConfigSchema(BaseModel):
    """Assembly instructions export configuration.

    Controls how assembly instruction documents are generated,
    including safety information and metadata. Supports both
    template-based and LLM-based instruction generation.

    Attributes:
        include_safety_warnings: Whether to include safety warnings and precautions.
        include_timestamps: Whether to include generation timestamps.
        use_llm: Enable LLM-based instruction generation (requires Ollama).
        skill_level: Target skill level for LLM instructions.
        llm_model: Ollama model name for generation.
        ollama_url: Ollama server URL.
        timeout_seconds: LLM generation timeout in seconds.
        include_troubleshooting: Include troubleshooting tips section (LLM mode).
        include_time_estimates: Include time estimates per step (LLM mode).
    """

    model_config = ConfigDict(extra="forbid")

    # Existing fields
    include_safety_warnings: bool = True
    include_timestamps: bool = True

    # New LLM-related fields (FRD-20)
    use_llm: bool = Field(
        default=False,
        description="Enable LLM-based instruction generation (requires Ollama)",
    )
    skill_level: Literal["beginner", "intermediate", "expert"] = Field(
        default="intermediate", description="Target skill level for instructions"
    )
    llm_model: str = Field(
        default="llama3.2", description="Ollama model name for generation"
    )
    ollama_url: str = Field(
        default="http://localhost:11434", description="Ollama server URL"
    )
    timeout_seconds: int = Field(
        default=30,
        ge=5,
        le=300,
        description="LLM generation timeout in seconds (5-300)",
    )
    include_troubleshooting: bool = Field(
        default=True, description="Include troubleshooting tips section (LLM mode)"
    )
    include_time_estimates: bool = Field(
        default=True, description="Include time estimates per step (LLM mode)"
    )

    @field_validator("llm_model")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        """Validate model name format.

        Model names should be alphanumeric with optional colons and dots
        (e.g., "llama3.2", "llama3.2:latest", "mistral:7b").
        """
        import re

        if not re.match(r"^[a-zA-Z0-9._:-]+$", v):
            raise ValueError(
                f"Invalid model name '{v}'. "
                "Model names should contain only letters, numbers, dots, colons, and hyphens."
            )
        return v

    @field_validator("ollama_url")
    @classmethod
    def validate_ollama_url(cls, v: str) -> str:
        """Validate Ollama URL format.

        Must be a valid HTTP or HTTPS URL.
        """
        if not v.startswith(("http://", "https://")):
            raise ValueError(
                f"Invalid Ollama URL '{v}'. URL must start with http:// or https://"
            )
        return v.rstrip("/")


class JsonOutputConfigSchema(BaseModel):
    """Enhanced JSON export configuration.

    Controls what data is included in JSON exports for integration
    with other software or data analysis.

    Attributes:
        include_3d_positions: Include 3D position data for each panel.
        include_joinery: Include joinery details (dado, rabbet, etc.).
        include_warnings: Include woodworking warnings and advisories.
        include_bom: Include bill of materials data.
        indent: JSON indentation level (0 for compact).
    """

    model_config = ConfigDict(extra="forbid")

    include_3d_positions: bool = True
    include_joinery: bool = True
    include_warnings: bool = True
    include_bom: bool = True
    indent: int = Field(default=2, ge=0, description="JSON indentation spaces")


class OutputConfig(BaseModel):
    """Configuration for output format and file paths.

    Supports both legacy single-format output and new multi-format output
    with per-format configuration options.

    Attributes:
        format: Legacy single format type (use 'formats' for multi-format output).
        stl_file: Path to STL output file (optional).
        formats: List of output formats to generate (FRD-16).
        output_dir: Directory for output files (FRD-16).
        project_name: Base name for output files (FRD-16).
        dxf: DXF export configuration (FRD-16).
        svg: SVG export configuration (FRD-16).
        bom: BOM export configuration (FRD-16).
        assembly: Assembly instructions configuration (FRD-16).
        json_options: Enhanced JSON export configuration (FRD-16), aliased as "json" in config files.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    # Legacy fields
    format: Literal[
        "all",
        "cutlist",
        "diagram",
        "materials",
        "json",
        "stl",
        "cutlayout",
        "woodworking",
        "installation",
        "safety",
        "safety_labels",
        "llm-assembly",
    ] = "all"
    stl_file: str | None = None

    # New fields for FRD-16
    formats: list[str] = Field(
        default_factory=list, description="List of output formats to generate"
    )
    output_dir: str | None = Field(
        default=None, description="Directory for output files"
    )
    project_name: str = Field(
        default="cabinet", description="Base name for output files"
    )

    # Per-format configuration
    dxf: DxfOutputConfigSchema | None = None
    svg: SvgOutputConfigSchema | None = None
    bom: BomOutputConfigSchema | None = None
    assembly: AssemblyOutputConfigSchema | None = None
    json_options: JsonOutputConfigSchema | None = Field(default=None, alias="json")

    @field_validator("formats")
    @classmethod
    def validate_formats(cls, v: list[str]) -> list[str]:
        """Validate format names in the formats list."""
        valid_formats = {
            "stl",
            "dxf",
            "json",
            "bom",
            "svg",
            "assembly",
            "llm-assembly",
            "cutlist",
            "diagram",
            "materials",
            "woodworking",
            "installation",
        }
        invalid = set(v) - valid_formats - {"all"}
        if invalid:
            raise ValueError(
                f"Invalid formats: {invalid}. Valid formats: {sorted(valid_formats)}"
            )
        return v

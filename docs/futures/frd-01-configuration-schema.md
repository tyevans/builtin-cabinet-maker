# FRD-01: Configuration Schema & Loading System

**Created:** 2025-12-27
**Status:** Codebase Aligned and Ready for Task Breakdown
**Priority:** Foundation (blocks all future features)
**Refined:** 2025-12-27

---

## Problem Statement

The current CLI requires all parameters as command-line options. This becomes unwieldy for complex configurations and prevents saving/sharing designs. A JSON-based configuration system is needed as the foundation for all future features.

---

## Goals & Success Criteria

| Goal | Success Criteria |
|------|------------------|
| JSON config as primary input | Any design expressible via JSON; CLI options become overrides |
| Clear validation errors | Errors include JSON path (e.g., `cabinet.sections[0].width`) |
| Schema versioning | Breaking changes detectable; migration guidance provided |
| Template system | Users can start from bundled examples |
| Fast loading | Config load + validate < 500ms for typical files |

---

## Scope

### In Scope
- Pydantic v2 configuration models
- JSON Schema v1.0 with major.minor versioning
- CLI `--config` flag on existing commands
- CLI `validate` command
- CLI `templates list` and `templates init <name>` commands
- Configuration merging (CLI args override config values)
- Bundled starter templates (3-5 examples)

### Out of Scope
- YAML support (JSON only for v1)
- Config file auto-discovery
- Remote config loading
- Config file generation from CLI args
- GUI config editor

---

## Functional Requirements

### FR-01: Configuration Loading

- **FR-01.1**: CLI SHALL accept `--config`/`-c` flag with path to JSON file
- **FR-01.2**: If file not found, exit code 1 with message: `Error: Config file not found: {path}`
- **FR-01.3**: If JSON invalid, exit code 1 with message including line/column
- **FR-01.4**: CLI args SHALL override config file values (merge behavior)

### FR-02: Schema Validation

- **FR-02.1**: Config files SHALL include `schema_version` field (format: `"1.0"`)
- **FR-02.2**: Validator SHALL reject unsupported schema versions with clear message
- **FR-02.3**: All validation errors SHALL be collected and reported (not fail-fast)
- **FR-02.4**: Error messages SHALL include JSON path to invalid field

### FR-03: Validate Command

- **FR-03.1**: CLI SHALL provide `validate <config-file>` command
- **FR-03.2**: Exit codes: 0 = valid, 1 = errors, 2 = warnings only
- **FR-03.3**: Output SHALL distinguish errors (blocking) from warnings (advisory)
- **FR-03.4**: Warnings SHALL include woodworking advisories (e.g., shelf span limits)

### FR-04: Template System

- **FR-04.1**: CLI SHALL provide `templates list` showing available templates
- **FR-04.2**: CLI SHALL provide `templates init <name> [--output path]`
- **FR-04.3**: Templates SHALL be bundled in package (not external)
- **FR-04.4**: Minimum 3 templates: `simple-shelf`, `bookcase`, `cabinet-with-doors`

### FR-05: Configuration Merging

- **FR-05.1**: CLI flags SHALL override corresponding config values
- **FR-05.2**: Unspecified CLI flags SHALL use config values
- **FR-05.3**: If no config and no CLI flag, use documented defaults

---

## Configuration Schema (v1.0)

### Root Structure

```json
{
  "schema_version": "1.0",
  "cabinet": { ... },
  "output": { ... }
}
```

### Cabinet Configuration

```json
{
  "cabinet": {
    "width": 48.0,
    "height": 84.0,
    "depth": 12.0,
    "material": {
      "type": "plywood",
      "thickness": 0.75
    },
    "back_material": {
      "type": "plywood",
      "thickness": 0.25
    },
    "sections": [
      {
        "width": 24.0,
        "shelves": 3
      },
      {
        "width": "fill",
        "shelves": 4
      }
    ]
  }
}
```

### Field Definitions

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| `schema_version` | string | Yes | - | Pattern: `^\d+\.\d+$` |
| `cabinet.width` | float | Yes | - | 6.0 - 240.0 inches |
| `cabinet.height` | float | Yes | - | 6.0 - 120.0 inches |
| `cabinet.depth` | float | Yes | - | 4.0 - 36.0 inches |
| `cabinet.material.type` | enum | No | `"plywood"` | plywood, mdf, particle_board, solid_wood |
| `cabinet.material.thickness` | float | No | 0.75 | 0.25 - 2.0 inches |
| `cabinet.sections` | array | No | Single section | 1-20 sections |
| `cabinet.sections[].width` | float\|"fill" | No | `"fill"` | >0 or "fill" |
| `cabinet.sections[].shelves` | int | No | 0 | 0-20 |

### Output Configuration

```json
{
  "output": {
    "format": "all",
    "stl_file": "cabinet.stl"
  }
}
```

---

## Pydantic Models

Location: `src/cabinets/application/config/`

```python
# src/cabinets/application/config/schema.py

from pydantic import BaseModel, Field, field_validator
from typing import Literal
from enum import Enum

class MaterialType(str, Enum):
    PLYWOOD = "plywood"
    MDF = "mdf"
    PARTICLE_BOARD = "particle_board"
    SOLID_WOOD = "solid_wood"

class MaterialConfig(BaseModel):
    type: MaterialType = MaterialType.PLYWOOD
    thickness: float = Field(default=0.75, ge=0.25, le=2.0)

class SectionConfig(BaseModel):
    width: float | Literal["fill"] = "fill"
    shelves: int = Field(default=0, ge=0, le=20)

    @field_validator("width")
    @classmethod
    def validate_width(cls, v):
        if isinstance(v, (int, float)) and v <= 0:
            raise ValueError("width must be positive")
        return v

class CabinetConfig(BaseModel):
    width: float = Field(..., ge=6.0, le=240.0)
    height: float = Field(..., ge=6.0, le=120.0)
    depth: float = Field(..., ge=4.0, le=36.0)
    material: MaterialConfig = Field(default_factory=MaterialConfig)
    back_material: MaterialConfig | None = None
    sections: list[SectionConfig] = Field(default_factory=list, max_length=20)

class OutputConfig(BaseModel):
    format: Literal["all", "cutlist", "diagram", "materials", "json", "stl"] = "all"
    stl_file: str | None = None

class CabinetConfiguration(BaseModel):
    """Root configuration model."""
    schema_version: str = Field(..., pattern=r"^\d+\.\d+$")
    cabinet: CabinetConfig
    output: OutputConfig = Field(default_factory=OutputConfig)

    model_config = {"extra": "forbid"}
```

---

## CLI Interface

### Updated Generate Command

```bash
# With config file
cabinets generate --config my-cabinet.json

# Config with CLI overrides
cabinets generate --config my-cabinet.json --width 60

# Original CLI-only usage still works
cabinets generate --width 48 --height 84 --depth 12
```

### Validate Command

```bash
$ cabinets validate my-cabinet.json

Validating my-cabinet.json...

Errors:
  cabinet.width: Value -10 is less than minimum 6.0
  cabinet.sections[1].shelves: Value 25 exceeds maximum 20

Warnings:
  cabinet.sections[0]: Shelf span of 42" exceeds recommended 36" for 3/4" plywood

Validation failed: 2 errors, 1 warning
```

### Templates Commands

```bash
$ cabinets templates list

Available templates:
  simple-shelf    - Basic wall shelf unit
  bookcase        - Standard bookcase with adjustable shelves
  cabinet-doors   - Base cabinet with door openings

$ cabinets templates init bookcase --output my-bookcase.json
Created: my-bookcase.json
```

---

## Error Message Format

### Validation Error Structure

```python
@dataclass
class ValidationError:
    path: str          # e.g., "cabinet.sections[0].width"
    message: str       # e.g., "Value must be positive"
    value: Any         # The invalid value

@dataclass
class ValidationWarning:
    path: str
    message: str
    suggestion: str | None = None
```

### Example Error Output

```
Error at cabinet.sections[2].width:
  Value: -5
  Problem: Section width must be positive

Error at cabinet.material.type:
  Value: "oak"
  Problem: Invalid material type
  Valid options: plywood, mdf, particle_board, solid_wood
```

---

## File Structure

```
src/cabinets/
  application/
    config/
      __init__.py
      schema.py          # Pydantic models
      loader.py          # Load and parse JSON
      validator.py       # Validation logic
      merger.py          # CLI + config merging
    templates/
      __init__.py
      manager.py         # Template operations
      data/
        simple-shelf.json
        bookcase.json
        cabinet-doors.json
  cli/
    main.py              # Updated with --config
    commands/
      validate.py        # New validate command
      templates.py       # New templates commands
```

---

## Testing Strategy

### Unit Tests
- Pydantic model validation (valid/invalid inputs)
- Config loader error handling
- CLI arg + config merging logic
- Template file parsing

### Integration Tests
- End-to-end: config file to generated output
- Validate command with various error cases
- Templates init creates valid, loadable files

### Test Cases

| Test | Input | Expected |
|------|-------|----------|
| Valid minimal config | `{schema_version, cabinet}` | Loads successfully |
| Missing required field | No `cabinet.width` | Error with path |
| Invalid type | `width: "big"` | Type error with path |
| Unknown field | `cabinet.color: "red"` | Error (extra="forbid") |
| Version mismatch | `schema_version: "2.0"` | Unsupported version error |
| CLI override | `--width 60` + config | Width = 60 |

---

## Implementation Phases

### Phase 1: Core Schema (Week 1)
- [ ] Create Pydantic models in `application/config/schema.py`
- [ ] Implement ConfigLoader with JSON parsing
- [ ] Add `--config` flag to `generate` command
- [ ] Basic error formatting with JSON paths

### Phase 2: Validation & Templates (Week 2)
- [ ] Implement `validate` command
- [ ] Add warning system for woodworking advisories
- [ ] Create template manager and bundled templates
- [ ] Implement `templates list` and `templates init`

### Phase 3: Polish (Week 3)
- [ ] CLI arg + config merging
- [ ] Comprehensive error messages
- [ ] Documentation and examples
- [ ] Test coverage > 90%

---

## Dependencies

### Python Packages (to add)
```toml
# pyproject.toml
dependencies = [
    "pydantic>=2.0",
    # existing deps...
]
```

### Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| Pydantic v2 learning curve | Medium | Use simple patterns; reference docs |
| Schema evolution | High | Strict versioning from day 1 |
| Template maintenance | Low | Keep templates minimal |

---

## Open Questions

1. **Section width "fill" behavior**: When multiple sections use "fill", split equally or error?
   - Proposed: Split equally among all "fill" sections

2. **Config file search paths**: Support `./cabinet.json` auto-discovery?
   - Proposed: No, explicit `--config` only for v1

3. **Schema version compatibility**: Support `1.x` configs with `1.0` parser?
   - Proposed: Yes, minor versions are backwards compatible

---

## Implementation Analysis

### Backend Support Analysis

#### Current State

**Relevant Files:**
- `/src/cabinets/domain/value_objects.py` - MaterialType enum, MaterialSpec class
- `/src/cabinets/domain/entities.py` - Cabinet, Section, Shelf, Wall entities
- `/src/cabinets/domain/services.py` - LayoutCalculator, LayoutParameters
- `/src/cabinets/application/dtos.py` - WallInput, LayoutParametersInput, LayoutOutput
- `/src/cabinets/application/commands.py` - GenerateLayoutCommand
- `/src/cabinets/cli/main.py` - Typer CLI with generate, cutlist, materials, diagram commands

**Existing Patterns:**
1. **MaterialType enum** already matches FRD schema exactly (`plywood`, `mdf`, `particle_board`, `solid_wood`)
2. **MaterialSpec** value object with `thickness` and `material_type` fields
3. **Validation pattern** using `validate()` methods that return `list[str]` of error messages
4. **Command pattern** with `GenerateLayoutCommand.execute()` returning `LayoutOutput` with `is_valid` and `errors`
5. **Clean architecture** with domain/application/infrastructure separation

**Current Capabilities:**
- Cabinet dimension validation (width 0-240, height 0-120, depth 0-36)
- Material type validation against enum
- Error collection (not fail-fast) in DTOs
- Section generation with uniform shelf distribution

#### Needed Work

**High Priority (Core Schema):**
- [ ] Add `pydantic>=2.0` to dependencies (Complexity: Low)
- [ ] Create `src/cabinets/application/config/` package (Complexity: Low)
- [ ] Create Pydantic models in `config/schema.py` (Complexity: Medium)
  - Note: Should **reuse** existing `MaterialType` enum from domain layer
- [ ] Implement `ConfigLoader` in `config/loader.py` (Complexity: Medium)
  - JSON parsing with line/column error reporting
  - File existence checking

**Medium Priority (Section Configuration):**
- [ ] Add `"fill"` width support to domain layer (Complexity: Medium)
  - Current `LayoutCalculator.generate_cabinet()` calculates equal section widths
  - Need: Algorithm to resolve mixed fixed/fill widths
  - Location: `domain/services.py` lines 40-84

**Decision Required - Lateral Move LM-02:**
Should existing `WallInput`/`LayoutParametersInput` DTOs be:
1. **Replaced** with Pydantic models (cleaner, but breaking internal API)
2. **Preserved** with conversion layer from config models (more code, but non-breaking)

**Recommendation:** Option 2 - Create adapter/converter in `config/merger.py` that converts `CabinetConfiguration` to existing DTOs. This preserves current command structure and allows gradual migration.

#### Recommended Approach

1. **Preserve domain layer** - Reuse `MaterialType` enum, don't duplicate
2. **Add config layer** as new subpackage under application
3. **Create adapters** to convert Pydantic config models to existing DTOs
4. **Extend LayoutCalculator** to accept section width specifications

```python
# Proposed conversion flow:
# JSON file -> CabinetConfiguration (Pydantic) -> ConfigToDto adapter -> WallInput + LayoutParametersInput -> GenerateLayoutCommand
```

---

### CLI Patterns Analysis

#### Current State

**Relevant Files:**
- `/src/cabinets/cli/main.py` - All CLI commands

**Existing Patterns:**
1. **Typer app** with `@app.command()` decorators
2. **Annotated parameters** with `typer.Option()` for help text and short flags
3. **Error handling** via `typer.Exit(code=1)` with `typer.echo()` to stderr
4. **Multiple commands** sharing same parameter patterns (generate, cutlist, materials, diagram)

**Current Commands:**
- `generate` - Main command with all options, supports multiple output formats
- `cutlist` - Subset, shows cut list only
- `materials` - Subset, shows material estimate only
- `diagram` - Subset, shows ASCII diagram only

**Output Format Handling:**
- `--format` flag accepts: `all`, `cutlist`, `diagram`, `materials`, `json`, `stl`
- STL output requires `--output` flag for file path

#### Needed Work

- [ ] Add `--config`/`-c` option to `generate` command (Complexity: Low)
  - Type: `Path | None`
  - Make `width`, `height`, `depth` optional when config provided
- [ ] Add `validate` command (Complexity: Medium)
  - New file: `src/cabinets/cli/commands/validate.py`
  - Exit codes: 0=valid, 1=errors, 2=warnings only
- [ ] Add `templates` command group (Complexity: Medium)
  - New file: `src/cabinets/cli/commands/templates.py`
  - Subcommands: `list`, `init <name> [--output path]`
- [ ] Refactor `generate` to support config loading (Complexity: Medium)
  - Load config if `--config` provided
  - Merge CLI overrides with config values
  - Fall back to required CLI args if no config

**FRD Correction Needed:**
The FRD proposes file structure with `cli/commands/` subdirectory, but current codebase has single `cli/main.py`. Options:
1. Add commands to `main.py` (simpler, matches current pattern)
2. Create `commands/` subdirectory (FRD approach, more modular)

**Recommendation:** Option 2 - Create `commands/` subdirectory for new commands to keep `main.py` focused on core generate functionality.

#### Recommended Approach

```python
# Updated generate command signature
@app.command()
def generate(
    config: Annotated[Path | None, typer.Option("--config", "-c")] = None,
    # Existing options become optional when config provided
    width: Annotated[float | None, typer.Option("--width", "-w")] = None,
    # ...
):
    if config:
        # Load and validate config
        # Merge with CLI overrides
    elif width is None or height is None or depth is None:
        typer.echo("Error: --width, --height, --depth required when --config not provided")
        raise typer.Exit(code=1)
```

---

### Configuration Merging Strategy

#### Current State

No merging logic exists. CLI parameters directly populate DTOs.

#### Needed Work

- [ ] Create `config/merger.py` with `ConfigMerger` class (Complexity: Medium)
- [ ] Define merge precedence: CLI args > config values > defaults
- [ ] Handle partial CLI overrides (e.g., only `--width` specified)

**Algorithm:**
```python
def merge(config: CabinetConfiguration, cli_args: dict) -> CabinetConfiguration:
    # Start with config values
    # Override with any non-None CLI args
    # Return merged config
```

**Edge Cases to Handle:**
1. CLI provides `--width` but config has sections with fixed widths that sum > new width
2. CLI provides `--sections` but config has explicit section array
3. Nested overrides (e.g., `--material-thickness` overriding `cabinet.material.thickness`)

**Recommendation:** For v1, support only top-level overrides (`--width`, `--height`, `--depth`, `--thickness`). Nested section-level overrides require more complex CLI design.

---

### Template System Design

#### Current State

No template system exists. No bundled configuration files.

#### Needed Work

- [ ] Create `src/cabinets/application/templates/` package (Complexity: Low)
- [ ] Create `templates/data/` directory for JSON files (Complexity: Low)
- [ ] Implement `TemplateManager` class (Complexity: Medium)
  - `list_templates()` -> list of (name, description) tuples
  - `get_template(name)` -> template file path
  - `init_template(name, output_path)` -> copy template to destination
- [ ] Create 3 bundled templates (Complexity: Low)
  - `simple-shelf.json`
  - `bookcase.json`
  - `cabinet-doors.json` (Note: doors not yet supported in domain - this template would need to be shelf-only or mark doors as future)

**Package Data Consideration:**
Templates must be bundled with the installed package. Options:
1. Use `importlib.resources` (Python 3.9+ standard library)
2. Use `pkg_resources` (setuptools, older)

**Recommendation:** Use `importlib.resources` for modern Python compatibility.

```python
# In templates/manager.py
from importlib import resources

def get_template_path(name: str) -> Path:
    with resources.files("cabinets.application.templates.data").joinpath(f"{name}.json") as path:
        return path
```

**pyproject.toml update needed:**
```toml
[tool.setuptools.package-data]
"cabinets.application.templates" = ["data/*.json"]
```

---

### Validation System Design

#### Current State

**Existing Validation:**
- `WallInput.validate()` returns `list[str]` errors
- `LayoutParametersInput.validate()` returns `list[str]` errors
- No JSON path information in error messages
- No warning system (only blocking errors)

#### Needed Work

- [ ] Create `config/validator.py` with validation orchestration (Complexity: Medium)
- [ ] Create `ValidationError` and `ValidationWarning` dataclasses (Complexity: Low)
- [ ] Implement woodworking advisories as warnings (Complexity: Medium)
  - Shelf span > 36" for 3/4" plywood
  - Very thin shelves (< 0.5" thickness)
  - Extreme aspect ratios

**Pydantic Integration:**
Pydantic v2 provides `ValidationError` with `errors()` method that includes `loc` (location tuple) for JSON path construction.

```python
try:
    config = CabinetConfiguration.model_validate(data)
except PydanticValidationError as e:
    for error in e.errors():
        path = ".".join(str(p) for p in error["loc"])
        # e.g., "cabinet.sections.0.width"
```

**Warning System (New):**
```python
def check_warnings(config: CabinetConfiguration) -> list[ValidationWarning]:
    warnings = []
    for i, section in enumerate(config.cabinet.sections):
        if section.width and section.width > 36 and config.cabinet.material.thickness <= 0.75:
            warnings.append(ValidationWarning(
                path=f"cabinet.sections[{i}]",
                message="Shelf span exceeds recommended 36\" for 3/4\" material",
                suggestion="Consider adding a center support or using thicker material"
            ))
    return warnings
```

---

### Dependency and Infrastructure Considerations

#### Dependencies to Add

```toml
# pyproject.toml
dependencies = [
    "numpy-stl>=3.2.0",
    "typer>=0.21.0",
    "pydantic>=2.0",  # NEW
]
```

#### Package Structure Changes

```
src/cabinets/
  application/
    config/                    # NEW
      __init__.py
      schema.py                # Pydantic models
      loader.py                # JSON loading
      validator.py             # Validation + warnings
      merger.py                # CLI + config merging
    templates/                 # NEW
      __init__.py
      manager.py               # Template operations
      data/                    # NEW
        simple-shelf.json
        bookcase.json
        cabinet-doors.json
  cli/
    main.py                    # MODIFY: add --config
    commands/                  # NEW
      __init__.py
      validate.py              # validate command
      templates.py             # templates commands
```

---

### Testing Requirements

#### Current Test Coverage

No tests directory found in codebase. Testing infrastructure needs to be established.

#### Needed Work

- [ ] Create `tests/` directory structure (Complexity: Low)
- [ ] Add pytest to dev dependencies (Complexity: Low)
- [ ] Write unit tests for Pydantic models (Complexity: Medium)
- [ ] Write integration tests for config loading (Complexity: Medium)
- [ ] Write CLI tests using typer.testing.CliRunner (Complexity: Medium)

**Recommended Test Structure:**
```
tests/
  unit/
    test_config_schema.py
    test_config_loader.py
    test_config_merger.py
    test_template_manager.py
  integration/
    test_generate_with_config.py
    test_validate_command.py
    test_templates_command.py
  fixtures/
    valid_config.json
    invalid_config.json
    ...
```

---

## Appendix: Example Configurations

### Simple Shelf

```json
{
  "schema_version": "1.0",
  "cabinet": {
    "width": 36,
    "height": 48,
    "depth": 10,
    "sections": [
      {"shelves": 4}
    ]
  }
}
```

### Bookcase with Sections

```json
{
  "schema_version": "1.0",
  "cabinet": {
    "width": 72,
    "height": 84,
    "depth": 12,
    "material": {"type": "plywood", "thickness": 0.75},
    "sections": [
      {"width": 24, "shelves": 5},
      {"width": 24, "shelves": 5},
      {"width": "fill", "shelves": 5}
    ]
  },
  "output": {
    "format": "all"
  }
}
```

---

## Implementation Summary

### Complexity Assessment

| Component | Complexity | Effort Estimate | Risk |
|-----------|------------|-----------------|------|
| Pydantic schema models | Medium | 2-3 days | Low |
| Config loader | Medium | 1-2 days | Low |
| CLI --config integration | Medium | 2 days | Low |
| Configuration merging | Medium | 2 days | Medium |
| Validate command | Medium | 1-2 days | Low |
| Template system | Low-Medium | 2 days | Low |
| Section "fill" width support | Medium | 2-3 days | Medium |
| Testing infrastructure | Medium | 2-3 days | Low |
| **Total** | | **14-19 days** | |

### Implementation Order (Recommended)

1. **Phase 0: Infrastructure Setup** (1 day)
   - Add pydantic dependency
   - Create package structure (`config/`, `templates/`, `cli/commands/`)
   - Add pytest to dev dependencies

2. **Phase 1: Core Schema** (5-6 days)
   - Pydantic models (reuse domain `MaterialType`)
   - ConfigLoader with JSON parsing and error formatting
   - Basic integration with `generate` command

3. **Phase 2: CLI Enhancement** (4-5 days)
   - `--config` flag with required parameter handling
   - Configuration merging (CLI overrides)
   - `validate` command with error/warning distinction

4. **Phase 3: Template System** (3-4 days)
   - TemplateManager with `importlib.resources`
   - `templates list` and `templates init` commands
   - 3 bundled template files

5. **Phase 4: Domain Enhancement** (2-3 days)
   - Section "fill" width resolution algorithm
   - Update LayoutCalculator to accept section specifications

### Key Decisions Required

1. **LM-02: DTO Strategy** - Preserve existing DTOs with conversion layer (recommended) vs. replace with Pydantic models
2. **CLI Override Scope** - Support only top-level overrides for v1 (recommended) vs. nested section-level overrides
3. **Template Content** - `cabinet-doors.json` scope given doors not yet implemented in domain

### Lateral Moves Documented

| ID | Description | Status | Risk |
|----|-------------|--------|------|
| LM-01 | Add Pydantic dependency | Required | Low |
| LM-02 | DTO coexistence strategy | Pending decision | Medium |
| LM-03 | Section width enhancement | Required for full FRD | Medium |

### Codebase Integration Points

| Existing File | Modification Type | Purpose |
|--------------|-------------------|---------|
| `pyproject.toml` | Add dependency | pydantic>=2.0, package-data |
| `domain/value_objects.py` | Reuse | MaterialType enum |
| `application/dtos.py` | Preserve | WallInput, LayoutParametersInput |
| `application/commands.py` | Preserve | GenerateLayoutCommand |
| `cli/main.py` | Modify | Add --config, import commands |
| `domain/services.py` | Extend | LayoutCalculator section support |

---

*FRD Refinement completed: 2025-12-27*
*Status: Codebase Aligned and Ready for Task Breakdown*

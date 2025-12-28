"""Configuration file loader with comprehensive error handling.

This module provides functionality to load and parse JSON configuration files
for cabinet specifications. It handles file system errors, JSON parsing errors,
and Pydantic validation errors with clear, actionable error messages.
"""

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from cabinets.application.config.schema import CabinetConfiguration


class ConfigError(Exception):
    """Exception raised for configuration-related errors.

    This exception provides detailed error information including:
    - File path (if applicable)
    - Error type (file_not_found, json_parse, validation)
    - Human-readable error message
    - Additional details for debugging

    Attributes:
        message: The primary error message
        error_type: Category of error (file_not_found, json_parse, validation)
        path: Path to the configuration file (if applicable)
        details: Additional error details (line/column for JSON, validation errors, etc.)
    """

    def __init__(
        self,
        message: str,
        error_type: str = "unknown",
        path: Path | None = None,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        self.message = message
        self.error_type = error_type
        self.path = path
        self.details = details or []
        super().__init__(message)

    def __str__(self) -> str:
        """Format error message for display."""
        return self.message


def _format_json_path(loc: tuple[str | int, ...]) -> str:
    """Format a Pydantic location tuple as a JSON path string.

    Args:
        loc: Tuple of path segments (strings for keys, ints for array indices)

    Returns:
        Formatted JSON path like "cabinet.sections[0].width"

    Examples:
        >>> _format_json_path(("cabinet", "width"))
        'cabinet.width'
        >>> _format_json_path(("cabinet", "sections", 0, "shelves"))
        'cabinet.sections[0].shelves'
    """
    parts: list[str] = []
    for segment in loc:
        if isinstance(segment, int):
            # Array index - append to last part with brackets
            if parts:
                parts[-1] = f"{parts[-1]}[{segment}]"
            else:
                parts.append(f"[{segment}]")
        else:
            parts.append(str(segment))
    return ".".join(parts)


def _extract_validation_errors(
    error: PydanticValidationError,
) -> list[dict[str, Any]]:
    """Extract and format validation errors from a Pydantic ValidationError.

    Args:
        error: The Pydantic ValidationError to process

    Returns:
        List of error dictionaries with path, message, value, and error_type
    """
    details: list[dict[str, Any]] = []
    for err in error.errors():
        path = _format_json_path(err["loc"])
        details.append(
            {
                "path": path,
                "message": err["msg"],
                "value": err.get("input"),
                "error_type": err["type"],
            }
        )
    return details


def _format_validation_error_message(details: list[dict[str, Any]]) -> str:
    """Format validation error details into a human-readable message.

    Args:
        details: List of error detail dictionaries

    Returns:
        Formatted multi-line error message
    """
    lines = ["Configuration validation failed:"]
    for detail in details:
        path = detail["path"]
        message = detail["message"]
        value = detail.get("value")
        if value is not None:
            lines.append(f"  - {path}: {message} (got: {value!r})")
        else:
            lines.append(f"  - {path}: {message}")
    return "\n".join(lines)


def load_config(path: Path) -> CabinetConfiguration:
    """Load and validate a cabinet configuration from a JSON file.

    This function handles three types of errors:
    1. File not found - The specified file does not exist
    2. JSON parse error - The file contains invalid JSON
    3. Validation error - The JSON is valid but doesn't match the schema

    Args:
        path: Path to the JSON configuration file

    Returns:
        A validated CabinetConfiguration instance

    Raises:
        ConfigError: If the file cannot be loaded or validated.
            The error_type attribute indicates the specific error category:
            - "file_not_found": File does not exist
            - "json_parse": Invalid JSON syntax
            - "validation": Schema validation failed

    Example:
        >>> from pathlib import Path
        >>> try:
        ...     config = load_config(Path("my-cabinet.json"))
        ... except ConfigError as e:
        ...     print(f"Error: {e}")
        ...     for detail in e.details:
        ...         print(f"  {detail['path']}: {detail['message']}")
    """
    # Check if file exists
    if not path.exists():
        raise ConfigError(
            message=f"Config file not found: {path}",
            error_type="file_not_found",
            path=path,
        )

    # Read and parse JSON
    try:
        content = path.read_text(encoding="utf-8")
    except PermissionError:
        raise ConfigError(
            message=f"Permission denied reading config file: {path}",
            error_type="permission_denied",
            path=path,
        )
    except OSError as e:
        raise ConfigError(
            message=f"Error reading config file: {path}: {e}",
            error_type="file_read_error",
            path=path,
        )

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        # Extract line and column information
        raise ConfigError(
            message=f"Invalid JSON in config file: {path} (line {e.lineno}, column {e.colno}): {e.msg}",
            error_type="json_parse",
            path=path,
            details=[
                {
                    "line": e.lineno,
                    "column": e.colno,
                    "message": e.msg,
                }
            ],
        )

    # Validate against schema
    try:
        return CabinetConfiguration.model_validate(data)
    except PydanticValidationError as e:
        details = _extract_validation_errors(e)
        raise ConfigError(
            message=_format_validation_error_message(details),
            error_type="validation",
            path=path,
            details=details,
        )


def load_config_from_dict(data: dict[str, Any]) -> CabinetConfiguration:
    """Load and validate a cabinet configuration from a dictionary.

    This is useful for loading configuration from sources other than files,
    such as API requests or programmatic configuration.

    Args:
        data: Dictionary containing configuration data

    Returns:
        A validated CabinetConfiguration instance

    Raises:
        ConfigError: If the data fails validation.
    """
    try:
        return CabinetConfiguration.model_validate(data)
    except PydanticValidationError as e:
        details = _extract_validation_errors(e)
        raise ConfigError(
            message=_format_validation_error_message(details),
            error_type="validation",
            details=details,
        )

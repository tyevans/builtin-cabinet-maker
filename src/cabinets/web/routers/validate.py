"""Configuration validation endpoints."""

from fastapi import APIRouter, HTTPException

from cabinets.application.config import load_config_from_dict, validate_config
from cabinets.web.schemas.requests import ConfigValidateRequest
from cabinets.web.schemas.responses import ValidationResultSchema

router = APIRouter(prefix="/validate", tags=["validate"])


@router.post("", response_model=ValidationResultSchema)
async def validate_configuration(
    request: ConfigValidateRequest,
) -> ValidationResultSchema:
    """Validate a cabinet configuration without generating.

    Args:
        request: Request containing configuration to validate.

    Returns:
        Validation result with errors and warnings.

    Raises:
        HTTPException: If configuration cannot be parsed.
    """
    try:
        # Load config from dict
        config = load_config_from_dict(request.config)

        # Validate config
        result = validate_config(config)

        return ValidationResultSchema(
            is_valid=result.is_valid,
            errors=[{"message": e.message, "path": e.path} for e in result.errors],
            warnings=[{"message": w.message, "path": w.path} for w in result.warnings],
        )

    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail={"error": str(e), "error_type": "parse_error"},
        ) from e

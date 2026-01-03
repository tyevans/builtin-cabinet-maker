"""FastAPI REST API for cabinet generation.

This module provides a REST API for generating cabinet layouts, validating
configurations, and exporting to various formats.

Usage:
    uvicorn cabinets.web:app --reload
"""

from cabinets.web.app import app, create_app

__all__ = ["app", "create_app"]

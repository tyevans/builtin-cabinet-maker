"""Template manager for bundled cabinet configuration templates.

This module provides the TemplateManager class for accessing and copying
bundled template configurations.
"""

from importlib import resources
from pathlib import Path


class TemplateNotFoundError(Exception):
    """Raised when a requested template does not exist."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Template not found: {name}")


# Template metadata: name -> description
TEMPLATE_METADATA: dict[str, str] = {
    "simple-shelf": "Basic wall shelf unit",
    "bookcase": "Standard bookcase with adjustable shelves",
    "cabinet-doors": "Base cabinet with door openings",
}


class TemplateManager:
    """Manager for bundled cabinet configuration templates.

    Provides methods to list available templates, retrieve template content,
    and initialize new configuration files from templates.

    Example:
        manager = TemplateManager()
        templates = manager.list_templates()
        for name, description in templates:
            print(f"{name}: {description}")

        manager.init_template("bookcase", Path("my-bookcase.json"))
    """

    def __init__(self) -> None:
        """Initialize the TemplateManager."""
        self._data_package = "cabinets.application.templates.data"

    def list_templates(self) -> list[tuple[str, str]]:
        """List all available templates with their descriptions.

        Returns:
            List of (name, description) tuples for each available template.
        """
        return [(name, desc) for name, desc in TEMPLATE_METADATA.items()]

    def get_template(self, name: str) -> str:
        """Get the JSON content of a template.

        Args:
            name: The template name (without .json extension).

        Returns:
            The template JSON content as a string.

        Raises:
            TemplateNotFoundError: If the template does not exist.
        """
        if name not in TEMPLATE_METADATA:
            raise TemplateNotFoundError(name)

        filename = f"{name}.json"
        try:
            # Use importlib.resources to access package data
            # resources.files() returns a Traversable
            data_files = resources.files(self._data_package)
            template_file = data_files.joinpath(filename)
            return template_file.read_text(encoding="utf-8")
        except FileNotFoundError as e:
            raise TemplateNotFoundError(name) from e

    def init_template(self, name: str, output_path: Path) -> None:
        """Copy a template to the specified output path.

        Args:
            name: The template name (without .json extension).
            output_path: The destination path for the template copy.

        Raises:
            TemplateNotFoundError: If the template does not exist.
            FileExistsError: If the output file already exists.
        """
        # Get template content (validates template exists)
        content = self.get_template(name)

        # Write to output path
        output_path.write_text(content, encoding="utf-8")

    def template_exists(self, name: str) -> bool:
        """Check if a template with the given name exists.

        Args:
            name: The template name to check.

        Returns:
            True if the template exists, False otherwise.
        """
        return name in TEMPLATE_METADATA

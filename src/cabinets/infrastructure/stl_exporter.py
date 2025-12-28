"""STL export functionality using numpy-stl."""

from pathlib import Path

import numpy as np
from stl import mesh

from cabinets.domain import BoundingBox3D, Cabinet, Panel3DMapper


class StlMeshBuilder:
    """Builds STL meshes from 3D bounding boxes.

    Single Responsibility: Handles low-level mesh creation from geometry primitives.
    """

    def build_box_mesh(self, box: BoundingBox3D) -> mesh.Mesh:
        """Create an STL mesh for a single bounding box.

        Args:
            box: The 3D bounding box to convert to a mesh.

        Returns:
            A numpy-stl Mesh object representing the box.
        """
        vertices = np.array(box.get_vertices())
        triangles = box.get_triangles()

        # Create mesh with 12 triangles (2 per face, 6 faces)
        box_mesh = mesh.Mesh(np.zeros(12, dtype=mesh.Mesh.dtype))

        for i, (v0, v1, v2) in enumerate(triangles):
            box_mesh.vectors[i] = [vertices[v0], vertices[v1], vertices[v2]]

        return box_mesh

    def combine_meshes(self, meshes: list[mesh.Mesh]) -> mesh.Mesh:
        """Combine multiple meshes into a single mesh.

        Args:
            meshes: List of meshes to combine.

        Returns:
            A single combined mesh containing all faces.
        """
        if not meshes:
            return mesh.Mesh(np.zeros(0, dtype=mesh.Mesh.dtype))

        total_faces = sum(m.vectors.shape[0] for m in meshes)
        combined = mesh.Mesh(np.zeros(total_faces, dtype=mesh.Mesh.dtype))

        offset = 0
        for m in meshes:
            num_faces = m.vectors.shape[0]
            combined.vectors[offset : offset + num_faces] = m.vectors
            offset += num_faces

        return combined


class StlExporter:
    """Exports cabinet layouts to STL format.

    Single Responsibility: Orchestrates the conversion of Cabinet domain objects
    to STL files using the Panel3DMapper and StlMeshBuilder.

    Dependency Inversion: Depends on domain abstractions (Cabinet, BoundingBox3D),
    not on numpy-stl implementation details exposed to the domain.
    """

    def __init__(self, mesh_builder: StlMeshBuilder | None = None) -> None:
        """Initialize the exporter.

        Args:
            mesh_builder: Optional mesh builder instance for dependency injection.
        """
        self.mesh_builder = mesh_builder or StlMeshBuilder()

    def export(self, cabinet: Cabinet) -> mesh.Mesh:
        """Export a cabinet to an STL mesh object.

        Args:
            cabinet: The cabinet to export.

        Returns:
            A numpy-stl Mesh object representing the entire cabinet.
        """
        mapper = Panel3DMapper(cabinet)
        boxes = mapper.map_all_panels()

        meshes = [self.mesh_builder.build_box_mesh(box) for box in boxes]
        return self.mesh_builder.combine_meshes(meshes)

    def export_to_file(self, cabinet: Cabinet, filepath: Path | str) -> None:
        """Export a cabinet to an STL file.

        Args:
            cabinet: The cabinet to export.
            filepath: Path where the STL file will be saved.
        """
        combined_mesh = self.export(cabinet)
        combined_mesh.save(str(filepath))

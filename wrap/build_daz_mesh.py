import bpy
from typing import cast
from ..skinwrap.mesh_uv_fix import fix_uv_tangent_winding
from .wrap_types import DAZBuildResult, DAZMeshData, DAZTopology, FlippedTriangles
from .DeriveMeshes import (
    build_base_mesh,
    build_uv_mesh,
    flatten_material_triangles,
    poly_list_to_triangle_indexes,
    recalculate_normals,
    update_duplicate_uv_normals,
    recalculate_tangents_fast,
)
def validate_mesh_mapping(daz:DAZMeshData):
    base_vertices = daz.base_vertices
    uv_vertices = daz.uv_vertices
    base_triangles = daz.base_triangles
    uv_triangles = daz.uv_triangles
    vertex_maps = daz.vertex_maps

    print("=== DAZMesh validation ===")
    print("base vertex count:", len(base_vertices))
    print("UV vertex count:", len(uv_vertices))
    print("duplicate UV vertex count:", len(vertex_maps))
    print("base triangle index count:", len(base_triangles))
    print("UV triangle index count:", len(uv_triangles))

    if len(base_triangles) != len(uv_triangles):
        print("ERROR: base_triangles and uv_triangles have different lengths")

    for i, index in enumerate(base_triangles):
        if not 0 <= index < len(base_vertices):
            print(f"ERROR: base_triangles[{i}] out of range: {index}")

    for i, index in enumerate(uv_triangles):
        if not 0 <= index < len(uv_vertices):
            print(f"ERROR: uv_triangles[{i}] out of range: {index}")

    for i, vm in enumerate(vertex_maps):
        if not 0 <= vm.fromvert < len(base_vertices):
            print(f"ERROR: vertex_maps[{i}].fromvert out of range")
        if not 0 <= vm.tovert < len(uv_vertices):
            print(f"ERROR: vertex_maps[{i}].tovert out of range")

        if (
            0 <= vm.fromvert < len(base_vertices)
            and 0 <= vm.tovert < len(uv_vertices)
        ):
            delta = (
                base_vertices[vm.fromvert]
                - uv_vertices[vm.tovert]
            ).length

            if delta > 1e-6:
                print(
                    f"ERROR: duplicated vertex position mismatch "
                    f"at vertex_map[{i}]: delta={delta}"
                )

    print("=== validation completed ===")

def build_daz_mesh(
    obj: bpy.types.Object,
    is_body:bool,
    split_material = False
) -> DAZBuildResult:
    ##########################################################
    # Get Blender Mesh
    ##########################################################
    mesh = cast(bpy.types.Mesh, obj.data)
    uv_layer = mesh.uv_layers.active
    if uv_layer is None:
        raise RuntimeError("Mesh has no UV layer")
    ##########################################################
    # Matrix
    ##########################################################
    daz = DAZMeshData()
    daz.matrix_world = (
        obj.matrix_world.copy()
    )
    ##########################################################
    # Build BaseMesh
    ##########################################################
    base = build_base_mesh(mesh)
    daz.base_vertices = base.base_vertices
    daz.base_poly_list = base.base_poly_list
    topology=DAZTopology(
        object=obj,
        data=mesh.copy(),
        name=obj.name
    )
    topology.base_vertices=base.base_vertices
    topology.base_poly_list=base.base_poly_list
    ##########################################################
    # Build UVMesh
    ##########################################################
    (
        uv_vertices,
        orig_uv,
        vertex_maps,
        uv_poly_list,
    ) = build_uv_mesh(
        mesh,
        uv_layer
    )
    daz.uv_vertices = uv_vertices
    daz.orig_uv = orig_uv
    daz.vertex_maps = vertex_maps
    daz.uv_poly_list = uv_poly_list
    ##########################################################
    # Triangle Index
    ##########################################################
    temp_base = poly_list_to_triangle_indexes(daz.base_poly_list, split_material)
    temp_uv = poly_list_to_triangle_indexes(daz.uv_poly_list, split_material)
    daz.base_triangles = (flatten_material_triangles(cast(list[list[int]], temp_base)))
    daz.uv_triangles=(flatten_material_triangles(cast(list[list[int]], temp_uv)))
    ##########################################################
    # Base Normals
    ##########################################################
    (daz.base_normals,daz.base_surface_normals) = recalculate_normals(triangles=daz.base_triangles,vertices=daz.base_vertices, is_body=is_body)
    ##########################################################
    # Morphed Base
    ##########################################################
    daz.morphed_base_vertices = [
        v.copy()
        for v in daz.base_vertices
    ]
    daz.morphed_base_normals = [
        n.copy()
        for n in daz.base_normals
    ]
    daz.morphed_base_surface_normals = [
        n.copy()
        for n in daz.base_surface_normals
    ]
    ##########################################################
    # UV Normals
    ##########################################################
    daz.morphed_uv_normals = (
        update_duplicate_uv_normals(
            base_normals=daz.morphed_base_normals,
            vertex_maps=daz.vertex_maps,
            uv_vertex_count=len(
                daz.uv_vertices
            )
        )
    )
    daz.uv_normals = [
        n.copy()
        for n in daz.morphed_uv_normals
    ]
    ##########################################################
    # UV Tangents
    ##########################################################
    daz.uv_tangents = (
        recalculate_tangents_fast(
            triangles=daz.uv_triangles,
            vertices=daz.uv_vertices,
            normals=daz.uv_normals,
            uv=daz.orig_uv
        )
    )

    daz.morphed_uv_tangents = [
        t.copy()
        for t in daz.uv_tangents
    ]
    ##########################################################
    # Morphed UV
    ##########################################################
    daz.morphed_uv_vertices = [
        v.copy()
        for v in daz.uv_vertices
    ]
    daz.visible_morphed_uv_vertices = [
        v.copy()
        for v in daz.uv_vertices
    ]
    daz.smoothed_morphed_uv_vertices = [
        v.copy()
        for v in daz.morphed_uv_vertices
    ]
    ##########################################################
    # Dirty Flags
    ##########################################################
    daz.morphed_base_dirty_vertices = [
        False
        for _ in daz.morphed_base_vertices
    ]
    daz.morphed_uv_dirty_vertices = [
        False
        for _ in daz.morphed_uv_vertices
    ]
    return DAZBuildResult(
        mesh=daz,
        topology=topology
    )
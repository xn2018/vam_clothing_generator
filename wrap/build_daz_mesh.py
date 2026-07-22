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
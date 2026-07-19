from typing import cast
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

from ..skinwrap.runtime_mesh_cache import get_genesis_daz_mesh
from .wrap_types import (
    SkinWrapCache,
    TriangleInfo,
)
from mathutils.bvhtree import BVHTree
def build_mesh_cache_from_object(
    genesis_obj:bpy.types.Object
)->SkinWrapCache:
    ##########################################################
    # Build DAZ Mesh
    ##########################################################
    daz_mesh = get_genesis_daz_mesh(
        genesis_obj
    )
    mesh_data = daz_mesh.mesh
    ##########################################################
    # Build Body Triangle Cache
    ##########################################################
    triangles:list[TriangleInfo] = []
    base_vertices = mesh_data.base_vertices
    base_triangles = mesh_data.base_triangles
    #
    # BVH polygons
    #
    bvh_polygons:list[list[int]] = []
    bvh_to_triangle:list[int]=[]
    for i in range(
        0,
        len(base_triangles),
        3
    ):
        a = base_triangles[i]
        b = base_triangles[i+1]
        c = base_triangles[i+2]
        p1 = base_vertices[a]
        p2 = base_vertices[b]
        p3 = base_vertices[c]
        tri_index=i//3
        #
        # surface normal
        #
        normal = (mesh_data.base_surface_normals[tri_index].copy())

        if normal.length_squared < 1e-12:
            continue
        bvh_to_triangle.append(len(triangles))
        # normal.normalize()
        center = (p1+p2+p3) / 3.0
        triangles.append(
            TriangleInfo(
                triangle_id=len(triangles),
                original_triangle_id=tri_index,
                vertex1=a,
                vertex2=b,
                vertex3=c,
                v1=p1,
                v2=p2,
                v3=p3,
                center=center,
                normal=normal
            )
        )
        #
        # BVHTree polygon
        #
        bvh_polygons.append(
            [
                a,
                b,
                c
            ]
        )
    bvh_vertices = [
    (
        float(v.x),
        float(v.y),
        float(v.z)
    )
    for v in base_vertices]
    ##########################################################
    # Build BVHTree
    ##########################################################
    bvh_tree = BVHTree.FromPolygons(
        bvh_vertices,
        bvh_polygons,
        all_triangles=True
    )
    ##########################################################
    # anchor by vertex group
    ##########################################################
    anchor_vertices:set[int]=set()
    vg = genesis_obj.vertex_groups.get("anchor")
    if vg is not None:
        group_index = vg.index
        mesh = cast(
            bpy.types.Mesh,
            genesis_obj.data
        )
        for v in mesh.vertices:
            for g in v.groups:
                if g.group == group_index:
                    if g.weight > 0.001:
                        anchor_vertices.add(
                            v.index
                        )
                    break
    ##########################################################
    # Cache
    ##########################################################
    cache = SkinWrapCache()
    cache.object_name = genesis_obj.name
    cache.body_mesh = mesh_data
    cache.body_triangles = triangles
    ##########################################################
    # New Cache Items
    ##########################################################
    cache.body_bvh = bvh_tree
    cache.bvh_to_triangle=bvh_to_triangle
    cache.anchor_vertices = anchor_vertices
    cache.vertex_count = len(
        mesh_data.base_vertices
    )
    cache.initialized=True
    ##########################################################
    # Debug
    ##########################################################
    print()
    print("==============================")
    print("Genesis SkinWrap Cache")
    print("==============================")
    print("Base Vertices:",len(mesh_data.base_vertices))
    print("Base Triangles:",len(triangles))
    print("BVH:",bvh_tree)
    print("Anchor Vertices:",len(anchor_vertices))
    print()
    return cache
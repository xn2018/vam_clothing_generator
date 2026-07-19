import os
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from .build_mesh_cache_from_object import build_mesh_cache_from_object
from .wrap_types import DAZMeshData, PerSkinWrapCalculationResult, SkinWrapCache, SkinWrapVertex, WrapInputVertex
from typing import Optional
def empty_result():
    return SkinWrapVertex(
        closestTriangle=-1,
        Vertex1=-1,
        Vertex2=-1,
        Vertex3=-1,
        surfaceNormalProjection=0.0,
        surfaceTangent1Projection=0.0,
        surfaceTangent2Projection=0.0,
        surfaceNormalWrapNormalDot=1.0,
        surfaceTangent1WrapNormalDot=0.0,
        surfaceTangent2WrapNormalDot=0.0,
    )
# ============================================================
# Global Cache
# ============================================================
_CACHE: Optional[SkinWrapCache] = None
# ============================================================
# Cache State
# ============================================================
def cache_ready() -> bool:
    return _CACHE is not None and _CACHE.initialized
# ============================================================
# Invalidate Cache
# ============================================================
def invalidate_cache():
    global _CACHE
    _CACHE = SkinWrapCache()
    print("[SkinWrap] Cache cleared.")
# ============================================================
# Cache Statistics
# ============================================================
def print_cache_info():
    if _CACHE is not None:
        print()
        print("========================================")
        print("Genesis Mesh Cache")
        print("========================================")
        print("Initialized :", _CACHE.initialized)
        print("Object      :", _CACHE.object_name)
        print("Vertices    :", _CACHE.vertex_count)
        print("Triangles   :", _CACHE.triangle_count)
        print("AnchorVert  :", len(_CACHE.anchor_vertices))
        print("BVH         :", _CACHE.bvh is not None)
        print()
# ============================================================
# Get Cache
# ============================================================
def get_cache() -> SkinWrapCache:
    if _CACHE is None:
        raise RuntimeError(
            "SkinWrap cache has not been initialized."
        )
    return _CACHE
# ============================================================
# Clear Cache
# ============================================================
def clear_cache():
    global _CACHE
    _CACHE = None
    print(
        "[SkinWrap] Cache cleared."
    )
# ============================================================
# Validate Cache
# ============================================================
def validate_cache(
    obj,
    cache:SkinWrapCache
)->bool:
    if cache is None:
        return False
    if cache.object_name != obj.name:
        return False
    if cache.mesh_pointer != obj.data.as_pointer():
        return False
    if cache.vertex_count != len(obj.data.vertices):
        return False
    return True
# ============================================================
# Ensure Cache
# ============================================================
def ensure_cache(
    genesis_obj: bpy.types.Object
)->SkinWrapCache|None:
    global _CACHE
    #
    # First Build
    #
    if _CACHE is None:
        _CACHE = build_mesh_cache_from_object(
            genesis_obj
        )
        return _CACHE
    #
    # Not Ready
    #
    if not _CACHE.initialized:
        _CACHE = build_mesh_cache_from_object(
            genesis_obj
        )
        return _CACHE
    #
    # Object Changed
    #
    if _CACHE.object_name != genesis_obj.name:
        _CACHE = build_mesh_cache_from_object(
            genesis_obj
        )
        return _CACHE
    #
    # Vertex Count Changed
    #
    if (
        _CACHE.body_mesh is None
        or
        _CACHE.vertex_count != len(
            _CACHE.body_mesh.base_vertices
        )
    ):
        _CACHE = build_mesh_cache_from_object(
            genesis_obj
        )
        return _CACHE
    #
    # Cache valid
    #
    return _CACHE
# ============================================================
# build_anchor_triangle_cache
# ============================================================
def build_anchor_triangle_cache(
    cache: SkinWrapCache,
    min_anchor_vertices=3
):
    ##########################################################
    # Collect anchor triangles
    ##########################################################
    anchor = set(
        cache.anchor_vertices
    )
    anchor_triangles = []
    for tri in cache.body_triangles:
        count = 0
        if tri.vertex1 in anchor:
            count += 1
        if tri.vertex2 in anchor:
            count += 1
        if tri.vertex3 in anchor:
            count += 1
        #
        # Official Logic: 
        #
        # triangle must be entirely within the anchor region
        #
        if count >= min_anchor_vertices:
            anchor_triangles.append(
                tri
            )
    cache.anchor_triangles = anchor_triangles
    ##########################################################
    # Build BVH
    ##########################################################
    vertices = []
    polygons = []
    vertex_map = {}
    for tri in anchor_triangles:
        ids = []
        for index, co in (
            (
                tri.vertex1,
                tri.v1
            ),
            (
                tri.vertex2,
                tri.v2
            ),
            (
                tri.vertex3,
                tri.v3
            ),
        ):
            if index not in vertex_map:
                vertex_map[index] = len(vertices)
                vertices.append(
                    (
                        float(co.x),
                        float(co.y),
                        float(co.z)
                    )
                )
            ids.append(
                vertex_map[index]
            )
        polygons.append(ids)
    if len(polygons) > 0:
        anchor_bvh = BVHTree.FromPolygons(
            vertices,
            polygons,
            all_triangles=True
        )
    else:
        anchor_bvh = None
    cache.anchor_bvh = anchor_bvh
    ##########################################################
    # Debug
    ##########################################################
    print(
        "[SkinWrap] Anchor triangles:",
        len(anchor_triangles)
    )
    print(
        "[SkinWrap] Anchor BVH:",
        anchor_bvh
    )
# ============================================================
# Reorder Triangle
# ============================================================
def reorder_triangle(
    tri,
    pos
):
    verts=[
        (tri.vertex1,tri.v1),
        (tri.vertex2,tri.v2),
        (tri.vertex3,tri.v3),
    ]
    distances=[
        (v[1]-pos).length_squared
        for v in verts
    ]
    first=min(
        range(3),
        key=lambda i:distances[i]
    )
    order=[
        first,
        (first+1)%3,
        (first+2)%3
    ]
    ids=[
        verts[i][0]
        for i in order
    ]
    ps=[
        verts[i][1]
        for i in order
    ]
    return (
        ids[0],
        ids[1],
        ids[2],
        ps[0],
        ps[1],
        ps[2],
    )
# ============================================================
# SkinWrap Matrix
# ============================================================
def calculate_skinwrap_matrix(
    genesis_obj: bpy.types.Object,
    clothing_mesh: DAZMeshData,
    wrap_vertices: list[WrapInputVertex],
    anchor_only=False,
    wrap_check_normals=False,
    max_wrap_distance=1.0
):
    cache=ensure_cache(
        genesis_obj
    )
    if cache is None:
        raise RuntimeError(
            "SkinWrap cache missing"
        )
    local_matrix = (genesis_obj.matrix_world.inverted()@clothing_mesh.matrix_world)
    normal_matrix = (local_matrix.to_3x3())
    return PerSkinWrapCalculationResult(
        wrap_vertices=wrap_vertices,
        clothing_mesh=clothing_mesh,
        local_matrix=local_matrix,
        normal_matrix=normal_matrix,
        anchor_only=anchor_only,
        wrap_check_normals=wrap_check_normals,
        max_wrap_distance=max_wrap_distance
    )
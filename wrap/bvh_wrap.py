import os
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from .build_mesh_cache_from_object import build_mesh_cache_from_object
from .mesh_inspect import geometry_signature, get_anchor_signature
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
        print("Body source :", _CACHE.body_source)
        print("Base / UV   :", _CACHE.body_base_count, "/", _CACHE.body_uv_count)
        print("AnchorVert  :", len(_CACHE.anchor_vertices))
        print("Body BVH    :", _CACHE.body_bvh is not None)
        print("Anchor BVH  :", _CACHE.anchor_bvh is not None)
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
def ensure_cache(genesis_obj):
    global _CACHE
    sig = geometry_signature(genesis_obj)
    anchor_sig = get_anchor_signature(genesis_obj)

    if (
        _CACHE is None
        or not _CACHE.initialized
        or _CACHE.object_name != genesis_obj.name
        or _CACHE.mesh_pointer != genesis_obj.data.as_pointer()
        or _CACHE.geometry_signature != sig
        or _CACHE.anchor_signature != anchor_sig
        or _CACHE.body_mesh is None
        or _CACHE.body_bvh is None
        or _CACHE.body_base_count <= 0
        or _CACHE.vertex_count != len(genesis_obj.data.vertices)
    ):
        _CACHE = build_mesh_cache_from_object(genesis_obj)
    return _CACHE
# ============================================================
# build_anchor_triangle_cache
# ============================================================
def build_anchor_triangle_cache(cache: SkinWrapCache, min_anchor_vertices=3):
    anchor = set(cache.anchor_vertices)
    ids = [t.triangle_id for t in cache.body_triangles
           if sum(1 for v in (t.vertex1, t.vertex2, t.vertex3) if v in anchor)
              >= min_anchor_vertices]

    cache.anchor_triangles = [cache.body_triangles[i] for i in ids]
    cache.anchor_bvh_to_triangle = list(range(len(cache.anchor_triangles)))

    if not cache.anchor_triangles:
        cache.anchor_bvh = None
        return

    vertex_map, vertices, polygons = {}, [], []
    for tri in cache.anchor_triangles:
        local = []
        for index, co in ((tri.vertex1, tri.v1), (tri.vertex2, tri.v2), (tri.vertex3, tri.v3)):
            if index not in vertex_map:
                vertex_map[index] = len(vertices)
                vertices.append((float(co.x), float(co.y), float(co.z)))
            local.append(vertex_map[index])
        polygons.append(local)

    cache.anchor_bvh = BVHTree.FromPolygons(vertices, polygons, all_triangles=True)
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
    clothing_obj: DAZMeshData,
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
    local_matrix = (genesis_obj.matrix_world.inverted()@clothing_obj.matrix_world)
    normal_matrix = (local_matrix.to_3x3())
    return PerSkinWrapCalculationResult(
        wrap_vertices=wrap_vertices,
        clothing_obj=clothing_obj,
        local_matrix=local_matrix,
        normal_matrix=normal_matrix,
        anchor_only=anchor_only,
        wrap_check_normals=wrap_check_normals,
        max_wrap_distance=max_wrap_distance
    )
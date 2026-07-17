import os
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from .build_mesh_cache_from_object import build_mesh_cache_from_object
from .wrap_types import SkinWrapCache, SkinWrapVertex, TriangleInfo, DAZMeshData

from .DeriveMeshes import recover_vertex_normal
from .build_wrap_vertices import WrapInputVertex
from typing import Optional
from typing import cast
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
# Ensure Cache
# ============================================================
def ensure_cache(
    genesis_obj: bpy.types.Object
) -> SkinWrapCache|None:
    global _CACHE
    #
    # First Build
    #
    if _CACHE is None:
        _CACHE = build_mesh_cache_from_object(genesis_obj)
        return _CACHE
    #
    # Not Ready
    #
    if not _CACHE.initialized:
        _CACHE = build_mesh_cache_from_object(genesis_obj)
        return _CACHE
    #
    # Object Changed
    #
    if _CACHE.object_name != genesis_obj.name:
        _CACHE = build_mesh_cache_from_object(genesis_obj)
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
        _CACHE = build_mesh_cache_from_object(genesis_obj)
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
# find_nearest_triangle
# ============================================================
def find_nearest_triangle(
    pos: Vector,
    wrap_normal: Vector | None,
    *,
    anchor_only=False,
    check_normals=False,
    normal_dot_limit=0,
)->TriangleInfo|None:
    cache = get_cache()
    if cache is None:
        raise RuntimeError(
            "find_nearest_triangle cache is None"
        )
    ##########################################################
    # Select BVH
    ##########################################################
    if anchor_only:
        if (
            cache.anchor_bvh is None
            or
            not cache.anchor_triangles
        ):
            build_anchor_triangle_cache(
                cache,
                min_anchor_vertices=3
            )
        tree = cache.anchor_bvh
        triangles = cache.anchor_triangles
    else:
        tree = cache.body_bvh
        triangles = cache.body_triangles
    if tree is None:
        raise RuntimeError(
            "BVH is None"
        )
    if not triangles:
        return None
    ##########################################################
    # BVH Nearest
    ##########################################################
    hit = tree.find_nearest(
        (
            pos.x,
            pos.y,
            pos.z
        )
    )
    if hit is None:
        return None
    (location,normal,polygon_index,distance) = hit
    if polygon_index is None:
        return None
    if polygon_index < 0:
        return None
    ##########################################################
    # Get TriangleInfo
    ##########################################################
    if polygon_index >= len(triangles):
        return None
    tri = triangles[
        polygon_index
    ]
    ##########################################################
    # Normal Check
    ##########################################################
    if (
        wrap_normal is not None
        and
        check_normals
    ):
        dot = (
            wrap_normal.dot(
                tri.normal
            )
        )

        if dot < normal_dot_limit:
            print("BACKFACE",polygon_index,dot)
            return None
    return tri
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
    genesis_obj:bpy.types.Object,
    clothing_mesh:DAZMeshData,
    wrap_vertices:list[WrapInputVertex],
    anchor_only:bool=False,
    wrap_check_normals:bool=False,
    max_wrap_distance:float=1.0
)->list[SkinWrapVertex]:
    empty_count={
        "tri":0,
        "distance":0,
        "tangent1":0,
        "normal":0,
        "tangent2":0,
        "wrap_normal":0
    }
    ##########################################################
    # Genesis Cache
    ##########################################################
    cache=ensure_cache(
        genesis_obj
    )
    if cache is None:
        raise RuntimeError(
            "SkinWrap cache is None"
        )
    ##########################################################
    # Validate clothing UV mesh
    ##########################################################
    if (
        len(wrap_vertices)
        !=
        len(clothing_mesh.uv_vertices)
    ):
        raise RuntimeError(
            "UV vertex count mismatch"
        )
    if (
        len(wrap_vertices)
        !=
        len(clothing_mesh.uv_normals)
    ):
        raise RuntimeError(
            "UV normal count mismatch"
        )
    ##########################################################
    # Matrix
    ##########################################################
    g_inv = (
        genesis_obj.matrix_world.inverted()
    )
    local_matrix = (
        g_inv
        @
        clothing_mesh.matrix_world
    )
    normal_matrix = (
        local_matrix
        .to_3x3()
    )
    ##########################################################
    # Result
    ##########################################################
    results=[]
    print()
    print("==============================")
    print("Calculate SkinWrap Matrix BVH")
    print("==============================")
    print("Wrap vertices:",len(wrap_vertices))
    ##########################################################
    # Loop
    ##########################################################
    for wrap_vertex in wrap_vertices:
        ######################################################
        # Position
        ######################################################
        local_pos = (
            local_matrix
            @
            wrap_vertex.co
        )
        ######################################################
        # Normal
        ######################################################
        wrap_normal = (normal_matrix@wrap_vertex.normal)

        if wrap_normal.length_squared < 1e-12:
            empty_count["wrap_normal"]+=1
            recovered = recover_vertex_normal(
                wrap_vertex.index,
                clothing_mesh.uv_triangles,
                clothing_mesh.base_surface_normals
            )

            if recovered:
                wrap_normal=recovered
            else:
                raise RuntimeError(
                    f"Cannot recover normal {wrap_vertex.index}"
                )
            
        wrap_normal.normalize()
        ######################################################
        # BVH nearest triangle
        ######################################################
        tri = find_nearest_triangle(
            local_pos,
            wrap_normal,
            anchor_only=anchor_only,
            check_normals=wrap_check_normals
        )

        if tri is None:
            empty_count["tri"] += 1
            results.append(empty_result())
            continue
        ######################################################
        # Exact triangle distance
        ######################################################
        #
        # BVH has ensured the closest surface
        #
        # Use point-center distance
        #
        distance = (local_pos -tri.center).length

        if distance > max_wrap_distance:
            empty_count["distance"] += 1
            results.append(empty_result())
            continue
        ######################################################
        # DAZ reorder
        ######################################################
        v1=tri.vertex1
        v2=tri.vertex2
        v3=tri.vertex3

        p1=tri.v1
        p2=tri.v2
        p3=tri.v3

        center = (
            p1+p2+p3
        ) / 3.0

        tangent1 = (center-p1)

        if tangent1.length_squared < 1e-12:
            empty_count["tangent1"]+=1
            results.append(empty_result())
            continue

        normal = tri.normal.copy()

        if normal.length_squared < 1e-12:
            empty_count["normal"]+=1
            results.append(empty_result())
            continue

        tangent2 = cast(Vector,tangent1.cross(normal))

        if tangent2.length_squared < 1e-12:
            empty_count["tangent2"]+=1
            results.append(empty_result())
            continue

        ######################################################
        # Projection
        ######################################################
        delta = (
            local_pos-p1
        )
        tangent1_len2 = tangent1.length_squared
        tangent2_len2 = tangent2.length_squared
        normal_projection = (
            delta.dot(normal)
            /
            normal.length_squared
        )
        tangent1_projection = (
            delta.dot(tangent1)
            /
            tangent1_len2
        )
        tangent2_projection = (
            delta.dot(tangent2)
            /
            tangent2_len2
        )
        ######################################################
        # Store
        ######################################################
        results.append(
            SkinWrapVertex(
                closestTriangle=tri.original_triangle_id,
                Vertex1=v1,
                Vertex2=v2,
                Vertex3=v3,
                surfaceNormalProjection=
                    float(normal_projection),
                surfaceTangent1Projection=
                    float(tangent1_projection),
                surfaceTangent2Projection=
                    float(tangent2_projection),
                surfaceNormalWrapNormalDot=
                    float(
                        wrap_normal.dot(normal)
                    ),
                surfaceTangent1WrapNormalDot=
                    float(
                        wrap_normal.dot(tangent1)/tangent1.length_squared
                    ),
                surfaceTangent2WrapNormalDot=
                    float(
                        wrap_normal.dot(tangent2)/tangent2.length_squared
                    )
            )
        )

    print("===========Empty===========")
    print("tri",empty_count["tri"])
    print("distance",empty_count["distance"])
    print("tangent1",empty_count["tangent1"])
    print("normal",empty_count["normal"])
    print("tangent2",empty_count["tangent2"])
    print("wrap_normal",empty_count["wrap_normal"])
    return results
# ============================================================
# find_nearest_triangle
# ============================================================
from mathutils import Vector

from ..wrap.bvh_wrap import build_anchor_triangle_cache, get_cache
from ..wrap.wrap_types import TriangleInfo


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

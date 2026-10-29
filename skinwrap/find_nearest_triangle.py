from mathutils import Vector
from ..wrap.bvh_wrap import get_cache
from ..wrap.wrap_types import TriangleInfo


def _select_tree(cache, anchor_only: bool):
    if anchor_only and cache.anchor_bvh is not None and cache.anchor_triangles:
        # 映射表必须与三角形表等长；不一致时宁可回退全身，也不能用错下标
        if len(cache.anchor_bvh_to_triangle) == len(cache.anchor_triangles):
            return cache.anchor_bvh, cache.anchor_triangles, cache.anchor_bvh_to_triangle
    # 防御性回退：anchor 不可用时用全身 BVH，绝不 raise
    return cache.body_bvh, cache.body_triangles, cache.bvh_to_triangle


def find_nearest_triangle(
    pos: Vector,
    wrap_normal: Vector | None,
    *,
    anchor_only: bool = False,
    check_normals: bool = False,
    normal_dot_limit=0,
) -> TriangleInfo | None:

    cache = get_cache()
    if cache is None:
        return None

    tree, triangles, mapping = _select_tree(cache, anchor_only)
    if tree is None or not triangles or not mapping:
        return None

    hit = tree.find_nearest((pos.x, pos.y, pos.z))
    if hit is None:
        return None
    _location, _bvh_normal, polygon_index, _distance = hit

    # ← 关键防护：BVH 下标只能通过映射表翻译，且必须双向越界检查
    if polygon_index is None or not (0 <= polygon_index < len(mapping)):
        return None
    tri_index = mapping[polygon_index]
    if tri_index < 0 or tri_index >= len(triangles):
        return None

    tri = triangles[tri_index]

    if wrap_normal is not None and check_normals:
        if wrap_normal.dot(tri.normal) < normal_dot_limit:
            return None        # 不要 print，20k 顶点会刷爆控制台

    return tri
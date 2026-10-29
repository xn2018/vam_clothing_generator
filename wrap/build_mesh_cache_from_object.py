from typing import cast

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from ..paths import PLUGIN_ROOT
from ..reader.daz_surface_normals import load_surface_normals
from ..reader.genesis_base_data import resolve_body_base_data
from .mesh_inspect import collect_anchor_vertices, geometry_signature
from .wrap_types import DAZMeshData, SkinWrapCache, TriangleInfo


def build_mesh_cache_from_object(genesis_obj: bpy.types.Object) -> SkinWrapCache:
    """
    Build the SkinWrap cache in VaM's *base* vertex space.

    ``TriangleInfo.vertex1..3`` end up in the VAB as
    ``DAZSkinWrapStore.Vertex1..3``, which VaM uses to index the body's
    base vertex buffers (``skin.rawVertsBuffer`` on the GPU path).  They
    must therefore never point at the UV duplicate vertices that sit
    after the base block of a render mesh - otherwise every triangle
    touching a UV seam reads a wrong vertex and the clothing tears along
    the seams.

    The base mesh comes from DAZExtraData when it matches the object, and
    is derived from the object otherwise (see reader.genesis_base_data).
    """
    base_data, warnings = resolve_body_base_data(genesis_obj)
    for warning in warnings:
        print("[SkinWrap]", warning)

    base_vertices = base_data.vertices
    base_triangles = base_data.triangles
    num_base = len(base_vertices)
    tri_count = len(base_triangles) // 3

    if num_base == 0:
        raise RuntimeError("Genesis base 顶点为空，无法建立 SkinWrap 缓存")
    if tri_count == 0:
        raise RuntimeError("Genesis 网格没有三角形，无法建立 SkinWrap 缓存")

    surface_normals = load_surface_normals(
        PLUGIN_ROOT / "DAZExtraData" / "surfaceNormals.bin"
    )
    if len(surface_normals) < tri_count:
        raise RuntimeError(
            f"surfaceNormals 不足: bin={len(surface_normals)} 三角形={tri_count}；"
            "Genesis 拓扑与 surfaceNormals.bin 不匹配"
        )

    triangles: list[TriangleInfo] = []
    zero_normal = 0
    normal_flip = 0
    non_unit = 0

    for i in range(0, len(base_triangles), 3):
        a, b, c = base_triangles[i], base_triangles[i + 1], base_triangles[i + 2]
        p1, p2, p3 = base_vertices[a], base_vertices[b], base_vertices[c]
        tri_index = i // 3

        geo = cast(Vector, (p2 - p1).cross(p3 - p1))   # 真实几何法线（未归一化）
        normal = surface_normals[tri_index].copy()     # DAZ 烘焙面法线

        if normal.length_squared < 1e-12:
            # 补洞：几何有效但 bin 法线缺失 → 用几何法线，且必须归一化
            zero_normal += 1
            if geo.length_squared < 1e-12:
                continue                               # 真正零面积，无切空间
            normal = geo.normalized()
        else:
            if abs(normal.length - 1.0) > 1e-3:
                non_unit += 1
            if geo.length_squared > 1e-12 and normal.dot(geo) < 0:
                normal_flip += 1
            # 统一到单位法线约定（投影量对缩放不敏感）
            normal = normal.normalized()

        triangles.append(TriangleInfo(
            triangle_id=len(triangles),
            original_triangle_id=tri_index,
            vertex1=a, vertex2=b, vertex3=c,
            v1=p1, v2=p2, v3=p3,
            center=(p1 + p2 + p3) / 3.0,
            normal=normal,
        ))

    if not triangles:
        raise RuntimeError("Genesis 网格没有有效三角形")

    # === 唯一真源：多边形序列从 triangles 派生，结构上不可能错位 ===
    bvh_polygons = [[t.vertex1, t.vertex2, t.vertex3] for t in triangles]
    bvh_vertices = [(float(v.x), float(v.y), float(v.z)) for v in base_vertices]
    bvh_tree = BVHTree.FromPolygons(bvh_vertices, bvh_polygons, all_triangles=True)

    body_mesh = DAZMeshData()
    body_mesh.base_vertices = base_vertices
    body_mesh.base_triangles = base_triangles
    body_mesh.base_surface_normals = surface_normals
    body_mesh.base_vertex_count = num_base
    body_mesh.matrix_world = genesis_obj.matrix_world.copy()

    # The anchor group is stored in object vertex space; the wrap works in
    # base vertex space, so translate the indices once.
    object_to_base = base_data.object_to_base
    anchor_object = collect_anchor_vertices(genesis_obj)
    anchor_base = {
        object_to_base[index]
        for index in anchor_object
        if index in object_to_base
    }

    cache = SkinWrapCache()
    cache.object_name = genesis_obj.name
    cache.mesh_pointer = genesis_obj.data.as_pointer()
    cache.geometry_signature = geometry_signature(genesis_obj)
    cache.body_mesh = body_mesh
    cache.body_triangles = triangles
    cache.body_bvh = bvh_tree
    cache.bvh_to_triangle = list(range(len(triangles)))
    cache.body_base_count = num_base
    cache.body_uv_count = base_data.num_uv_vertices
    cache.body_map_count = len(base_data.vertex_maps)
    cache.body_source = base_data.source
    cache.vertex_count = len(genesis_obj.data.vertices)
    cache.triangle_count = len(triangles)
    cache.anchor_vertices = anchor_base
    cache.anchor_signature = tuple(sorted(anchor_object))
    cache.initialized = True
    cache.normal_mismatch = normal_flip
    cache.normal_non_unit = non_unit

    print(
        "[SkinWrap] Body data:",
        base_data.source,
        "base =", num_base,
        "uv =", base_data.num_uv_vertices,
        "maps =", len(base_data.vertex_maps),
        "triangles =", len(triangles),
    )

    return cache

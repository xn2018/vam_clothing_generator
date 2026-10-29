# ============================================================
# Genesis base mesh data (VaM ground truth)
#
# VaM's Genesis mesh has two vertex spaces:
#
#   baseVertices : welded geometry vertices.  THIS is the index space
#                  of DAZSkinWrapStore.Vertex1/2/3 and of baseTriangles.
#   UVVertices   : baseVertices + one duplicate per UV seam, indexed by
#                  baseVerticesToUVVertices (tovert -> fromvert).
#
# The Blender "Genesis" object is normally imported from a *render*
# mesh (model.obj), which already contains the UV duplicates, so its
# vertex indices live in UV space.  Wrapping must be done in base space:
# VaM feeds Vertex1..3 to the body's base vertex buffers (rawVertsBuffer
# on the GPU path), so a duplicate index overflows there and only the
# triangles touching a UV seam break.
#
# DAZExtraData/*.json is a dump of VaM's arrays:
#   BaseVertices.json  -> base vertices
#   BaseTriangles.json -> base triangles (triangulated, VaM order)
#   VertexMaps.json    -> tovert (UV duplicate) -> fromvert (base)
#
# The data is only used when it can be matched against the object.  If it
# can not (different Genesis version, edited mesh), the base mesh is
# derived from the object itself: VaM appends UV duplicates *after* the
# base block, so the base block ends at the last vertex whose position is
# unique.  Deriving by "merge all coincident vertices" would be wrong:
# a base mesh legitimately contains coincident vertices (eye lids, lips)
# and merging them would shift every following index.
# ============================================================
import json
from dataclasses import dataclass, field
from pathlib import Path

import bpy
from mathutils import Vector

from ..paths import PLUGIN_ROOT

BASE_VERTICES_FILE = "BaseVertices.json"
BASE_TRIANGLES_FILE = "BaseTriangles.json"
VERTEX_MAPS_FILE = "VertexMaps.json"

# Position tolerance when matching DAZExtraData against the Blender object.
MATCH_TOLERANCE = 1e-5


class GenesisBaseDataError(RuntimeError):
    """Raised when a usable Genesis base mesh can not be provided."""


@dataclass(slots=True)
class GenesisBaseData:
    vertices: list[Vector] = field(default_factory=list)
    triangles: list[int] = field(default_factory=list)
    # (fromvert, tovert, polyindex), already deduplicated by tovert
    vertex_maps: list[tuple[int, int, int]] = field(default_factory=list)
    num_uv_vertices: int = 0
    source: str = ""
    # object vertex index -> base vertex index
    object_to_base: dict[int, int] = field(default_factory=dict)

    @property
    def num_base_vertices(self) -> int:
        return len(self.vertices)

    @property
    def num_triangles(self) -> int:
        return len(self.triangles) // 3


_CACHE: GenesisBaseData | None = None


# ============================================================
# Loading
# ============================================================
def _read_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def clear_cache() -> None:
    global _CACHE
    _CACHE = None


def load_daz_base_data(
    directory: str | Path | None = None
) -> GenesisBaseData:
    """
    Load and cache DAZExtraData's base mesh.

    Raises GenesisBaseDataError when the files are missing or internally
    inconsistent, so callers can fall back to the object.
    """
    global _CACHE
    if _CACHE is not None:
        return _CACHE

    root = (
        Path(directory)
        if directory is not None
        else Path(PLUGIN_ROOT) / "DAZExtraData"
    )
    base_path = root / BASE_VERTICES_FILE
    triangle_path = root / BASE_TRIANGLES_FILE
    map_path = root / VERTEX_MAPS_FILE

    for path in (base_path, triangle_path, map_path):
        if not path.is_file():
            raise GenesisBaseDataError(f"缺少文件: {path}")

    raw_vertices = _read_json(base_path)
    raw_triangles = _read_json(triangle_path)
    raw_maps = _read_json(map_path)

    vertices = [
        Vector((float(item["x"]), float(item["y"]), float(item["z"])))
        for item in raw_vertices
    ]
    if not vertices:
        raise GenesisBaseDataError(f"{BASE_VERTICES_FILE} 为空")
    num_base = len(vertices)

    triangles = [int(value) for value in raw_triangles]
    if len(triangles) % 3 != 0:
        raise GenesisBaseDataError(f"{BASE_TRIANGLES_FILE} 长度不是 3 的倍数")
    for index in triangles:
        if index < 0 or index >= num_base:
            raise GenesisBaseDataError(
                f"{BASE_TRIANGLES_FILE} 索引越界: {index} (base={num_base})"
            )

    maps: list[tuple[int, int, int]] = []
    seen_to: set[int] = set()
    for item in raw_maps:
        fromvert = int(item["fromvert"])
        tovert = int(item["tovert"])
        polyindex = int(item.get("polyindex", 0))
        if not 0 <= fromvert < num_base:
            raise GenesisBaseDataError(
                f"{VERTEX_MAPS_FILE} fromvert 越界: {fromvert} (base={num_base})"
            )
        # VaM keeps exactly one map per duplicate (DAZMesh.Import dedupes
        # by tovert); the JSON contains one entry per polygon occurrence.
        if tovert in seen_to:
            continue
        seen_to.add(tovert)
        maps.append((fromvert, tovert, polyindex))

    if not maps:
        raise GenesisBaseDataError(f"{VERTEX_MAPS_FILE} 没有有效映射")

    num_uv = max(tovert for _, tovert, _ in maps) + 1
    if num_uv != num_base + len(maps):
        raise GenesisBaseDataError(
            f"UV 顶点数不自洽: base={num_base}, maps={len(maps)}, "
            f"max(tovert)+1={num_uv}"
        )

    _CACHE = GenesisBaseData(
        vertices=vertices,
        triangles=triangles,
        vertex_maps=maps,
        num_uv_vertices=num_uv,
        source="DAZExtraData",
    )
    return _CACHE


# ============================================================
# Matching DAZExtraData against the Blender object
# ============================================================
def validate_against_object(
    data: GenesisBaseData,
    genesis_obj: bpy.types.Object,
    tolerance: float = MATCH_TOLERANCE,
) -> list[str]:
    """
    Return a list of reasons why ``data`` does not describe ``genesis_obj``.
    An empty list means the data can be used as-is.
    """
    mesh = getattr(genesis_obj, "data", None)
    if not isinstance(mesh, bpy.types.Mesh):
        return ["Genesis 不是网格对象"]

    count = len(mesh.vertices)
    problems: list[str] = []

    if count == data.num_base_vertices:
        # Object is already the welded base mesh; only positions matter.
        for index in range(count):
            if (mesh.vertices[index].co - data.vertices[index]).length > tolerance:
                problems.append(f"base 顶点 {index} 位置不一致")
                if len(problems) >= 8:
                    return problems
        return problems

    if count != data.num_uv_vertices:
        return [
            f"物体顶点数 {count} 与 DAZExtraData "
            f"base={data.num_base_vertices} / uv={data.num_uv_vertices} 都不匹配"
        ]

    for index in range(data.num_base_vertices):
        if (mesh.vertices[index].co - data.vertices[index]).length > tolerance:
            problems.append(f"base 顶点 {index} 位置不一致")
            if len(problems) >= 8:
                return problems

    for fromvert, tovert, _ in data.vertex_maps:
        if tovert >= count:
            problems.append(f"map.tovert {tovert} 超出物体顶点数 {count}")
        elif (
            mesh.vertices[tovert].co - mesh.vertices[fromvert].co
        ).length > tolerance:
            problems.append(f"map {tovert} -> {fromvert} 位置不一致")
        if len(problems) >= 8:
            break

    return problems


# ============================================================
# Fallback: derive base data from the object
# ============================================================
def derive_from_object(
    genesis_obj: bpy.types.Object
) -> GenesisBaseData:
    """
    Derive the base mesh from a render mesh that has UV duplicates
    appended after the base block.

    Raises GenesisBaseDataError when no base block can be identified.
    """
    mesh = getattr(genesis_obj, "data", None)
    if not isinstance(mesh, bpy.types.Mesh):
        raise GenesisBaseDataError("Genesis 不是网格对象")

    count = len(mesh.vertices)
    if count == 0:
        raise GenesisBaseDataError("Genesis 没有顶点")

    positions = [vertex.co.copy() for vertex in mesh.vertices]

    first_index: dict[tuple[float, float, float], int] = {}
    for index, co in enumerate(positions):
        key = (co.x, co.y, co.z)
        if key not in first_index:
            first_index[key] = index

    # Base block ends at the last vertex that is a *first* occurrence.
    boundary = count - 1
    while boundary >= 0:
        co = positions[boundary]
        if first_index[(co.x, co.y, co.z)] == boundary:
            break
        boundary -= 1

    num_base = boundary + 1
    if num_base <= 0 or num_base > count:
        raise GenesisBaseDataError("无法推导 base 顶点边界")

    object_to_base: dict[int, int] = {index: index for index in range(num_base)}
    vertex_maps: list[tuple[int, int, int]] = []

    for index in range(num_base, count):
        co = positions[index]
        origin = first_index[(co.x, co.y, co.z)]
        if origin >= num_base:
            raise GenesisBaseDataError(
                f"无法解析复制顶点 {index} 对应的 base 顶点"
            )
        object_to_base[index] = origin
        vertex_maps.append((origin, index, 0))

    triangles: list[int] = []
    for poly in mesh.polygons:
        indices = [object_to_base[vertex] for vertex in poly.vertices]
        if len(indices) < 3:
            continue
        root = indices[0]
        for offset in range(1, len(indices) - 1):
            triangles.extend((root, indices[offset], indices[offset + 1]))

    if not triangles:
        raise GenesisBaseDataError("Genesis 没有三角形")

    return GenesisBaseData(
        vertices=[co.copy() for co in positions[:num_base]],
        triangles=triangles,
        vertex_maps=vertex_maps,
        num_uv_vertices=count,
        source="object",
        object_to_base=object_to_base,
    )


# ============================================================
# Resolve
# ============================================================
def _build_object_to_base(
    data: GenesisBaseData,
    genesis_obj: bpy.types.Object,
) -> dict[int, int]:
    count = len(genesis_obj.data.vertices)
    if count == data.num_base_vertices:
        return {index: index for index in range(count)}

    mapping = {index: index for index in range(data.num_base_vertices)}
    for fromvert, tovert, _ in data.vertex_maps:
        mapping[tovert] = fromvert
    return mapping


def resolve_body_base_data(
    genesis_obj: bpy.types.Object
) -> tuple[GenesisBaseData, list[str]]:
    """
    Return the base mesh to wrap against, plus human readable warnings.

    Preference order:
      1. DAZExtraData, if it matches the object exactly;
      2. the object itself (duplicates appended after the base block).
    """
    warnings: list[str] = []

    try:
        data = load_daz_base_data()
    except Exception as error:
        warnings.append(
            f"DAZExtraData 不可用（{error}），改为从 Genesis 物体推导 base 网格"
        )
        return derive_from_object(genesis_obj), warnings

    problems = validate_against_object(data, genesis_obj)
    if problems:
        warnings.append(
            "DAZExtraData 与当前 Genesis 不匹配，改为从物体推导 base 网格："
            + "；".join(problems[:3])
        )
        return derive_from_object(genesis_obj), warnings

    data.object_to_base = _build_object_to_base(data, genesis_obj)
    return data, warnings

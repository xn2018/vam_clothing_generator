# ============================================================
# Dev Utils: SkinWrap cache self-test
#
# Read-only validation of the SkinWrap cache.  Nothing is rebuilt
# and nothing is modified, so a warning here means "the cache you
# are about to export from is not what you think it is".
#
# Three independent checks:
#
#   1. Signature   - is the cached geometry still the current
#                    Genesis geometry (mesh pointer, vertex /
#                    polygon / material counts, coordinate and
#                    material-index hashes, anchor vertex set)?
#   2. Structure   - are bvh_to_triangle, body_triangles and the
#                    TriangleInfo ids mutually consistent?
#   3. Ray cast    - sample triangles, shoot a ray from the
#                    triangle centroid back along -normal and check
#                    that the BVH returns that very polygon.
# ============================================================
import bpy

from ..reader.genesis_base_data import load_daz_base_data
from ..wrap.bvh_wrap import cache_ready, get_cache
from ..wrap.mesh_inspect import geometry_signature, get_anchor_signature
from ..wrap.wrap_types import SkinWrapCache
from .operators_types import OperatorReturn

# Must stay in sync with wrap.mesh_inspect.geometry_signature()
_SIGNATURE_FIELDS = (
    "mesh datablock",
    "vertex count",
    "polygon count",
    "material count",
    "vertex coordinate hash",
    "material index hash",
)

# Sample at most this many triangles per BVH (Genesis has ~70k).
RAY_SAMPLE_LIMIT = 2000
# Offset the ray origin along the triangle normal to avoid starting
# exactly on the surface.
RAY_ORIGIN_OFFSET = 1e-4
# How many failing samples to print / report.
RAY_MAX_REPORTED_FAILURES = 10
# Hard cap for structural problem lists.
MAX_REPORTED_PROBLEMS = 20


# ============================================================
# 1. Signature
# ============================================================
def _diff_signature(stored: tuple, current: tuple) -> list[str]:
    if not stored or not current:
        return ["cache has no geometry signature (built by an older version)"]

    problems: list[str] = []
    if len(stored) != len(current):
        problems.append(
            f"signature length {len(stored)} -> {len(current)}"
        )

    for label, old, new in zip(_SIGNATURE_FIELDS, stored, current):
        if old != new:
            problems.append(f"{label}: {old!r} -> {new!r}")

    return problems


def _diff_anchor(stored: tuple, current: tuple) -> list[str]:
    if stored == current:
        return []

    old = set(stored)
    new = set(current)
    return [
        "anchor group: "
        f"{len(old)} -> {len(new)} vertices "
        f"({len(old - new)} removed, {len(new - old)} added)"
    ]


# ============================================================
# 2. Structure
# ============================================================
def _check_triangle_table(cache: SkinWrapCache) -> list[str]:
    triangles = cache.body_triangles
    if not triangles:
        return ["body_triangles is empty"]

    problems: list[str] = []

    if cache.body_bvh is None:
        problems.append("body_triangles is not empty but body_bvh is None")

    mapping = cache.bvh_to_triangle
    if len(mapping) != len(triangles):
        problems.append(
            f"bvh_to_triangle length {len(mapping)} "
            f"!= body_triangles {len(triangles)}"
        )

    vertex_count = (
        len(cache.body_mesh.base_vertices)
        if cache.body_mesh is not None
        else 0
    )

    for position, tri in enumerate(triangles):
        message = None

        # triangle_id must equal its slot, otherwise the identity
        # mapping assumption used by bvh_to_triangle is broken
        if tri.triangle_id != position:
            message = f"triangle[{position}].triangle_id={tri.triangle_id}"
        elif position < len(mapping) and mapping[position] != position:
            message = f"bvh_to_triangle[{position}]={mapping[position]}"
        elif vertex_count and not (
            0 <= tri.vertex1 < vertex_count
            and 0 <= tri.vertex2 < vertex_count
            and 0 <= tri.vertex3 < vertex_count
        ):
            message = f"triangle[{position}] vertex index out of range"

        if message is not None:
            problems.append(message)
            if len(problems) >= MAX_REPORTED_PROBLEMS:
                problems.append("... truncated")
                break

    return problems


def _check_anchor_table(cache: SkinWrapCache) -> list[str]:
    triangles = cache.anchor_triangles
    if not triangles:
        # anchor data is built lazily on CALC; not an error
        return []

    problems: list[str] = []
    mapping = cache.anchor_bvh_to_triangle

    if cache.anchor_bvh is None:
        problems.append("anchor_triangles is not empty but anchor_bvh is None")

    if len(mapping) != len(triangles):
        problems.append(
            f"anchor_bvh_to_triangle length {len(mapping)} "
            f"!= anchor_triangles {len(triangles)}"
        )

    body = cache.body_triangles

    for position, tri in enumerate(triangles):
        if position >= len(mapping):
            break

        target = mapping[position]

        if not (0 <= target < len(body)):
            problems.append(
                f"anchor_bvh_to_triangle[{position}]={target} out of range"
            )
        elif body[target].triangle_id != tri.triangle_id:
            problems.append(
                f"anchor_bvh_to_triangle[{position}] -> body[{target}] "
                f"id {body[target].triangle_id}, expected {tri.triangle_id}"
            )

        if len(problems) >= MAX_REPORTED_PROBLEMS:
            problems.append("... truncated")
            break

    return problems


# ============================================================
# 2b. Body vertex space (base vs UV)
# ============================================================
def _check_body_layout(cache: SkinWrapCache) -> tuple[list[str], list[str]]:
    """
    Verify the cache lives in VaM's base vertex space.

    Returns (problems, info):
      problems -> hard errors (Vertex1..3 outside base space, ...)
      info     -> what was used / what DAZExtraData says
    """
    problems: list[str] = []
    info: list[str] = []

    base_count = cache.body_base_count
    if base_count <= 0 and cache.body_mesh is not None:
        base_count = len(cache.body_mesh.base_vertices)

    if base_count <= 0:
        return ["body base vertex count is 0"], info

    if cache.body_mesh is None:
        problems.append("body_mesh is None")
    elif len(cache.body_mesh.base_vertices) != base_count:
        problems.append(
            f"body_mesh.base_vertices {len(cache.body_mesh.base_vertices)} "
            f"!= body_base_count {base_count}"
        )

    uv_count = cache.body_uv_count
    map_count = cache.body_map_count
    if uv_count and uv_count != base_count + map_count:
        problems.append(
            f"uv {uv_count} != base {base_count} + maps {map_count}"
        )

    overflows: list[int] = []
    overflow_count = 0
    for position, tri in enumerate(cache.body_triangles):
        if max(tri.vertex1, tri.vertex2, tri.vertex3) >= base_count:
            overflow_count += 1
            if len(overflows) < 8:
                overflows.append(position)
    if overflow_count:
        problems.append(
            f"{overflow_count} body triangles reference UV duplicate "
            f"vertices (>= base {base_count}), e.g. {overflows}"
        )

    info.append(
        f"cache base={base_count} uv={uv_count} maps={map_count} "
        f"source={cache.body_source or '?'}"
    )

    try:
        ground = load_daz_base_data()
    except Exception as error:
        info.append(f"DAZExtraData unavailable: {error}")
    else:
        info.append(
            f"DAZExtraData base={ground.num_base_vertices} "
            f"uv={ground.num_uv_vertices} maps={len(ground.vertex_maps)}"
        )
        if ground.num_base_vertices != base_count:
            info.append(
                "WARNING: cache was not built from DAZExtraData "
                "(base count differs)"
            )

    return problems, info


# ============================================================
# 3. Ray cast round trip
# ============================================================
def _ray_cast_test(
    bvh,
    triangles: list,
    mapping: list[int],
    limit: int = RAY_SAMPLE_LIMIT,
) -> dict:
    """
    For a sample of triangles, cast a ray from the centroid back along
    -normal.  The BVH must report the polygon that maps to the very
    same TriangleInfo; anything else means the polygon table and the
    triangle table have drifted apart.
    """
    total = len(triangles)
    stride = max(1, total // limit) if limit > 0 else 1

    result = {
        "total": total,
        "stride": stride,
        "tested": 0,
        "passed": 0,
        "skipped": 0,
        "failures": [],
    }

    for position in range(0, total, stride):
        tri = triangles[position]

        # Degenerate normals can not define a ray; they were filtered
        # out when the table was built, so this should never happen.
        if tri.normal.length_squared < 1e-12:
            result["skipped"] += 1
            continue

        direction = -tri.normal.normalized()
        origin = tri.center - direction * RAY_ORIGIN_OFFSET

        hit = bvh.ray_cast(origin, direction)
        result["tested"] += 1

        polygon_index = None if hit is None else hit[2]

        if polygon_index is None or polygon_index < 0:
            result["failures"].append((position, None))
            continue

        resolved = (
            mapping[polygon_index]
            if polygon_index < len(mapping)
            else -1
        )

        if resolved == position:
            result["passed"] += 1
        else:
            result["failures"].append((position, resolved))

    return result


# ============================================================
# Console report
# ============================================================
def _print_report(
    genesis,
    cache: SkinWrapCache,
    signature_problems: list[str],
    structure_problems: list[str],
    anchor_problems: list[str],
    body_problems: list[str],
    body_info: list[str],
    body_ray: dict | None,
    anchor_ray: dict | None,
) -> None:
    print()
    print("=" * 64)
    print("[Validate Cache]")
    print("  Object       :", genesis.name)
    print("  Triangles    :", len(cache.body_triangles))
    print("  Anchor verts :", len(cache.anchor_vertices))
    print("  Anchor tris  :", len(cache.anchor_triangles))
    for line in body_info:
        print("  Body data    :", line)

    for label, ray in (("body", body_ray), ("anchor", anchor_ray)):
        if ray is None:
            continue
        print(
            f"  Ray {label:<7}: {ray['passed']}/{ray['tested']} passed"
            f"  (stride {ray['stride']}, {ray['total']} triangles"
            f", {ray['skipped']} skipped)"
        )
        for position, resolved in ray["failures"][:RAY_MAX_REPORTED_FAILURES]:
            print(f"      fail: triangle {position} -> {resolved}")
        remaining = len(ray["failures"]) - RAY_MAX_REPORTED_FAILURES
        if remaining > 0:
            print(f"      ... {remaining} more")

    if signature_problems:
        print("  Signature    : MISMATCH")
        for problem in signature_problems:
            print("      -", problem)
    else:
        print("  Signature    : OK")

    for label, problems in (
        ("Structure", structure_problems),
        ("Anchor map", anchor_problems),
        ("Body layout", body_problems),
    ):
        if problems:
            print(f"  {label:<12}: PROBLEM")
            for problem in problems:
                print("      -", problem)
        else:
            print(f"  {label:<12}: OK")

    print("=" * 64)


# ============================================================
# Operator
# ============================================================
class VAM_OT_VALIDATE_CACHE(bpy.types.Operator):
    """Run a read-only self-test on the SkinWrap cache (Dev)"""

    bl_idname = "vam.ot_validatecache"
    bl_label = "Validate Cache"

    @classmethod
    def poll(cls, context):
        props = context.scene.vamgen_props
        return props.genesis_obj is not None

    def execute(
        self,
        context: bpy.types.Context
    ) -> set[OperatorReturn]:
        props = context.scene.vamgen_props
        genesis = props.genesis_obj

        if genesis is None:
            self.report({'ERROR'}, "Genesis mesh not selected")
            return {'CANCELLED'}

        if not cache_ready():
            self.report(
                {'WARNING'},
                "SkinWrap cache is empty, run CALC first"
            )
            return {'CANCELLED'}

        cache = get_cache()

        # --------------------------------------------------
        # 1. Signatures
        # --------------------------------------------------
        try:
            current_signature = geometry_signature(genesis)
            current_anchor = get_anchor_signature(genesis)
        except Exception as error:
            self.report(
                {'ERROR'},
                f"Cannot read Genesis mesh: {error}"
            )
            return {'CANCELLED'}

        signature_problems: list[str] = []

        if cache.object_name != genesis.name:
            signature_problems.append(
                f"object name: {cache.object_name!r} -> {genesis.name!r}"
            )

        signature_problems.extend(
            _diff_signature(
                cache.geometry_signature,
                current_signature
            )
        )

        if cache.vertex_count != len(genesis.data.vertices):
            signature_problems.append(
                f"cached vertex_count {cache.vertex_count} "
                f"-> mesh {len(genesis.data.vertices)}"
            )

        if cache.triangle_count != len(cache.body_triangles):
            signature_problems.append(
                f"cached triangle_count {cache.triangle_count} "
                f"-> table {len(cache.body_triangles)}"
            )

        signature_problems.extend(
            _diff_anchor(
                cache.anchor_signature,
                current_anchor
            )
        )

        # --------------------------------------------------
        # 2. Structure
        # --------------------------------------------------
        structure_problems = _check_triangle_table(cache)
        anchor_problems = _check_anchor_table(cache)
        body_problems, body_info = _check_body_layout(cache)

        # --------------------------------------------------
        # 3. Ray cast
        # --------------------------------------------------
        body_ray = None
        if cache.body_bvh is not None:
            body_ray = _ray_cast_test(
                cache.body_bvh,
                cache.body_triangles,
                cache.bvh_to_triangle
            )

        anchor_ray = None
        if cache.anchor_bvh is not None and cache.anchor_triangles:
            anchor_ray = _ray_cast_test(
                cache.anchor_bvh,
                cache.anchor_triangles,
                cache.anchor_bvh_to_triangle
            )

        # --------------------------------------------------
        # Report
        # --------------------------------------------------
        _print_report(
            genesis,
            cache,
            signature_problems,
            structure_problems,
            anchor_problems,
            body_problems,
            body_info,
            body_ray,
            anchor_ray
        )

        ray_failures = 0
        ray_tested = 0
        for result in (body_ray, anchor_ray):
            if result is None:
                continue
            ray_failures += len(result["failures"])
            ray_tested += result["tested"]

        if signature_problems:
            self.report(
                {'ERROR'},
                f"Cache is stale: {signature_problems[0]} (run CALC again)"
            )
            return {'FINISHED'}

        if structure_problems or anchor_problems or body_problems:
            first = (structure_problems or anchor_problems or body_problems)[0]
            self.report(
                {'ERROR'},
                f"Cache structure broken: {first}"
            )
            return {'FINISHED'}

        if ray_failures:
            self.report(
                {'WARNING'},
                f"Ray self-test: {ray_tested - ray_failures}/{ray_tested} "
                f"passed, {ray_failures} mismatch"
            )
            return {'FINISHED'}

        if any("WARNING" in line for line in body_info):
            self.report(
                {'WARNING'},
                "Cache 不是用 DAZExtraData 构建的（base 数量不同），接缝可能仍会出错"
            )
            return {'FINISHED'}

        self.report(
            {'INFO'},
            f"Cache OK: base {cache.body_base_count}, "
            f"{len(cache.body_triangles)} triangles, "
            f"{ray_tested} ray samples passed"
        )
        return {'FINISHED'}

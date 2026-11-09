# ============================================================
# Blender curve hair helpers
#
# Shared by:
#   * Extract Curve  (operators.generate_package.VAM_OT_ExtractHairStrands)
#   * CurveHairImporter / curve_resampler  (export sampling)
#   * DAZHairData.build_hair_root_scalp_mapping  (curve -> scalp mapping)
#
# Sampling:
#   BEZIER splines are evaluated segment by segment (handles included);
#   POLY / NURBS use their control points as a polyline.  Resampling is
#   arc-length based, so every strand gets evenly spaced points no matter
#   how dense its control points are.
# ============================================================
from dataclasses import dataclass, field

import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree

DEFAULT_SCALP_GROUP = "scalp"
DEFAULT_MAX_ROOT_DISTANCE = 0.1
DEFAULT_BEZIER_STEPS = 8


class HairExtractionError(RuntimeError):
    """Raised when the curve hair can not be matched to the scalp."""


@dataclass(slots=True)
class HairExtractionResult:
    scalp_vertex_count: int
    total_splines: int
    # spline indices that were matched, in scalp vertex order
    spline_indices: list[int]
    # (scalp vertex index, spline index, match distance)
    assignments: list[tuple[int, int, float]]
    # parallel to spline_indices: reverse the copied spline so its root is
    # the end closest to the scalp
    reverse_flags: list[bool] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ============================================================
# Spline geometry
# ============================================================
def spline_control_points(spline) -> list[Vector]:
    """Local-space control points of a spline."""
    if spline.type == "BEZIER":
        return [point.co.copy() for point in spline.bezier_points]
    return [
        Vector((point.co.x, point.co.y, point.co.z))
        for point in spline.points
    ]


def _cubic_bezier(p0, p1, p2, p3, t: float) -> Vector:
    u = 1.0 - t
    return (
        p0 * (u * u * u)
        + p1 * (3.0 * u * u * t)
        + p2 * (3.0 * u * t * t)
        + p3 * (t * t * t)
    )


def sample_bezier_polyline(
    spline,
    steps_per_segment: int = DEFAULT_BEZIER_STEPS,
) -> list[Vector]:
    """
    Dense local-space polyline that follows *every* bezier segment.

    The previous exporter only used the first and the last control point,
    which collapsed multi-point bezier strands into a single segment.
    """
    bezier = spline.bezier_points
    if len(bezier) == 0:
        return []
    if len(bezier) == 1:
        return [bezier[0].co.copy()]

    steps = max(1, int(steps_per_segment))
    count = len(bezier)
    segments = count if spline.use_cyclic_u else count - 1

    points: list[Vector] = []
    for segment in range(segments):
        p0 = bezier[segment]
        p1 = bezier[(segment + 1) % count]
        for step in range(steps):
            t = step / steps
            points.append(
                _cubic_bezier(
                    p0.co,
                    p0.handle_right,
                    p1.handle_left,
                    p1.co,
                    t,
                )
            )

    if not spline.use_cyclic_u:
        points.append(bezier[-1].co.copy())

    return points


def sample_spline_polyline(
    spline,
    steps_per_segment: int = DEFAULT_BEZIER_STEPS,
) -> list[Vector]:
    """Local-space polyline for any spline type."""
    if spline.type == "BEZIER":
        return sample_bezier_polyline(spline, steps_per_segment)

    points = spline_control_points(spline)
    if spline.use_cyclic_u and len(points) > 1:
        points = points + [points[0].copy()]
    return points


def resample_polyline(points: list[Vector], count: int) -> list[Vector]:
    """Resample a polyline to ``count`` points evenly spaced by arc length."""
    count = max(2, int(count))
    if len(points) < 2:
        return [point.copy() for point in points]

    lengths = [0.0]
    total = 0.0
    for index in range(1, len(points)):
        total += (points[index] - points[index - 1]).length
        lengths.append(total)

    if total <= 1e-12:
        return [points[0].copy() for _ in range(count)]

    result: list[Vector] = []
    cursor = 0
    for index in range(count):
        target = total * index / (count - 1)
        while cursor < len(lengths) - 2 and lengths[cursor + 1] < target:
            cursor += 1
        low = lengths[cursor]
        high = lengths[cursor + 1]
        factor = (target - low) / (high - low) if high > low else 0.0
        result.append(points[cursor].lerp(points[cursor + 1], factor))
    return result


def spline_root_world(hair_obj: bpy.types.Object, spline) -> Vector | None:
    points = spline_control_points(spline)
    if not points:
        return None
    return hair_obj.matrix_world @ points[0]


def spline_tip_world(hair_obj: bpy.types.Object, spline) -> Vector | None:
    points = spline_control_points(spline)
    if not points:
        return None
    return hair_obj.matrix_world @ points[-1]


# ============================================================
# Editing
# ============================================================
def reverse_spline(spline) -> None:
    """Reverse the direction of a non-cyclic spline in place."""
    if spline.use_cyclic_u:
        return
    if spline.type == "BEZIER":
        _reverse_bezier_spline(spline)
    else:
        _reverse_poly_spline(spline)


def _reverse_bezier_spline(spline) -> None:
    points = list(spline.bezier_points)
    data = []
    for point in points:
        data.append({
            "co": point.co.copy(),
            # When the direction flips, the left handle becomes the right one.
            "handle_left": point.handle_right.copy(),
            "handle_right": point.handle_left.copy(),
            "handle_left_type": point.handle_right_type,
            "handle_right_type": point.handle_left_type,
            "hide": point.hide,
            "radius": point.radius,
            "select_control_point": point.select_control_point,
            "select_left_handle": point.select_right_handle,
            "select_right_handle": point.select_left_handle,
            "tilt": -point.tilt,
            "weight_softbody": point.weight_softbody,
        })

    data.reverse()

    for index, point in enumerate(points):
        item = data[index]
        point.co = item["co"]
        point.handle_left = item["handle_left"]
        point.handle_right = item["handle_right"]
        point.handle_left_type = item["handle_left_type"]
        point.handle_right_type = item["handle_right_type"]
        point.hide = item["hide"]
        point.radius = item["radius"]
        point.select_control_point = item["select_control_point"]
        point.select_left_handle = item["select_left_handle"]
        point.select_right_handle = item["select_right_handle"]
        point.tilt = item["tilt"]
        point.weight_softbody = item["weight_softbody"]


def _reverse_poly_spline(spline) -> None:
    points = list(spline.points)
    data = []
    for point in points:
        data.append({
            "co": point.co.copy(),
            "hide": point.hide,
            "radius": point.radius,
            "select": point.select,
            "tilt": -point.tilt,
            "weight": point.weight,
            "weight_softbody": point.weight_softbody,
        })

    data.reverse()

    for index, point in enumerate(points):
        item = data[index]
        point.co = item["co"]
        point.hide = item["hide"]
        point.radius = item["radius"]
        point.select = item["select"]
        point.tilt = item["tilt"]
        point.weight = item["weight"]
        point.weight_softbody = item["weight_softbody"]


# ============================================================
# Matching
# ============================================================
def active_vertex_indices(
    scalp_obj: bpy.types.Object,
    group_name: str = DEFAULT_SCALP_GROUP,
) -> list[int]:
    """
    Vertex indices that belong to the scalp vertex group.

    Membership is used (not the weight value), matching build_scalp_mask()
    and the way VaM treats the scalp mask.
    """
    if scalp_obj is None or scalp_obj.type != "MESH":
        raise HairExtractionError("头皮必须是网格对象")
    if not isinstance(scalp_obj.data, bpy.types.Mesh):
        raise HairExtractionError("头皮对象没有网格数据")

    group = scalp_obj.vertex_groups.get(group_name)
    if group is None:
        raise HairExtractionError(
            f'头皮对象缺少顶点组 "{group_name}"'
        )

    group_index = group.index
    result: list[int] = []
    for vertex in scalp_obj.data.vertices:
        for element in vertex.groups:
            if element.group == group_index:
                result.append(vertex.index)
                break
    return result


def nearest_unused(kd, co, used: set[int], total: int, start: int = 8):
    """
    Return (index, distance) of the nearest KDTree entry whose index is not
    in ``used``, or (None, None) when every entry is taken.
    """
    if total <= 0:
        return None, None

    k = min(max(1, int(start)), total)
    while True:
        for _, index, distance in kd.find_n(co, k):
            if index not in used:
                return index, distance
        if k >= total:
            return None, None
        k = min(total, k * 2)


def extract_strands(
    scalp_obj: bpy.types.Object,
    hair_obj: bpy.types.Object,
    group_name: str = DEFAULT_SCALP_GROUP,
    max_root_distance: float = DEFAULT_MAX_ROOT_DISTANCE,
) -> HairExtractionResult:
    """
    Match every active scalp vertex to exactly one hair strand.

    Matching uses both spline endpoints so strands whose root is on the
    wrong end are still found; the spline is reversed afterwards when the
    tip is the end closer to the scalp.  This keeps the export invariant:
    one strand per active scalp vertex, root near the scalp.
    """
    if hair_obj is None or hair_obj.type != "CURVE":
        raise HairExtractionError("发型必须是 Curve 对象")
    if not isinstance(hair_obj.data, bpy.types.Curve):
        raise HairExtractionError("发型对象没有 Curve 数据")

    scalp_vertices = active_vertex_indices(scalp_obj, group_name)
    if not scalp_vertices:
        raise HairExtractionError(
            f'顶点组 "{group_name}" 里没有顶点'
        )

    splines = list(hair_obj.data.splines)
    if not splines:
        raise HairExtractionError("发型里没有 spline")
    if len(splines) < len(scalp_vertices):
        raise HairExtractionError(
            f"发束数量 {len(splines)} 少于激活头皮顶点 "
            f"{len(scalp_vertices)}，无法做一对一匹配"
        )

    kd = KDTree(len(splines) * 2)
    entries = 0
    for spline_index, spline in enumerate(splines):
        root = spline_root_world(hair_obj, spline)
        tip = spline_tip_world(hair_obj, spline)
        if root is not None:
            kd.insert(root, spline_index)
            entries += 1
        if tip is not None and (root is None or (tip - root).length > 1e-9):
            kd.insert(tip, spline_index)
            entries += 1

    if entries == 0:
        raise HairExtractionError("所有 spline 都是空的")

    kd.balance()

    used: set[int] = set()
    assignments: list[tuple[int, int, float]] = []
    missing: list[int] = []

    for scalp_index in scalp_vertices:
        vertex_co = (
            scalp_obj.matrix_world
            @ scalp_obj.data.vertices[scalp_index].co
        )
        spline_index, distance = nearest_unused(
            kd, vertex_co, used, entries
        )
        if spline_index is None:
            missing.append(scalp_index)
            continue
        used.add(spline_index)
        assignments.append((scalp_index, spline_index, distance))

    if missing:
        raise HairExtractionError(
            f"{len(missing)} 个激活头皮顶点找不到未使用的发束"
            f"（例如 {missing[:8]}），请增加发束或减少头皮顶点"
        )

    warnings: list[str] = []
    too_far: list[tuple[int, int, float]] = []
    reverse_flags: list[bool] = []

    for scalp_index, spline_index, _ in assignments:
        spline = splines[spline_index]
        vertex_co = (
            scalp_obj.matrix_world
            @ scalp_obj.data.vertices[scalp_index].co
        )
        root = spline_root_world(hair_obj, spline)
        tip = spline_tip_world(hair_obj, spline)

        reverse = False
        near = root
        if (
            root is not None
            and tip is not None
            and not spline.use_cyclic_u
            and (tip - vertex_co).length < (root - vertex_co).length
        ):
            reverse = True
            near = tip

        reverse_flags.append(reverse)

        if near is not None:
            distance = (near - vertex_co).length
            if distance > max_root_distance:
                too_far.append((scalp_index, spline_index, distance))

    if too_far:
        longest = max(distance for _, _, distance in too_far)
        warnings.append(
            f"{len(too_far)} 根发束的 root 距离头皮超过 "
            f"{max_root_distance:.3f} m（最大 {longest:.3f} m），"
            "导出前请用 Set Spline Root 修正"
        )

    return HairExtractionResult(
        scalp_vertex_count=len(scalp_vertices),
        total_splines=len(splines),
        spline_indices=[
            spline_index for _, spline_index, _ in assignments
        ],
        assignments=assignments,
        reverse_flags=reverse_flags,
        warnings=warnings,
    )


def _copy_spline(source, curve):
    """Copy one spline (points/handles/settings) into ``curve``."""
    target = curve.splines.new(type=source.type)

    if source.type == "BEZIER":
        count = len(source.bezier_points)
        if count == 0:
            return target
        target.bezier_points.add(count - 1)
        for src, dst in zip(source.bezier_points, target.bezier_points):
            dst.co = src.co
            dst.handle_left = src.handle_left
            dst.handle_right = src.handle_right
            dst.handle_left_type = src.handle_left_type
            dst.handle_right_type = src.handle_right_type
            dst.radius = src.radius
            dst.tilt = src.tilt
    else:
        count = len(source.points)
        if count == 0:
            return target
        target.points.add(count - 1)
        for src, dst in zip(source.points, target.points):
            dst.co = src.co
            dst.radius = src.radius
            dst.tilt = src.tilt
            dst.weight = src.weight

    target.use_cyclic_u = source.use_cyclic_u
    target.resolution_u = source.resolution_u
    target.use_smooth = source.use_smooth

    if source.type == "NURBS":
        target.order_u = source.order_u
        target.use_endpoint_u = source.use_endpoint_u

    return target


def build_extracted_object(
    source_obj: bpy.types.Object,
    spline_indices: list[int],
    reverse_flags: list[bool] | None = None,
    suffix: str = "_extracted",
) -> bpy.types.Object:
    """
    Create a new object with only ``spline_indices``.

    Splines are copied into a fresh Curve datablock in the given order
    (which is the scalp vertex order produced by extract_strands), so the
    whole object stays editable and the operation is O(selected strands)
    instead of removing thousands of splines one by one.
    """
    if not spline_indices:
        raise HairExtractionError("没有可以分离的发束")

    source_curve = source_obj.data
    splines = list(source_curve.splines)
    selected = [splines[index] for index in spline_indices]
    if not selected:
        raise HairExtractionError("没有可以分离的发束")

    curve = bpy.data.curves.new(
        f"{source_curve.name}{suffix}",
        type="CURVE",
    )
    curve.dimensions = source_curve.dimensions
    curve.resolution_u = source_curve.resolution_u
    curve.render_resolution_u = source_curve.render_resolution_u
    curve.bevel_depth = source_curve.bevel_depth
    curve.bevel_resolution = source_curve.bevel_resolution
    curve.fill_mode = source_curve.fill_mode

    for material in source_curve.materials:
        curve.materials.append(material)

    for order, source_spline in enumerate(selected):
        target_spline = _copy_spline(source_spline, curve)
        if (
            reverse_flags is not None
            and order < len(reverse_flags)
            and reverse_flags[order]
        ):
            # Reverse only the copy; the source hair stays untouched.
            reverse_spline(target_spline)

    new_obj = source_obj.copy()
    new_obj.data = curve
    new_obj.name = f"{source_obj.name}{suffix}"

    for collection in source_obj.users_collection:
        collection.objects.link(new_obj)

    new_obj.animation_data_clear()

    return new_obj

import bpy

from .curve_tools import (
    resample_polyline,
    sample_spline_polyline,
)


# =========================================================================
# 1. Core algorithm: evenly spaced points along one spline
# =========================================================================
def get_resampled_coords_for_spline(spline, target_segments):
    """
    Return ``target_segments`` local-space points evenly spaced by arc
    length along the spline.

    BEZIER splines are evaluated through every segment (handles included)
    instead of using their control points, so resampling no longer
    flattens a curved strand into a straight line.
    """
    count = max(2, int(target_segments))
    points = sample_spline_polyline(spline)
    if len(points) < 2:
        return []

    total_length = 0.0
    for index in range(1, len(points)):
        total_length += (points[index] - points[index - 1]).length
    if total_length <= 1e-12:
        return []

    return resample_polyline(points, count)


# =========================================================================
# 2. Resample a whole curve object
# =========================================================================
def resample_curve_object(obj, target_segments):
    curve = obj.data

    # Record the new coordinates and closure state of each original spline.
    all_splines_new_data = []
    for spline in curve.splines:
        coords = get_resampled_coords_for_spline(spline, target_segments)
        if not coords:
            continue
        if spline.use_cyclic_u and len(coords) > 2:
            # The sampler closes the loop; a cyclic POLY spline must not
            # repeat its first point.
            coords = coords[:-1]
        all_splines_new_data.append({
            'coords': coords,
            'use_cyclic_u': spline.use_cyclic_u,
        })

    # Clear all splines first to avoid index conflicts.
    curve.splines.clear()

    # Recreate one POLY spline per strand.
    for spline_data in all_splines_new_data:
        coords = spline_data['coords']
        new_spline = curve.splines.new(type='POLY')

        # new() already creates one point, so only add N - 1 more.
        new_spline.points.add(len(coords) - 1)

        for idx, coord in enumerate(coords):
            new_spline.points[idx].co = (coord.x, coord.y, coord.z, 1.0)

        new_spline.use_cyclic_u = spline_data['use_cyclic_u']

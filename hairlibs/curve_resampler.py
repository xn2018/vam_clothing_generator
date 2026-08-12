import bpy
import mathutils

# =========================================================================
# 1. Core algorithm: Calculate the arc length of a single spline using equidistant sampling coordinates.
# =========================================================================
def get_resampled_coords_for_spline(spline, target_segments):
    """
    Receive a spline and return a list of coordinates sampled by target_segments. [(x, y, z), ...]
    """
    if target_segments < 1:
        return []
    
    # Obtain the set of coordinates of the original point
    eval_points = []
    if spline.type == 'BEZIER' and len(spline.bezier_points) > 0:
        # For BEZIER, the control points are simply obtained here (a higher density sampling can be used for smoother results).
        for bp in spline.bezier_points:
            eval_points.append(bp.co.copy())
    elif len(spline.points) > 0:
        for p in spline.points:
            eval_points.append(p.co.xyz.copy())
            
    if len(eval_points) < 2:
        return []

    # 1. Calculate cumulative arc length (Cumulative Arc Lengths)
    lengths = [0.0]
    total_length = 0.0
    for i in range(1, len(eval_points)):
        dist = (eval_points[i] - eval_points[i-1]).length
        total_length += dist
        lengths.append(total_length)
        
    if total_length == 0:
        return []

    # 2. Find interpolation points at equal intervals according to the target segment.
    is_cyclic = spline.use_cyclic_u
    num_points = target_segments if is_cyclic else (target_segments + 1)
    step = total_length / target_segments
    
    new_coords = []
    current_idx = 0
    
    for i in range(num_points):
        target_len = i * step
        if target_len >= total_length:
            new_coords.append(eval_points[-1].copy())
            continue
            
        while current_idx < len(lengths) - 1 and lengths[current_idx + 1] < target_len:
            current_idx += 1
            
        p1 = eval_points[current_idx]
        p2 = eval_points[current_idx + 1]
        l1 = lengths[current_idx]
        l2 = lengths[current_idx + 1]
        
        factor = (target_len - l1) / (l2 - l1) if (l2 - l1) > 0 else 0
        interpolated_p = p1.lerp(p2, factor)
        new_coords.append(interpolated_p)

    return new_coords


# =========================================================================
# 2. Resample logic for refactoring multi-segment
# =========================================================================
def resample_curve_object(obj, target_segments):
    curve = obj.data
    
    # Record the new coordinates and closure state of each original spline after resampling.
    all_splines_new_data = []
    for spline in curve.splines:
        coords = get_resampled_coords_for_spline(spline, target_segments)
        if coords:
            all_splines_new_data.append({
                'coords': coords,
                'use_cyclic_u': spline.use_cyclic_u
            })
            
    # Clear all splines in the original object (to prevent index conflicts or data corruption).
    curve.splines.clear()
    
    # Recreate the Spline for each Strand and write the data.
    for spline_data in all_splines_new_data:
        coords = spline_data['coords']
        new_spline = curve.splines.new(type='POLY')
        
        # The `new()` function creates a node that already has one node by default, so you only need to add (N - 1) nodes.
        new_spline.points.add(len(coords) - 1)
        
        for idx, coord in enumerate(coords):
            new_spline.points[idx].co = (coord.x, coord.y, coord.z, 1.0)
            
        new_spline.use_cyclic_u = spline_data['use_cyclic_u']
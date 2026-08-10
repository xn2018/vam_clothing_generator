import bpy
import mathutils

# =========================================================================
# 1. 核心算法：对单条 Spline 计算弧长等距采样坐标
# =========================================================================
def get_resampled_coords_for_spline(spline, target_segments):
    """
    接收一条 spline，返回按 target_segments 采样后的坐标列表 [(x, y, z), ...]
    """
    if target_segments < 1:
        return []
    
    # 获取原始点的坐标集合
    eval_points = []
    if spline.type == 'BEZIER' and len(spline.bezier_points) > 0:
        # 如果是 BEZIER，这里简单获取控制点（若想更平滑可依靠更高密度的采样）
        for bp in spline.bezier_points:
            eval_points.append(bp.co.copy())
    elif len(spline.points) > 0:
        for p in spline.points:
            eval_points.append(p.co.xyz.copy())
            
    if len(eval_points) < 2:
        return []

    # 1. 计算累积弧长 (Cumulative Arc Lengths)
    lengths = [0.0]
    total_length = 0.0
    for i in range(1, len(eval_points)):
        dist = (eval_points[i] - eval_points[i-1]).length
        total_length += dist
        lengths.append(total_length)
        
    if total_length == 0:
        return []

    # 2. 按目标 Segment 等间距寻找插值点
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
# 2. 重构多线段 Resample 逻辑
# =========================================================================
def resample_curve_object(obj, target_segments):
    curve = obj.data
    
    # 记录原先每条 Spline 重采样后的新坐标和闭合状态
    all_splines_new_data = []
    for spline in curve.splines:
        coords = get_resampled_coords_for_spline(spline, target_segments)
        if coords:
            all_splines_new_data.append({
                'coords': coords,
                'use_cyclic_u': spline.use_cyclic_u
            })
            
    # 清空原对象中的所有 Splines（防止索引冲突或数据错乱）
    curve.splines.clear()
    
    # 重新为每一条 Strand 创建 Spline 并写入数据
    for spline_data in all_splines_new_data:
        coords = spline_data['coords']
        new_spline = curve.splines.new(type='POLY')
        
        # new() 创建时默认已有 1 个点，因此只需要 add(N - 1) 个点
        new_spline.points.add(len(coords) - 1)
        
        for idx, coord in enumerate(coords):
            new_spline.points[idx].co = (coord.x, coord.y, coord.z, 1.0)
            
        new_spline.use_cyclic_u = spline_data['use_cyclic_u']
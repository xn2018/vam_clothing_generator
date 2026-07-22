import bpy
def check_uv_mirror_overlap(
    mesh: bpy.types.Mesh,
    epsilon=1e-5
):
    """
    Detect mirrored UV triangles.
    Conditions:
    1. UV bounding boxes overlap
    2. UV triangle area magnitude is similar
    3. UV winding direction opposite
    return:
    {
        "mirrored_overlap": int,
        "pairs": [
            {
                "a": triangle_id,
                "b": triangle_id,
                "area_a": float,
                "area_b": float
            }
        ]
    }
    """
    mesh.calc_loop_triangles()
    uv_layer = mesh.uv_layers.active
    if uv_layer is None:
        return {
            "mirrored_overlap":0,
            "pairs":[]
        }
    triangles=[]
    #
    # Collect UV triangles
    #
    for tri in mesh.loop_triangles:
        loops = tri.loops
        uv0 = uv_layer.data[
            loops[0] # type: ignore
        ].uv
        uv1 = uv_layer.data[
            loops[1] # type: ignore
        ].uv
        uv2 = uv_layer.data[
            loops[2] # type: ignore
        ].uv
        #
        # UV signed area
        #
        area = (
            (uv1.x-uv0.x)
            *
            (uv2.y-uv0.y)
            -
            (uv1.y-uv0.y)
            *
            (uv2.x-uv0.x)
        )
        #
        # Degenerate UV
        #
        if abs(area)<epsilon:
            continue
        bbox = (
            min(
                uv0.x,
                uv1.x,
                uv2.x
            ),
            min(
                uv0.y,
                uv1.y,
                uv2.y
            ),
            max(
                uv0.x,
                uv1.x,
                uv2.x
            ),
            max(
                uv0.y,
                uv1.y,
                uv2.y
            )
        )
        triangles.append(
            {
                "id":tri.index,
                "area":area,
                "bbox":bbox,
                "uv":(
                    uv0.copy(),
                    uv1.copy(),
                    uv2.copy()
                )
            }
        )
    #
    # Pair test
    #
    result=[]
    count=len(triangles)
    for i in range(count):
        a=triangles[i]
        for j in range(
            i+1,
            count
        ):
            b=triangles[j]
            #
            # bbox overlap
            #
            if (
                a["bbox"][2]
                <
                b["bbox"][0]
                or
                b["bbox"][2]
                <
                a["bbox"][0]
                or
                a["bbox"][3]
                <
                b["bbox"][1]
                or
                b["bbox"][3]
                <
                a["bbox"][1]
            ):
                continue
            #
            # same area
            #
            if abs(
                abs(a["area"])
                -
                abs(b["area"])
            ) > epsilon:
                continue
            #
            # opposite winding
            #
            if (
                a["area"]
                *
                b["area"]
                <
                0
            ):
                result.append(
                    {
                        "a":a["id"],
                        "b":b["id"],
                        "area_a":a["area"],
                        "area_b":b["area"],
                        "uv_a":a["uv"],
                        "uv_b":b["uv"]
                    }
                )
    return {
        "mirrored_overlap":
            len(result)
    }
def check_uv_winding(
    mesh: bpy.types.Mesh
):
    """
    Check Blender mesh UV winding.
    Compare 3D triangle winding vs UV triangle winding.
    """
    if mesh.uv_layers.active is None:
        raise RuntimeError("Mesh has no UV layer")
    uv_layer = mesh.uv_layers.active
    mesh.calc_loop_triangles()
    flipped = []
    total = 0
    degenerate = 0
    for tri in mesh.loop_triangles:
        # 1. 解包或直接转为 tuple 避开 bpy_prop_array 的下标类型检测
        v_idx0, v_idx1, v_idx2 = tri.vertices # type: ignore
        l_idx0, l_idx1, l_idx2 = tri.loops # type: ignore
        # 顶点 3D 坐标
        v0 = mesh.vertices[v_idx0].co
        v1 = mesh.vertices[v_idx1].co
        v2 = mesh.vertices[v_idx2].co
        # 3D normal
        e1 = v1 - v0
        e2 = v2 - v0
        normal = e1.cross(e2)
        # if normal.length_squared < 1e-12:
        #     degenerate += 1
        #     continue
        # UV 坐标
        uv0 = uv_layer.data[l_idx0].uv
        uv1 = uv_layer.data[l_idx1].uv
        uv2 = uv_layer.data[l_idx2].uv
        # UV determinant
        du1 = uv1.x - uv0.x
        dv1 = uv1.y - uv0.y
        du2 = uv2.x - uv0.x
        dv2 = uv2.y - uv0.y
        uv_det = du1 * dv2 - dv1 * du2
        # if abs(uv_det) < 1e-12:
        #     degenerate += 1
        #     continue
        # tangent basis
        tangent = e1.normalized()
        bitangent = normal.normalized().cross(tangent)
        # determinant in tangent space
        det = (
            e1.dot(tangent) * e2.dot(bitangent)
            - e2.dot(tangent) * e1.dot(bitangent)
        )
        total += 1
        if det * uv_det < 0:
            info = {
                "id":tri.index,
                # Blender loop index
                "loops":
                (
                    l_idx0,
                    l_idx1,
                    l_idx2
                ),
                # vertex index
                "vertices":
                (
                    v_idx0,
                    v_idx1,
                    v_idx2
                )
            }
            flipped.append(info)
    ratio = len(flipped) / total if total else 0
    return {
        "total": total,
        "degenerate": degenerate,
        "flipped_count": len(flipped),
        "ratio": ratio,
        "filpped_triangles": flipped
    }
def triangle_orientation_3d(
    p0,
    p1,
    p2
):
    n=(p1-p0).cross(
        p2-p0
    )
    ax=max(
        range(3),
        key=lambda i:abs(n[i])
    )
    if ax==0:
        # project YZ
        return (
            (p1.y-p0.y)*(p2.z-p0.z)
            -
            (p1.z-p0.z)*(p2.y-p0.y)
        )
    elif ax==1:
        # project XZ
        return (
            (p1.x-p0.x)*(p2.z-p0.z)
            -
            (p1.z-p0.z)*(p2.x-p0.x)
        )
    else:
        # project XY
        return (
            (p1.x-p0.x)*(p2.y-p0.y)
            -
            (p1.y-p0.y)*(p2.x-p0.x)
        )
from typing import cast
from mathutils import Vector

from wrap.wrap_types import DAZMeshData
def check_uv_winding(
    mesh_data: DAZMeshData
):
    """
    Detect inverted UV triangles
    return:
        {
            "total":int,
            "flipped":int,
            "ratio":float
        }
    """
    flipped=0
    total=0
    vertices = mesh_data.base_vertices
    triangles = mesh_data.base_triangles
    uvs = mesh_data.uv_vertices
    for i in range(
        0,
        len(triangles),
        3
    ):
        a=triangles[i]
        b=triangles[i+1]
        c=triangles[i+2]
        #
        # 3D normal
        #
        p1=vertices[a]
        p2=vertices[b]
        p3=vertices[c]
        normal3d=cast(Vector,(p2-p1).cross(p3-p1))
        #
        # UV normal
        #
        uv1=uvs[a]
        uv2=uvs[b]
        uv3=uvs[c]
        uv_cross=(
            (uv2-uv1).x *
            (uv3-uv1).y
            -
            (uv2-uv1).y *
            (uv3-uv1).x
        )
        if (
            normal3d.length_squared
            <
            1e-12
        ):
            continue
        total+=1
        if (
            normal3d.z * uv_cross
            <
            0
        ):
            flipped+=1
    ratio=0
    if total:
        ratio=flipped/total
    return {
        "total":total,
        "flipped":flipped,
        "ratio":ratio
    }
def detect_uv_overlap(
    mesh_data,
    epsilon=1e-5
):
    uv_map={}
    overlap=0
    uvs=mesh_data.uv_vertices
    for i,uv in enumerate(uvs):
        key=(
            round(uv.x/epsilon),
            round(uv.y/epsilon)
        )
        if key in uv_map:
            overlap+=1
        else:
            uv_map[key]=i
    return overlap
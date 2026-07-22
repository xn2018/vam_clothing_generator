from mathutils import Vector
from typing import Optional, cast

from ..wrap.DeriveMeshes import recover_vertex_normal
from .find_nearest_triangle import find_nearest_triangle
from ..wrap.wrap_types import (
    WrapInputVertex,
    SkinWrapVertex,
    DAZMeshData
)
EPS = 1e-12
def calculate_skinwrap_vertex(
    wrap_vertex:WrapInputVertex,
    clothing_obj:DAZMeshData,
    local_matrix,
    normal_matrix,
    anchor_only:bool=False,
    wrap_check_normals:bool=False,
    max_wrap_distance:float=1.0,
)->tuple[SkinWrapVertex|None,dict]:
    empty_count={
        "tri":0,
        "distance":0,
        "tangent1":0,
        "normal":0,
        "tangent2":0,
        "wrap_normal":0
    }
    empty_result=lambda:SkinWrapVertex(
        closestTriangle=-1,
        Vertex1=-1,
        Vertex2=-1,
        Vertex3=-1,
        surfaceNormalProjection=0.0,
        surfaceTangent1Projection=0.0,
        surfaceTangent2Projection=0.0,
        surfaceNormalWrapNormalDot=0.0,
        surfaceTangent1WrapNormalDot=0.0,
        surfaceTangent2WrapNormalDot=0.0
    )
    ##################################################
    # Position
    ##################################################
    local_pos = (
        local_matrix
        @
        wrap_vertex.co
    )
    ##################################################
    # Normal
    ##################################################
    wrap_normal = (
        normal_matrix
        @
        wrap_vertex.normal
    )
    if wrap_normal.length_squared < EPS:
        empty_count["wrap_normal"] += 1
        recovered = recover_vertex_normal(
            wrap_vertex.index,
            clothing_obj.uv_triangles,
            clothing_obj.base_surface_normals
        )
        if recovered:
            wrap_normal = recovered
        else:
            raise RuntimeError(
                f"Cannot recover normal {wrap_vertex.index}"
            )
    wrap_normal.normalize()
    ##################################################
    # Find Triangle
    ##################################################
    tri = find_nearest_triangle(
        local_pos,
        wrap_normal,
        anchor_only=anchor_only,
        check_normals=wrap_check_normals
    )
    if tri is None:
        empty_count["tri"] += 1
        return (
            empty_result(),
            empty_count
        )
    ##################################################
    # Distance
    ##################################################
    distance = (
        local_pos -
        tri.center
    ).length
    if distance > max_wrap_distance:
        empty_count["distance"] += 1
        return (
            empty_result(),
            empty_count
        )
    ##################################################
    # DAZ reorder
    ##################################################
    v1 = tri.vertex1
    v2 = tri.vertex2
    v3 = tri.vertex3
    p1 = tri.v1
    p2 = tri.v2
    p3 = tri.v3
    center = (
        p1+p2+p3
    ) / 3.0
    ##################################################
    # tangent1
    ##################################################
    tangent1 = (
        center-p1
    )
    if tangent1.length_squared < EPS:
        empty_count["tangent1"] += 1
        return (
            empty_result(),
            empty_count
        )
    ##################################################
    # normal
    ##################################################
    normal = tri.normal.copy()
    if normal.length_squared < EPS:
        empty_count["normal"] += 1
        return (
            empty_result(),
            empty_count
        )
    ##################################################
    # tangent2
    ##################################################
    tangent2 = cast(
        Vector,
        tangent1.cross(normal)
    )
    if tangent2.length_squared < EPS:
        empty_count["tangent2"] += 1
        return (
            empty_result(),
            empty_count
        )
    ##################################################
    # Projection
    ##################################################
    delta = (
        local_pos-p1
    )
    tangent1_len2 = (
        tangent1.length_squared
    )
    tangent2_len2 = (
        tangent2.length_squared
    )
    normal_len2 = (
        normal.length_squared
    )
    normal_projection = (
        delta.dot(normal)
        /
        normal_len2
    )
    tangent1_projection = (
        delta.dot(tangent1)
        /
        tangent1_len2
    )
    tangent2_projection = (
        delta.dot(tangent2)
        /
        tangent2_len2
    )
    ##################################################
    # Result
    ##################################################
    result = SkinWrapVertex(
        closestTriangle=
            tri.original_triangle_id,
        Vertex1=v1,
        Vertex2=v2,
        Vertex3=v3,
        surfaceNormalProjection=
            float(normal_projection),
        surfaceTangent1Projection=
            float(tangent1_projection),
        surfaceTangent2Projection=
            float(tangent2_projection),
        surfaceNormalWrapNormalDot=
            float(
                wrap_normal.dot(normal)
            ),
        surfaceTangent1WrapNormalDot=
            float(
                wrap_normal.dot(tangent1)
                /
                tangent1_len2
            ),
        surfaceTangent2WrapNormalDot=
            float(
                wrap_normal.dot(tangent2)
                /
                tangent2_len2
            )
    )
    return (
        result,
        empty_count
    )
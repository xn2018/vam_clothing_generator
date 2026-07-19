from dataclasses import dataclass
import math
EPS = 1e-12
# ============================================================
# Vector Math
# ============================================================
def add(a,b):
    return (
        a[0]+b[0],
        a[1]+b[1],
        a[2]+b[2],
    )
def sub(a,b):
    return (
        a[0]-b[0],
        a[1]-b[1],
        a[2]-b[2],
    )
def mul(a,s):
    return (
        a[0]*s,
        a[1]*s,
        a[2]*s,
    )
def dot(a,b):
    return (
        a[0]*b[0]
        +
        a[1]*b[1]
        +
        a[2]*b[2]
    )
def cross(a,b):
    return (
        a[1]*b[2]-a[2]*b[1],
        a[2]*b[0]-a[0]*b[2],
        a[0]*b[1]-a[1]*b[0]
    )
def length_sq(v):
    return dot(v,v)
def length(v):
    return math.sqrt(
        length_sq(v)
    )
def normalize(v):
    l2=length_sq(v)
    if l2<EPS:
        return None
    inv=1.0/math.sqrt(l2)
    return (
        v[0]*inv,
        v[1]*inv,
        v[2]*inv
    )
# ============================================================
# Matrix
# Blender Matrix 4x4 -> tuple
# ============================================================
def transform_point(m,p):
    x,y,z=p
    return (
        m[0][0]*x+
        m[0][1]*y+
        m[0][2]*z+
        m[0][3],
        m[1][0]*x+
        m[1][1]*y+
        m[1][2]*z+
        m[1][3],
        m[2][0]*x+
        m[2][1]*y+
        m[2][2]*z+
        m[2][3],
    )
def transform_vector(m,v):
    x,y,z=v
    return (
        m[0][0]*x+
        m[0][1]*y+
        m[0][2]*z,
        m[1][0]*x+
        m[1][1]*y+
        m[1][2]*z,
        m[2][0]*x+
        m[2][1]*y+
        m[2][2]*z,
    )
# ============================================================
# Triangle Search
# ============================================================
def distance_sq_point_triangle_center(
        p,
        tri
):
    d=sub(
        p,
        tri.center
    )
    return length_sq(d)

# ============================================================
# find_nearest_triangle_worker
# ============================================================
def find_nearest_triangle_worker(
    bvh_data,
    pos,
    normal,
    anchor_only=False
):
    if anchor_only:
        triangles = (
            bvh_data.anchor_triangles
        )
    else:
        triangles = (
            bvh_data.triangles
        )
    nearest=None
    nearest_dist=999999999
    for tri in triangles:
        cx,cy,cz = tri.center
        dx=pos[0]-cx
        dy=pos[1]-cy
        dz=pos[2]-cz
        d2=(
            dx*dx+
            dy*dy+
            dz*dz
        )
        if d2 < nearest_dist:
            nearest_dist=d2
            nearest=tri
    return nearest
# ============================================================
# Empty
# ============================================================
def empty_result():
    return {
        "closestTriangle":-1,
        "Vertex1":-1,
        "Vertex2":-1,
        "Vertex3":-1,
        "surfaceNormalProjection":0.0,
        "surfaceTangent1Projection":0.0,
        "surfaceTangent2Projection":0.0,
        "surfaceNormalWrapNormalDot":1.0,
        "surfaceTangent1WrapNormalDot":0.0,
        "surfaceTangent2WrapNormalDot":0.0,
    }
# ============================================================
# Main Worker
# ============================================================
def calculate_skinwrap_matrix_worker(
        wrap_vertices,
        bvh_data,
        local_matrix,
        normal_matrix,
        anchor_only=False,
        max_wrap_distance=1.0,
        progress_callback=None
):
    results=[]
    total=len(wrap_vertices)
    for index,wrap_vertex in enumerate(wrap_vertices):
        if progress_callback:
            progress_callback(
                index,
                total
            )
        #
        # Position
        #
        local_pos=transform_point(
            local_matrix,
            wrap_vertex.co
        )
        #
        # Normal
        #
        wrap_normal=transform_vector(
            normal_matrix,
            wrap_vertex.normal
        )
        wrap_normal=normalize(
            wrap_normal
        )
        if wrap_normal is None:
            raise RuntimeError(
                f"Invalid wrap normal {wrap_vertex.index}"
            )
        #
        # Triangle
        #
        tri = find_nearest_triangle_worker(
            bvh_data,
            local_pos,
            wrap_normal,
            anchor_only
        )
        if tri is None:
            results.append(
                empty_result()
            )
            continue
        #
        # Distance
        #
        distance=length(
            sub(
                local_pos,
                tri.center
            )
        )
        if distance>max_wrap_distance:
            results.append(
                empty_result()
            )
            continue
        #
        # DAZ reorder
        #
        p1=tri.v1
        center=mul(
            add(
                add(
                    tri.v1,
                    tri.v2
                ),
                tri.v3
            ),
            1.0/3.0
        )
        tangent1=sub(
            center,
            p1
        )
        if length_sq(tangent1)<EPS:
            results.append(
                empty_result()
            )
            continue
        normal=tri.normal
        if length_sq(normal)<EPS:
            results.append(
                empty_result()
            )
            continue
        tangent2=cross(
            tangent1,
            normal
        )
        if length_sq(tangent2)<EPS:
            results.append(
                empty_result()
            )
            continue
        delta=sub(
            local_pos,
            p1
        )
        normal_projection=(
            dot(delta,normal)
            /
            length_sq(normal)
        )
        tangent1_projection=(
            dot(delta,tangent1)
            /
            length_sq(tangent1)
        )
        tangent2_projection=(
            dot(delta,tangent2)
            /
            length_sq(tangent2)
        )
        results.append({
            "closestTriangle":
                tri.original_triangle_id,
            "Vertex1":
                tri.vertex1,
            "Vertex2":
                tri.vertex2,
            "Vertex3":
                tri.vertex3,
            "surfaceNormalProjection":
                float(normal_projection),
            "surfaceTangent1Projection":
                float(tangent1_projection),
            "surfaceTangent2Projection":
                float(tangent2_projection),
            "surfaceNormalWrapNormalDot":
                float(
                    dot(
                        wrap_normal,
                        normal
                    )
                ),
            "surfaceTangent1WrapNormalDot":
                float(
                    dot(
                        wrap_normal,
                        tangent1
                    )
                    /
                    length_sq(tangent1)
                ),
            "surfaceTangent2WrapNormalDot":
                float(
                    dot(
                        wrap_normal,
                        tangent2
                    )
                    /
                    length_sq(tangent2)
                )
        })
    return results
from typing import cast
import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree
from .daz_hair_data import DAZHairData
#=============================
# 1.find_hair_root
#=============================
def find_hair_root(clothing_hair_obj):
    """
    Find hair roots from curve splines.
    Each spline first point is treated as root.
    return:
        [
            {
              spline_index:int,
              position:Vector,
              spline:Object
            }
        ]
    """
    roots=[]
    _curve=clothing_hair_obj.data
    for index,spline in enumerate(_curve.splines):
        if spline.type == 'BEZIER':
            if len(spline.bezier_points)==0:
                continue
            p=spline.bezier_points[0]
            co=p.co
        else:
            if len(spline.points)==0:
                continue
            p=spline.points[0]
            co=Vector(
                (
                    p.co.x,
                    p.co.y,
                    p.co.z
                )
            )
        # object local -> world
        world_pos = (
            clothing_hair_obj.matrix_world
            @
            co
        )
        roots.append(
            {
                "spline_index":index,
                "position":world_pos,
                "spline":spline
            }
        )
    return roots
#=============================
# 2.find_nearest_scalp_vertex
#=============================
def find_nearest_scalp_vertex(
        hair_roots,
        genesis_obj:bpy.types.Object,
        group_name="scalp"
):
    mesh=cast(bpy.types.Mesh,genesis_obj.data)
    vg=genesis_obj.vertex_groups.get(
        group_name
    )
    if vg is None:
        raise Exception(
            f"Missing {group_name}"
        )
    scalp_vertices=[]
    for v in mesh.vertices:
        for g in v.groups:
            if g.group==vg.index:
                scalp_vertices.append(
                    v.index
                )
                break
    if not scalp_vertices:
        raise Exception(
            "Empty scalp group"
        )
    kd=KDTree(
        len(scalp_vertices)
    )
    for vid in scalp_vertices:
        co=(
            genesis_obj.matrix_world
            @
            mesh.vertices[vid].co
        )
        kd.insert(
            co,
            vid
        )
    kd.balance()
    result=[]
    for root in hair_roots:
        co=root["position"]
        nearest=kd.find(
            co
        )
        result.append(
            {
                "spline_index":
                    root["spline_index"],
                "scalp_index":
                    nearest[1],
                "distance":
                    nearest[2],
                "position":
                    co
            }
        )
    return result
def sample_spline(
        obj,
        spline,
        segments
):
    """
    Sample Blender Curve Spline
    Return world-space points
    """
    if segments < 2:
        raise ValueError(
            "segments must >= 2"
        )
    points=[]
    # =================================================
    # Bezier
    # =================================================
    if spline.type == 'BEZIER':
        bp = spline.bezier_points
        count = len(bp)
        if count < 2:
            return points
        for i in range(segments):
            t = (
                i /
                float(segments-1)
            )
            # convert global t to segment
            ft = t * (count-1)
            seg = min(
                int(ft),
                count-2
            )
            local_t = (
                ft-seg
            )
            p0 = bp[seg]
            p1 = bp[seg+1]
            co = (
                (1-local_t)**3 * p0.co
                +
                3*(1-local_t)**2*local_t *
                (
                    p0.co +
                    p0.handle_right -
                    p0.co
                )
                +
                3*(1-local_t)*local_t**2 *
                (
                    p1.co -
                    (
                        p1.co -
                        p1.handle_left
                    )
                )
                +
                local_t**3*p1.co
            )
            points.append(
                obj.matrix_world @ co
            )
    # =================================================
    # Poly
    # =================================================
    elif spline.type == 'POLY':
        p=spline.points
        count=len(p)
        if count < 2:
            return points
        for i in range(segments):
            t=(
                i /
                float(segments-1)
            )
            ft=t*(count-1)
            idx=min(
                int(ft),
                count-2
            )
            lt=ft-idx
            a=Vector(
                (
                    p[idx].co.x,
                    p[idx].co.y,
                    p[idx].co.z
                )
            )
            b=Vector(
                (
                    p[idx+1].co.x,
                    p[idx+1].co.y,
                    p[idx+1].co.z
                )
            )
            co=a.lerp(
                b,
                lt
            )
            points.append(
                obj.matrix_world @ co
            )
    else:
        raise RuntimeError(
            f"Unsupported spline type: {spline.type}"
        )
    return points
#=============================
# 3.convert_to_dazhair
#=============================
# =========================================================
# Convert Blender Curve -> DAZHairData
# =========================================================
def convert_to_dazhair(
        clothing_hair_obj,
        root_mapping,
        segments=16
):
    """
    Convert Blender curve hair into
    RuntimeHairGeometryCreator format.
    Parameters
    ----------
    clothing_hair_obj:
        Blender Curve object
    root_mapping:
        result from find_nearest_scalp_vertex()
        [
            {
                spline_index:int,
                scalp_index:int,
                distance:float,
                position:Vector
            }
        ]
    segments:
        points per hair strand
    Return
    ------
    DAZHairData
    """
    data = DAZHairData()
    data.name = (
        clothing_hair_obj.name
    )
    data.segments = segments
    curve = (
        clothing_hair_obj.data
    )
    # -------------------------------------------------
    # build spline -> scalp map
    # -------------------------------------------------
    scalp_map={}
    for item in root_mapping:
        scalp_map[
            item["spline_index"]
        ] = item["scalp_index"]
    # -------------------------------------------------
    # build strands
    # -------------------------------------------------
    for index, spline in enumerate(
            curve.splines
    ):
        #
        # sample curve
        #
        points = sample_spline(
            clothing_hair_obj,
            spline,
            segments
        )
        #
        # find scalp vertex
        #
        scalp_index = (
            scalp_map.get(
                index,
                -1
            )
        )
        #
        # create strand
        #
        data.add_strand(
            points,
            scalp_index
        )
        #
        # root -> scalp
        #
        data.hair_root_to_scalp_indices.append(
            scalp_index
        )
    # -------------------------------------------------
    # geometry build
    # -------------------------------------------------
    data.calculate_segment_length()
    data.build_vertex_buffer()
    # -------------------------------------------------
    # physics
    # -------------------------------------------------
    data.build_rigidities()
    #
    # distance joints
    #
    if hasattr(
        data,
        "build_distance_joints"
    ):
        data.build_distance_joints()
    #
    # point joints
    #
    if hasattr(
        data,
        "build_point_joints"
    ):
        data.build_point_joints()
    #
    # render index
    #
    if hasattr(
        data,
        "build_indices"
    ):
        data.build_indices()
    #
    # render particles
    #
    if hasattr(
        data,
        "build_render_particles"
    ):
        data.build_render_particles()
    # -------------------------------------------------
    # validation
    # -------------------------------------------------
    errors = data.validate()
    if errors:
        raise RuntimeError(
            "DAZHair validation failed:\n"
            +
            "\n".join(errors)
        )
    return data
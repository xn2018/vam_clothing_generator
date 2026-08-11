from dataclasses import dataclass
from typing import cast
import bpy
from mathutils import Vector
from .daz_hair_data import DAZHairStrand
@dataclass
class DAZHairRoot:
    index:int
    position:Vector
    source:object
#=============================
# 1.find_hair_root
#=============================
def find_hair_root(
    scalp_obj:bpy.types.Object,
    eval_psys:bpy.types.ParticleSystem|None
)->list[DAZHairRoot]:
    """
    Find hair roots from Blender Particle Hair.
    Particle:
        particle
            |
            + hair_keys[0]
                    |
                    + root position
    return:
        [
            {
                particle_index:int,
                position:Vector,
                particle:Object
            }
        ]
    """
    roots=[]
    if eval_psys is None:
        raise Exception("eval_psys is None, try to using curve mode")
    for index,particle in enumerate(eval_psys.particles):
        #
        # particle hair keys
        #
        keys = particle.hair_keys
        if len(keys)==0:
            print("no hair keys found!")
            continue
        #
        # first key = hair root
        #
        root_local = keys[0].co
        #
        # object local -> world
        #
        root_world = (scalp_obj.matrix_world@root_local)
        roots.append(
            DAZHairRoot(
                index=index,
                position=root_world,
                source=particle
            )
        )
    return roots
def find_curve_hair_root(
        hair_obj:bpy.types.Object
)->list[DAZHairRoot]:
    """
    Find hair roots from Blender Curve Hair.
    Curve:
        spline
            |
            +-- first control point
                    |
                    + root position
    Support:
        BEZIER
        POLY
        NURBS
    return:
        [
            {
                spline_index:int,
                position:Vector,
                spline:Spline
            }
        ]
    """
    if hair_obj.type != "CURVE":
        raise TypeError(
            "hair_obj must be Curve"
        )
    roots=[]
    curve = cast(bpy.types.Curve, hair_obj.data)
    for index,spline in enumerate(
        curve.splines
    ):
        root_local=None
        ####################################
        # BEZIER
        ####################################
        if spline.type == "BEZIER":
            if len(
                spline.bezier_points
            ) == 0:
                continue
            root_local = (
                spline.bezier_points[0].co
            )
        ####################################
        # POLY / NURBS
        ####################################
        elif (
            spline.type == "POLY"
            or
            spline.type == "NURBS"
        ):
            if len(
                spline.points
            ) == 0:
                continue
            p = spline.points[0]
            #
            # Curve point is Vector4
            # x,y,z,w
            #
            root_local = Vector(
                (
                    p.co.x,
                    p.co.y,
                    p.co.z
                )
            )
        else:
            print(
                "Unsupported spline type:",
                spline.type
            )
            continue
        ####################################
        # local -> world
        ####################################
        root_world = (
            hair_obj.matrix_world
            @
            root_local
        )
        roots.append(
            DAZHairRoot(
                index=index,
                position=root_world,
                source=spline
            )
        )
    return roots

#==================================
# resample_particle_strand
#==================================
def resample_particle_strand(
        vertices,
        weights,
        count
):
    if len(vertices)<2:
        return vertices,weights
    result_vertices=[]
    result_weights=[]
    total=len(vertices)-1
    for i in range(count):
        t=i/(count-1)
        pos=t*total
        index=int(pos)
        factor=pos-index
        if index>=total:
            result_vertices.append(
                vertices[-1]
            )
            result_weights.append(
                weights[-1]
            )
        else:
            p1=vertices[index]
            p2=vertices[index+1]
            result_vertices.append(
                p1.lerp(
                    p2,
                    factor
                )
            )
            w1=weights[index]
            w2=weights[index+1]
            result_weights.append(
                w1+(w2-w1)*factor
            )
    return (
        result_vertices,
        result_weights
    )

#======================================
# convert_particle_hair_to_dazhair
#======================================
def convert_particle_hair_to_dazhair(
        hair_psys:bpy.types.ParticleSystem | None,
        scalp_obj:bpy.types.Object,
        root_mapping:list[int],
        segments:int=5
    ):
    """
    Convert Blender Particle Hair
    to DAZHairData
    Blender Particle Hair
        |
        +-- particle
              |
              +-- hair_keys
                    |
                    +-- co
                    +-- weight
    VaM RuntimeHairGeometryCreator
        |
        +-- strands
              |
              +-- vertices
              +-- rigidities
    """
    from .daz_hair_data import DAZHairData
    if hair_psys is None:
        raise RuntimeError(
            "Particle system is None"
        )
    data=DAZHairData()
    #
    # segments
    #
    data.segments = len(hair_psys.particles[0].hair_keys) - 1
    #
    # scalp vertex count
    #
    scalp_mesh = cast(
        bpy.types.Mesh,
        scalp_obj.data
    )
    data.set_scalp_vertex_count(
        len(
            scalp_mesh.vertices
        )
    )
    #
    # create empty strands
    #
    data.init_strands()
    particles = hair_psys.particles
    if len(root_mapping)!=len(particles):
        raise RuntimeError(
            f"Root mapping {len(root_mapping)} "
            f"!= particles {len(particles)}"
        )
    used_scalp=set()
    #
    # particle -> strand
    #
    for particle_index,particle in enumerate(
        particles
    ):
        scalp_index = root_mapping[
            particle_index
        ]
        #
        # invalid root
        #
        if scalp_index < 0:
            continue
        #
        # avoid duplicate scalp strand
        #
        if scalp_index in used_scalp:
            print(
                "[Hair] duplicate scalp:",
                scalp_index
            )
            continue
        used_scalp.add(
            scalp_index
        )
        vertices=[]
        weights=[]
        #
        # particle hair keys
        #
        for key in particle.hair_keys:
            #
            # particle object local
            # ->
            # world
            #
            world_pos = (
                scalp_obj.matrix_world
                @
                key.co
            )
            vertices.append(
                world_pos
            )
            weights.append(
                float(
                    key.weight
                )
            )
        if len(vertices)<2:
            continue
        #
        # resample to VaM segments
        #
        if len(vertices)!=segments:
            vertices,weights = (
                resample_particle_strand(
                    vertices,
                    weights,
                    segments
                )
            )
        #
        # force root rigidity
        #
        if weights:
            weights[0]=1.0
        #
        # add strand
        #
        data.add_strand(
            scalp_index=scalp_index,
            vertices=vertices,
            weights=weights
        )
    #
    # validate
    #
    for strand in data.strands:
        if not strand.vertices:
            continue
        if len(strand.vertices)!=segments:
            raise RuntimeError(
                "Invalid strand segment count"
            )
        if len(strand.vertices)!=len(strand.weights):
            raise RuntimeError(
                "Vertex/weight mismatch"
            )
    #
    # calculate length
    #
    data.calculate_segment_length()
    #
    # painted rigidity
    #
    data.build_rigidities()
    #
    # RuntimeHairGeometryCreator mapping
    #
    data.hair_root_to_scalp_indices = [
        strand.scalp_index
        for strand in data.strands
        if strand.vertices
    ]
    print(
        "[Hair] strands:",
        len(data.hair_root_to_scalp_indices)
    )
    print(
        "[Hair] vertices:",
        len(data.vertices)
    )
    print(
        "[Hair] rigidities:",
        len(data.rigidities)
    )
    return data
def convert_strands_to_dazhair(
        strands:list[DAZHairStrand],
        scalp_obj:bpy.types.Object,
        segments:int
):
    from .daz_hair_data import DAZHairData
    data=DAZHairData()
    #
    # scalp count
    #
    scalp_mesh=cast(
        bpy.types.Mesh,
        scalp_obj.data
    )
    data.set_scalp_vertex_count(
        len(
            scalp_mesh.vertices
        )
    )
    data.segments=segments
    data.init_strands()
    used_scalp=set()
    for strand in strands:
        scalp_index=(
            strand.scalp_index
        )
        if scalp_index < 0:
            continue
        #
        # 防止重复root
        #
        if scalp_index in used_scalp:
            print(
                "[Hair] duplicate scalp:",
                scalp_index
            )
            continue
        used_scalp.add(
            scalp_index
        )
        vertices=strand.vertices
        weights=strand.weights
        if len(vertices)!=segments:
            vertices,weights = (
                resample_particle_strand(
                    vertices,
                    weights,
                    segments
                )
            )
        #
        # root必须固定
        #
        if weights:
            weights[0]=1.0
        data.add_strand(
            scalp_index=scalp_index,
            vertices=vertices,
            weights=weights
        )
    #
    # Runtime segment length
    #
    data.calculate_segment_length()
    #
    # painted rigidity
    #
    data.build_rigidities()
    #
    # mapping
    #
    data.hair_root_to_scalp_indices=[
        s.scalp_index
        for s in data.strands
        if s.vertices
    ]
    print(
        "[Hair] strands:",
        len(
            data.hair_root_to_scalp_indices
        )
    )
    print(
        "[Hair] vertices:",
        len(data.vertices)
    )
    print(
        "[Hair] rigidities:",
        len(data.rigidities)
    )
    return data
from bpy.types import ParticleSystem,Object
from .daz_hair_data import DAZHairStrand
class ParticleHairImporter:
    def __init__(
        self,
        obj: Object,
        eval_psys: ParticleSystem | None
    ):
        self.obj = obj
        self.psys = eval_psys
        self.segments = 0
    def extract(self):
        if self.psys is None:
            raise RuntimeError("No particle system")
        result=[]
        segment_set=set()
        for index,p in enumerate(
            self.psys.particles
        ):
            keys=p.hair_keys
            if len(keys)<2:
                continue
            segment_set.add(
                len(keys)
            )
            vertices=[]
            weights=[]
            for key in keys:
                world_pos = (
                    self.obj.matrix_world
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
            strand=DAZHairStrand()
            #
            # Blender particle index
            # == scalp vertex index
            #
            strand.scalp_index=index
            strand.root=vertices[0]
            strand.vertices=vertices
            strand.weights=weights
            result.append(
                strand
            )
        if len(segment_set)>1:
            print(
                "[Hair] Warning different segments:",
                segment_set
            )
        if segment_set:
            self.segments=max(
                segment_set
            )
        return result
from .daz_hair_data import DAZHairStrand


class ParticleHairImporter:
    def __init__(self,obj):
        self.obj=obj
        self.psys=obj.particle_systems.active
        self.segments=0
    def extract(self):
        result=[]
        segment_set=set()
        for index,p in enumerate(
            self.psys.particles
        ):
            vertices=[]
            weights=[]
            key_count=len(
                p.hair_keys
            )
            segment_set.add(
                key_count
            )
            for key in p.hair_keys:
                pos=(
                    self.obj.matrix_world
                    @
                    key.co
                )
                vertices.append(
                    pos
                )
                weights.append(
                    key.weight
                )
            if len(vertices)<2:
                continue
            result.append(
                DAZHairStrand(
                    scalp_index=index,
                    root=vertices[0],
                    vertices=vertices,
                    weights=weights
                )
            )
        #
        # check segments
        #
        if len(segment_set)>1:
            print(
                "Warning: particle strands have different key count:",
                segment_set
            )
        #
        # use first detected count
        #
        if segment_set:
            self.segments=max(
                segment_set
            )
        return result
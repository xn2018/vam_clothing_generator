from dataclasses import dataclass, field
from mathutils import Vector
@dataclass
class DAZHairStrand:
    """
    One hair strand.
    Equivalent to RuntimeHairGeometryCreator.Strand
    """
    scalp_index: int = -1
    # local strand points
    vertices: list = field(default_factory=list)
    root: Vector | None = None
    vertex_offset:int=0
    def add_point(self,co):
        v=Vector(co)
        if self.root is None:
            self.root=v
        self.vertices.append(v)
    @property
    def length(self):
        if len(self.vertices) < 2:
            return 0
        total = 0
        for i in range(len(self.vertices)-1):
            total += (
                self.vertices[i+1]
                -
                self.vertices[i]
            ).length
        return total
@dataclass
class DAZHairData:
    """
    Intermediate hair format.
    Blender Curve Hair
            |
            v
       DAZHairData
            |
            v
       VAM RuntimeHairGeometryCreator
    """
    # ==========================
    # scalp mask
    # ==========================
    scalp_provider_name:str="Genesis2Female"
    scalp_mask_name:str="scalp"
    scalp_mask:list=field(default_factory=list)
    scalp_indices = []
    strands_mask:list=field(default_factory=list)
    scalp_vertex_count:int=0
    runtime_strands:list = field(default_factory=list)
    # ==========================
    # basic geometry
    # ==========================
    name:str = "DAZHair"
    material_name:str="Main"
    # points per strand
    segments:int = 16
    # distance between points
    segment_length:float = 0.01
    # ==========================
    # strand data
    # ==========================
    strands:list = field(default_factory=list)
    # flattened vertices
    vertices:list = field(default_factory=list)
    # scalp vertex -> hair root
    hair_root_to_scalp_indices:list = field(default_factory=list)
    # root mapping
    hair_root_positions:list=field(
        default_factory=list
    )
    # point_joints
    point_joints:list = field(
        default_factory=list
    )
    # distance_joints
    distance_joints:list = field(default_factory=list)
    # ==========================
    # render particles
    # ==========================
    render_particles:list = field(
        default_factory=list
    )
    tess_render_particles:list = field(
        default_factory=list
    )
    out_particles:list = field(
        default_factory=list
    )
    # RenderParticles
    render_vertices:list = field(default_factory=list)
    indices:list = field(default_factory=list)
    # ==========================
    # physics
    # ==========================
    rigidities:list = field(default_factory=list)
    # nearby constraints
    nearby_vertex_groups:list = field(default_factory=list)
    # ==========================
    # material
    # ==========================
    root_color=(0.1,0.05,0.02)
    tip_color=(0.3,0.15,0.05)
    # ==========================
    # build functions
    # ==========================
    def add_strand(
        self,
        points,
        scalp_index=-1
    ):
        strand = DAZHairStrand()
        strand.scalp_index = scalp_index
        for p in points:
            strand.add_point(p)
        self.strands.append(strand)
    ######################################
    # build_scalp_mask
    ######################################
    def build_scalp_mask(
            self,
            genesis_obj,
            group_name="scalp"
    ):
        """
        Build RuntimeHairGeometryCreator.ScalpMask
        Blender:
            Vertex Group "scalp"
        VaM:
            bool[] scalpMask.vertices
        """
        if genesis_obj.type != "MESH":
            raise TypeError(
                "Genesis object must be mesh"
            )
        mesh = genesis_obj.data
        vg = genesis_obj.vertex_groups.get(
            group_name
        )
        if vg is None:
            raise Exception(
                f"Missing vertex group: {group_name}"
            )
        #
        # provider
        #
        self.scalp_provider_name = (
            genesis_obj.name
        )
        self.scalp_mask_name = (
            group_name
        )
        #
        # create bool array
        #
        self.scalp_mask = [
            False
        ] * len(mesh.vertices)
        #
        # fill mask
        #
        for v in mesh.vertices:
            for g in v.groups:
                if g.group == vg.index:
                    self.scalp_mask[
                        v.index
                    ] = True
                    break
        return self.scalp_mask
    # ==========================
    # build_vertex_buffer
    # ==========================
    def build_vertex_buffer(self):
        self.vertices.clear()
        offset=0
        for strand in self.strands:
            strand.vertex_offset=offset
            self.vertices.extend(
                strand.vertices
            )
            offset+=len(
                strand.vertices
            )
    # ==========================
    # build_out_particles
    # ==========================
    def build_out_particles(self):
        self.out_particles.clear()
        self.out_particles.extend(
            self.tess_render_particles
        )
    # ==========================
    # build_tess_render_particles
    # ==========================
    def build_tess_render_particles(
        self,
        tess_segments=4):
        """
        Subdivide render particles.
        Input:
            L0 R0
            L1 R1
        Output:
            L0 R0
            Lx Rx
            Lx Rx
            L1 R1
        """
        self.tess_render_particles.clear()
        rp=self.render_particles
        for i in range(
            0,
            len(rp)-2,
            2
        ):
            left0=rp[i]
            right0=rp[i+1]
            left1=rp[i+2]
            right1=rp[i+3]
            for j in range(
                tess_segments
            ):
                t=j/tess_segments
                left=(
                    left0*(1-t)
                    +
                    left1*t
                )
                right=(
                    right0*(1-t)
                    +
                    right1*t
                )
                self.tess_render_particles.append(
                    left
                )
                self.tess_render_particles.append(
                    right
                )
        #
        # append final point
        #
        self.tess_render_particles.append(
            rp[-2]
        )
        self.tess_render_particles.append(
            rp[-1]
        )
    # ==========================
    # build_render_particles
    # ==========================
    def build_render_particles(
        self,
        width=0.001):
        """
        Convert physics particles
        into render particles.
        One particle becomes:
            left
            right
        """
        self.render_particles.clear()
        for strand in self.strands:
            count=len(
                strand.vertices
            )
            if count < 2:
                continue
            for i,p in enumerate(
                strand.vertices
            ):
                #
                # calculate tangent
                #
                if i==0:
                    tangent=(
                        strand.vertices[1]
                        -
                        p
                    ).normalized()
                elif i==count-1:
                    tangent=(
                        p
                        -
                        strand.vertices[i-1]
                    ).normalized()
                else:
                    tangent=(
                        strand.vertices[i+1]
                        -
                        strand.vertices[i-1]
                    ).normalized()
                #
                # calculate hair width direction
                #
                side=tangent.cross(
                    Vector((0,1,0))
                )
                if side.length < 0.00001:
                    side=tangent.cross(
                        Vector((1,0,0))
                    )
                side.normalize()
                #
                # width falloff
                #
                t=i/(count-1)
                # root thicker
                w=width*(1.0-t*0.8)
                left=p-side*w
                right=p+side*w
                self.render_particles.append(
                    left
                )
                self.render_particles.append(
                    right
                )
    # ==========================
    # build_indices
    # ==========================
    def build_indices(
        self,
        width=0.001
    ):
        """
        Build hair render index buffer.
        Convert:
            particle strand
            p0
            p1
            p2
        into:
            ribbon mesh
        render_vertices:
            L0 R0
            L1 R1
            L2 R2
        indices:
            triangle list
        """
        self.render_vertices.clear()
        self.indices.clear()
        for strand in self.strands:
            if len(strand.vertices)<2:
                continue
            start=len(
                self.render_vertices
            )
            #
            # create ribbon vertices
            #
            for i,p in enumerate(
                strand.vertices
            ):
                if i==0:
                    tangent=(
                        strand.vertices[1]
                        -
                        p
                    ).normalized()
                elif i==len(strand.vertices)-1:
                    tangent=(
                        p
                        -
                        strand.vertices[i-1]
                    ).normalized()
                else:
                    tangent=(
                        strand.vertices[i+1]
                        -
                        strand.vertices[i-1]
                    ).normalized()
                #
                # generate side vector
                #
                side=tangent.cross(
                    Vector((0,1,0))
                )
                if side.length < 0.0001:
                    side=tangent.cross(
                        Vector((1,0,0))
                    )
                side.normalize()
                left=p-side*width
                right=p+side*width
                self.render_vertices.append(
                    left
                )
                self.render_vertices.append(
                    right
                )
            #
            # build triangles
            #
            point_count=len(
                strand.vertices
            )
            for i in range(
                point_count-1
            ):
                a=start+i*2
                b=a+1
                c=a+2
                d=a+3
                #
                # triangle 1
                #
                self.indices.extend(
                    [
                        a,
                        b,
                        c
                    ]
                )
                #
                # triangle 2
                #
                self.indices.extend(
                    [
                        a,
                        c,
                        d
                    ]
                )
    # ==========================
    # build_point_joints
    # ==========================
    def build_point_joints(self):
        self.point_joints=[]
        for strand_index,strand in enumerate(self.strands):
            if strand_index >= len(
                self.hair_root_to_scalp_indices
            ):
                continue
            scalp_index = (
                self.hair_root_to_scalp_indices[
                    strand_index
                ]
            )
            if scalp_index <0:
                continue
            joint={
                "particle":
                    strand.vertex_offset,
                "scalp_vertex":
                    scalp_index,
                "rigidity":
                    self.rigidities[strand.vertex_offset] # 这里数组越界了
            }
            self.point_joints.append(
                joint
            )
    # ==========================
    # build_distance_joints
    # ==========================
    def build_distance_joints(self):
        self.distance_joints=[]
        for strand in self.strands:
            offset=strand.vertex_offset
            count=len(strand.vertices)
            for i in range(count-1):
                a=offset+i
                b=offset+i+1
                length=(
                    self.vertices[a]
                    -
                    self.vertices[b]
                ).length
                self.distance_joints.append(
                    {
                        "a":a,
                        "b":b,
                        "distance":length
                    }
                )
    # ==========================
    # build_runtime_strands
    # ==========================
    def build_runtime_strands(
        self,
        scalp_vertex_count
    ):
        self.runtime_strands=[]
        #
        # create empty scalp strands
        #
        for i in range(
            scalp_vertex_count
        ):
            strand = DAZHairStrand()
            strand.scalp_index=i
            strand.vertices=[]
            self.runtime_strands.append(
                strand
            )
        #
        # attach curve hair
        #
        for source in self.strands:
            scalp_index = (
                source.scalp_index
            )
            if scalp_index < 0:
                continue
            if scalp_index >= scalp_vertex_count:
                continue
            target = (
                self.runtime_strands[
                    scalp_index
                ]
            )
            #
            # copy
            #
            target.vertices=[]
            for v in source.vertices:
                target.vertices.append(
                    Vector(v)
                )
            #
            # keep original data
            #
            target.vertex_offset = (
                source.vertex_offset
            )
        return self.runtime_strands
    # ==========================
    # build_rigidities
    # ==========================
    def build_rigidities(
        self,
        root_rigidity=0.55,
        main_rigidity=0.55,
        tip_rigidity=0.0,
        rolloff_power=5.0
    ):
        self.rigidities.clear()
        for strand in self.strands:
            count = len(
                strand.vertices
            )
            if count == 0:
                continue
            for i in range(count):
                if i == 0:
                    rigidity = 1.0
                elif i == 1:
                    rigidity = root_rigidity
                else:
                    x = (
                        float(i-1)
                        /
                        float(count-2)
                    )
                    t = (
                        1.0-x
                    ) ** rolloff_power
                    rigidity = (
                        tip_rigidity
                        +
                        (
                            main_rigidity
                            -
                            tip_rigidity
                        )
                        *
                        t
                    )
                self.rigidities.append(
                    max(
                        0.0,
                        min(
                            1.0,
                            rigidity
                        )
                    )
                )
    # ==========================
    # validate
    # ==========================  
    def validate(self):
        errors=[]
        if len(self.strands)==0:
            errors.append(
                "No strands"
            )
        if len(self.hair_root_to_scalp_indices):
            if len(self.hair_root_to_scalp_indices)!=len(self.strands):
                errors.append("hair_root_to_scalp_indices count mismatch")
        for s in self.strands:
            if len(s.vertices)!=self.segments:
                errors.append(
                    f"strand point count {len(s.vertices)} "
                    f"!= {self.segments}"
                )
        return errors
    # ==========================
    # statistics
    # ==========================  
    def statistics(self):
        return {
            "strand_count":
                len(self.strands),
            "vertex_count":
                len(self.vertices),
            "segments":
                self.segments,
            "rigidity_count":
                len(self.rigidities),
            "distance_joint_count":
                len(self.distance_joints)
        }
    ######################################
    # calculate_segment_length
    ######################################
    def calculate_segment_length(self):
        length=[]
        for strand in self.strands:
            for i in range(
                len(strand.vertices)-1
            ):
                d=(
                    strand.vertices[i+1]
                    -
                    strand.vertices[i]
                ).length
                length.append(d)
        if length:
            self.segment_length=sum(length)/len(length)
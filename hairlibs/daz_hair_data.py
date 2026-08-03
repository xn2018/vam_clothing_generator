from typing import cast
import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree
from dataclasses import dataclass, field
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
    rigidities:list=field(default_factory=list)
    weights:list=field(default_factory=list)
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
#==============================================
# DAZHairData
#==============================================
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
    scalp_provider_name:str="KrayonScalp"
    scalp_mask_name:str="scalp"
    scalp_mask:list=field(default_factory=list)
    strands_mask:list=field(default_factory=list)
    scalp_vertex_count:int=0
    # scalp_vertices:list=field(default_factory=list)
    # scalp triangle index buffer
    scalp_triangle_indices:list[int]=field(
        default_factory=list
    )
    # scalp active vertices
    scalp_vertices_indices:list[int]=field(
        default_factory=list
    )
    runtime_strands:list = field(default_factory=list)
    # ==========================
    # basic geometry
    # ==========================
    name:str = "DAZHair"
    material_name:str = "Main"
    # points per strand
    segments:int = 5
    # distance between points
    segment_length:float = 0.01
    # ==========================
    # strand data
    # ==========================
    strands:list = field(default_factory=list)
    # flattened vertices
    vertices:list = field(default_factory=list)
    # scalp vertex -> hair root
    hair_root_to_scalp_indices:list[int] = field(default_factory=list)
    # root mapping
    hair_root_positions:list=field(
        default_factory=list
    )
    hair_vertices_groups:list=field(default_factory=list)
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
    def blender_to_vam(
        self,
        v
    ) -> Vector:
        """
        Blender -> VaM(Unity)
        Blender:
            X right
            Y forward
            Z up
        VaM:
            X right
            Y up
            Z forward
        """
        return Vector((
            float(-v.x),
            float(v.z),
            float(-v.y)
        ))
    # ==========================
    # add_strand
    # ==========================
    def add_strand(
        self,
        scalp_index:int,
        vertices:list,
        weights:list,
        allow_replace=False
    ):
        #
        # validate
        #
        if scalp_index < 0:
            raise ValueError(
                f"Invalid scalp index {scalp_index}"
            )
        if scalp_index >= len(self.strands):
            raise IndexError(
                f"Scalp index {scalp_index} out of range"
            )
        strand = self.strands[scalp_index]
        if (strand.vertices and not allow_replace):
            raise Exception("Strands Exsit:", scalp_index)
        #
        # validate particle keys
        #
        if len(vertices)!=len(weights):
            raise ValueError(
                "vertices count != weights count"
            )
        #
        # coordinates
        #
        strand.vertices=[
            self.blender_to_vam(v)
            for v in vertices
        ]
        #
        # particle hair rigidity
        #
        strand.weights=[
            max(
                0.0,
                min(
                    1.0,
                    float(w)
                )
            )
            for w in weights
        ]
        if scalp_index not in (
            self.hair_root_to_scalp_indices
        ):
            self.hair_root_to_scalp_indices.append(
                scalp_index
            )
        return strand
    # ==========================
    # set_scalp_vertex_count
    # ==========================
    def set_scalp_vertex_count(self,count):
        self.scalp_vertex_count = count
    # ==========================
    # init_scalp_strands
    # ==========================
    def init_strands(self):
        self.strands.clear()
        for i in range(self.scalp_vertex_count):
            self.strands.append(
                DAZHairStrand(
                    scalp_index=i,
                    vertices=[]
                )
            )
        return self.strands
    # ==========================================================
    # find nearest scalp
    # ==========================================================
    def build_hair_root_scalp_mapping(
            self,
            hair_obj,
            scalp_obj,
            scalp_group="scalp",
            max_distance=0.1
    ):
        """
        Build RuntimeHairGeometryCreator.hairRootToScalpIndices
        hair_obj:
            Blender curve hair
        scalp_obj:
            VaM scalp provider mesh
        return:
            [
                scalp vertex index,
                ...
            ]
        Example:
            [408,409,410,411]
        """
        if scalp_obj.type != "MESH":
            raise TypeError(
                "Scalp object must be mesh"
            )
        mesh = scalp_obj.data
        ##################################################
        # collect scalp vertices
        ##################################################
        scalp_vertices=[]
        vg=None
        if scalp_group:
            vg=scalp_obj.vertex_groups.get(
                scalp_group
            )
        for v in mesh.vertices:
            if vg:
                enabled=False
                for g in v.groups:
                    if g.group == vg.index:
                        enabled=True
                        break
                if not enabled:
                    continue
            world_pos = (
                scalp_obj.matrix_world @ v.co
            )
            scalp_vertices.append(
                (
                    v.index,
                    world_pos
                )
            )
        if len(scalp_vertices)==0:
            raise RuntimeError(
                "No scalp vertices found"
            )
        ##################################################
        # KDTree
        ##################################################
        kd=KDTree(
            len(scalp_vertices)
        )
        for i,(vid,co) in enumerate(
            scalp_vertices
        ):
            kd.insert(
                co,
                vid
            )
        kd.balance()
        ##################################################
        # find hair roots
        ##################################################
        result=[]
        curve=hair_obj.data
        for spline in curve.splines:
            if spline.type=="BEZIER":
                if len(spline.bezier_points)==0:
                    continue
                root=spline.bezier_points[0].co
            else:
                if len(spline.points)==0:
                    continue
                p=spline.points[0]
                root=Vector(
                    (
                        p.co.x,
                        p.co.y,
                        p.co.z
                    )
                )
            root_world = (
                hair_obj.matrix_world @ root
            )
            ##################################################
            # nearest scalp vertex
            ##################################################
            co,index,distance = kd.find(root_world)
            distance = cast(float,distance)
            if distance > max_distance:
                print(
                    "Hair root too far:",
                    distance
                )
                continue
            result.append(
                index
            )
        ##################################################
        # remove duplicate
        ##################################################
        result=list(
            dict.fromkeys(
                result
            )
        )
        self.hair_root_to_scalp_indices=result
        return result
    def build_particle_hair_root_scalp_mapping(
        self,
        scalp_obj,
        hair_psys,
        scalp_group="scalp"
    ):
        if scalp_obj.type != "MESH":
            raise TypeError(
                "Scalp object must be mesh"
            )
        if hair_psys is None:
            raise RuntimeError(
                "Particle system missing"
            )
        mesh=scalp_obj.data
        #
        # collect scalp vertex indices
        #
        scalp_indices=[]
        vg=None
        if scalp_group:
            vg=scalp_obj.vertex_groups.get(
                scalp_group
            )
        for v in mesh.vertices:
            if vg:
                enabled=False
                for g in v.groups:
                    if g.group==vg.index:
                        enabled=True
                        break
                if not enabled:
                    continue
            scalp_indices.append(
                v.index
            )
        print(
            "Scalp vertices:",
            len(scalp_indices)
        )
        #
        # particle count
        #
        particle_count=len(
            hair_psys.particles
        )
        print(
            "Particle count:",
            particle_count
        )
        if particle_count != len(scalp_indices):
            raise RuntimeError(
                f"Particle count {particle_count} "
                f"!= scalp vertices {len(scalp_indices)}"
            )
        #
        # direct mapping
        #
        result=[]
        for i in range(
            particle_count
        ):
            result.append(
                scalp_indices[i]
            )
        print(
            "[Hair] Root mapping:",
            result[:20]
        )
        self.hair_root_to_scalp_indices=result
        return result
    ######################################
    # build_scalp_mask
    ######################################
    def build_scalp_mask(
            self,
            scalp_obj,
            group_name="scalp"
    ):
        """
        Build RuntimeHairGeometryCreator scalpMask
        Blender:
            vertex group "scalp"
        VaM:
            strandsMask
        Args:
            scalp_obj:
                Scalp Provider mesh
        """
        if scalp_obj.type != "MESH":
            raise TypeError(
                "Scalp provider must be mesh"
            )
        mesh = scalp_obj.data
        self.scalp_triangle_indices.clear()
        self.scalp_vertices_indices.clear()
        for poly in mesh.polygons:
            # 只取材质0
            if poly.material_index!=0:
                continue
            self.scalp_triangle_indices.extend(
                [
                    poly.vertices[2],
                    poly.vertices[1],
                    poly.vertices[0]
                ]
            )
        #
        # provider name
        #
        self.scalp_provider_name = (
            scalp_obj.name
        )
        #
        # remove Blender duplicate suffix
        #
        if "." in self.scalp_provider_name:
            base, suffix = (
                self.scalp_provider_name.rsplit(
                    ".",
                    1
                )
            )
            if suffix.isdigit():
                self.scalp_provider_name = base
        #
        # find scalp group
        #
        vg = scalp_obj.vertex_groups.get(
            group_name
        )
        if vg is None:
            raise Exception(
                f"Missing vertex group {group_name}"
            )
        vertex_count = len(
            mesh.vertices
        )
        #
        # default disabled
        #
        self.scalp_mask = [
            True
        ] * vertex_count
        #
        # active scalp vertices
        #
        for v in mesh.vertices:
            for g in v.groups:
                if g.group == vg.index:
                    self.scalp_mask[v.index] = False
                    self.scalp_vertices_indices.append(
                        v.index
                    )
                    break
        #
        # statistics
        #
        self.scalp_vertex_count = (
            vertex_count
        )
        self.scalp_enabled_count = (
            len(self.scalp_vertices_indices)
        )
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
    # build_flat_vertices
    # ==========================
    def build_flat_vertices(self):
        self.vertices.clear()
        self.hair_root_to_scalp_indices.clear()
        runtime_index=0
        for strand in self.strands:
            if not strand.vertices:
                continue
            strand.vertex_offset=runtime_index
            self.hair_root_to_scalp_indices.append(
                strand.scalp_index
            )
            self.vertices.extend(
                strand.vertices
            )
            runtime_index += len(
                strand.vertices
            )
        return self.vertices
    # ==========================
    # build_runtime_indices
    # ==========================
    def build_runtime_indices(self):
        self.indices.clear()
        #
        # build active vertex remap
        #
        active_vertices = (
            self.scalp_vertices_indices
        )
        #
        # original scalp vertex index
        # ->
        # runtime local index
        #
        remap = {}
        for i, vid in enumerate(active_vertices):
            remap[vid] = i
        #
        # build triangles
        #
        tris = self.scalp_triangle_indices
        if len(tris) % 3 != 0:
            raise Exception(
                "scalp triangle index count invalid"
            )
        for i in range(0,len(tris),3):
            a = tris[i]
            b = tris[i+1]
            c = tris[i+2]
            #
            # only keep triangle
            # whose three vertices are enabled
            #
            if (
                a not in remap or
                b not in remap or
                c not in remap
            ):
                continue
            #
            # convert to runtime local index
            #
            self.indices.extend(
                [
                    remap[a],
                    remap[b],
                    remap[c]
                ]
            )
        print(
            "Runtime indices:",
            len(self.indices)
        )
        print(
            self.indices
        )
    # ==========================
    # build_runtime_strands
    # ==========================
    def build_runtime_strands(
        self,
        scalp_vertex_count
    ):
        """
        Build RuntimeHairGeometryCreator.strands
        from Blender Particle Hair
        keep:
            strands[index]
            =
            scalp vertex index
        """
        self.runtime_strands=[]
        ##################################################
        # 1. create empty scalp strands
        ##################################################
        for i in range(
            scalp_vertex_count
        ):
            strand=DAZHairStrand()
            strand.scalp_index=i
            strand.vertices=[]
            strand.vertex_offset=0
            self.runtime_strands.append(
                strand
            )
        ##################################################
        # 2. attach particle hair
        ##################################################
        for source in self.strands:
            scalp_index=(
                source.scalp_index
            )
            if scalp_index < 0:
                continue
            if scalp_index >= scalp_vertex_count:
                continue
            target=(
                self.runtime_strands[
                    scalp_index
                ]
            )
            #
            # copy particle strand points
            #
            target.vertices=[
                Vector(v)
                for v in source.vertices
            ]
            #
            # keep offset
            #
            target.vertex_offset=(
                source.vertex_offset
            )
        return self.runtime_strands
    # ==========================
    # build_rigidities
    # ==========================
    def build_rigidities(self):
        self.rigidities.clear()
        vertex_count=0
        for strand in self.strands:
            if not strand.vertices:
                continue
            if len(strand.weights)!=len(strand.vertices):
                raise RuntimeError(
                    f"Rigidity mismatch: "
                    f"vertices={len(strand.vertices)} "
                    f"weights={len(strand.weights)}"
                )
            for w in strand.weights:
                self.rigidities.append(
                    max(
                        0.0,
                        min(
                            1.0,
                            float(w)
                        )
                    )
                )
            vertex_count+=len(strand.vertices)
        print(
            "Vertices:",
            vertex_count
        )
        print(
            "Rigidities:",
            len(self.rigidities)
        )
    # ==========================
    # validate
    # ==========================  
    def validate_before_export(
        self
    ):
        print("="*70)
        print("DAZHairData Validation")
        print("="*70)
        ####################################
        # Basic
        ####################################
        print(
            "Scalp Provider:",
            self.scalp_provider_name
        )
        print(
            "Segments:",
            self.segments
        )
        print(
            "Segment Length:",
            self.segment_length
        )
        ####################################
        # Scalp mask
        ####################################
        print(
            "Scalp Mask:",
            len(self.scalp_mask)
            if self.scalp_mask
            else 0
        )
        if self.scalp_mask:
            enabled=sum(
                1
                for x in self.scalp_mask
                if x
            )
            print(
                "Scalp Enabled:",
                enabled
            )
        ####################################
        # Strand
        ####################################
        strand_count=len(
            self.strands
        )
        print(
            "Strand Count:",
            strand_count
        )
        active_strands=0
        vertex_total=0
        for i,s in enumerate(
            self.strands
        ):
            if (
                s.vertices
                and
                len(s.vertices)>0
            ):
                active_strands+=1
                vertex_total+=len(
                    s.vertices
                )
        print(
            "Active Strands:",
            active_strands
        )
        print(
            "Total Strand Vertices:",
            vertex_total
        )
        ####################################
        # Flat vertices
        ####################################
        print(
            "Flat vertices:",
            len(self.vertices)
        )
        ####################################
        # Indices
        ####################################
        print("Indices:",len(self.indices))
        if len(self.indices)%3!=0:
            print(
                "ERROR: index count not triangle aligned"
            )
        ####################################
        # Rigidity
        ####################################
        if hasattr(
            self,
            "rigidities"
        ):
            print(
                "Rigidities:",
                len(self.rigidities)
            )
            if len(self.rigidities)!=len(self.vertices):
                print(
                    "WARNING:"
                    " rigidity count != vertex count"
                )
        ####################################
        # Root Mapping
        ####################################
        print(
            "HairRootToScalpIndices:",
            len(
                self.hair_root_to_scalp_indices
            )
        )
        bad=[]
        for x in self.hair_root_to_scalp_indices:
            if (
                x<0
                or
                x>=strand_count
            ):
                bad.append(x)
        if bad:
            print(
                "ERROR invalid scalp index:",
                bad[:20]
            )
        else:
            print(
                "Root mapping OK"
            )
        ####################################
        # Strand consistency
        ####################################
        mismatch=0
        for i,s in enumerate(
            self.strands
        ):
            if s.scalp_index != i:
                mismatch+=1
        print(
            "Strand scalp mismatch:",
            mismatch
        )
        ####################################
        # Sample
        ####################################
        print("\nFirst active strands")
        count=0
        for i,s in enumerate(
            self.strands
        ):
            if s.vertices:
                print(
                    i,
                    "scalp=",
                    s.scalp_index,
                    "vertices=",
                    len(s.vertices)
                )
                count+=1
                if count>=10:
                    break
        print("="*70)
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
                d=(strand.vertices[i+1]-strand.vertices[i]).length
                length.append(d)
        if length:
            self.segment_length=sum(length)/len(length)
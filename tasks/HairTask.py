from typing import Literal
import bpy
import traceback
from dataclasses import dataclass, field
from enum import Enum, auto
from ..hairlibs.curve_importer import CurveHairImporter
from ..hairlibs.particle_hair_importer import ParticleHairImporter
from ..hairlibs.hair_builder import convert_strands_to_dazhair, find_curve_hair_root, find_hair_root
from ..hairlibs.daz_hair_data import DAZHairData
##################################################
# State Machine
##################################################
class HairState(Enum):
    INIT = auto()
    BUILD_ROOT = auto()
    FIND_SCALP = auto()
    BUILD_STRANDS = auto()
    BUILD_SCALP_MASK = auto()
    BUILD_VERTEX_BUFFER = auto()
    BUILD_INDICES = auto()
    BUILD_DISTANCE_JOINTS = auto()
    BUILD_POINT_JOINTS = auto()
    BUILD_RIGIDITY = auto()
    FINISHED = auto()
    FAILED = auto()
    CANCELLED = auto()
##################################################
# Hair Build Task
##################################################
@dataclass
class HairBuildTask:
    ##################################################
    # Input
    ##################################################
    scalp_obj:bpy.types.Object
    hair_obj:bpy.types.Object
    eval_psys: bpy.types.ParticleSystem | None
    ##################################################
    # Options
    ##################################################
    segments:int = 5
    ##################################################
    # Runtime
    ##################################################
    state:HairState = (
        HairState.INIT
    )
    progress_value:float = 0.0
    error:Exception|None=None
    ##################################################
    # Temporary data
    ##################################################
    hair_roots:list = field(
        default_factory=list
    )
    root_mapping:list = field(
        default_factory=list
    )
    hair_data:DAZHairData=field(default_factory=DAZHairData)
    hair_type:str="Particles"
    ##################################################
    # Cancel
    ##################################################
    def cancel(self):
        self.state=(
            HairState.CANCELLED
        )
    ##################################################
    # Update
    ##################################################
    def update(self):
        if self.state in (
            HairState.FINISHED,
            HairState.FAILED,
            HairState.CANCELLED
        ):
            return
        try:
            if self.state == HairState.INIT:
                self.init_task()
            elif self.state == HairState.BUILD_ROOT:
                self.build_roots()
            elif self.state == HairState.FIND_SCALP:
                self.find_scalp()
            elif self.state == HairState.BUILD_STRANDS:
                self.build_strands()
            elif self.state == HairState.BUILD_SCALP_MASK:
                self.build_scalp_mask()
            elif self.state == HairState.BUILD_VERTEX_BUFFER:
                self.build_vertex_buffer()
            elif self.state == HairState.BUILD_INDICES:
                self.build_indices()
            # elif self.state == HairState.BUILD_DISTANCE_JOINTS:
            #     self.build_distance_joints()
            # elif self.state == HairState.BUILD_POINT_JOINTS:
            #     self.build_point_joints()
            elif self.state == HairState.BUILD_RIGIDITY:
                self.build_rigidity()
        except Exception as e:
            traceback.print_exc()
            self.error=e
            self.state=(
                HairState.FAILED
            )
    ##################################################
    # INIT
    ##################################################
    def init_task(self):
        if self.scalp_obj is None:
            raise Exception(
                "scalp object missing"
            )
        if self.hair_obj is None:
            raise Exception(
                "Hair object missing"
            )
        if type(self.hair_obj.data) is not bpy.types.Curve :
            raise Exception(
                "Hair object must be Curve"
            )
        self.progress_value=0.05
        self.state=(
            HairState.BUILD_ROOT
        )
    ##################################################
    # Step 1
    # Find hair roots
    ##################################################
    def build_roots(self):
        if self.hair_type == "Particles":
            self.hair_roots=find_hair_root(self.scalp_obj,self.eval_psys)
        elif self.hair_type == "Curve":
            self.hair_roots=find_curve_hair_root(self.hair_obj)

        if len(self.hair_roots)==0:
            raise Exception("No hair roots found")
        print(
            "[Hair]",
            "Root count:",
            len(self.hair_roots)
        )
        self.progress_value=0.15
        self.state=(
            HairState.FIND_SCALP
        )
    ##################################################
    # Step 2
    # KDTree scalp search
    ##################################################
    def find_scalp(self):
        if self.hair_type == "Particles":
            self.root_mapping=(
                self.hair_data.build_particle_hair_root_scalp_mapping(
                    self.scalp_obj,
                    self.eval_psys
                )
            )
        elif self.hair_type == "Curve":
            self.root_mapping=(
                self.hair_data.build_hair_root_scalp_mapping(
                            self.hair_obj,
                            self.scalp_obj
                        )
            )
        self.progress_value=0.3
        self.state=(
            HairState.BUILD_STRANDS
        )
    ##################################################
    # Step 3
    # Create DAZHairData
    ##################################################
    def build_strands(self):
        if self.hair_type == "Particles":
            importer=ParticleHairImporter(self.scalp_obj,self.eval_psys)
            strands=importer.extract()
            self.hair_data=convert_strands_to_dazhair(
                strands,
                self.scalp_obj,
                importer.segments
            )
        elif self.hair_type == "Curve":
            importer=CurveHairImporter(self.hair_obj)
            strands=importer.extract(self.root_mapping,self.segments)
            self.hair_data=convert_strands_to_dazhair(
                strands,
                self.scalp_obj,
                importer.segments
            )
        self.progress_value=0.45
        self.state=(
            HairState.BUILD_SCALP_MASK
        )
    ##################################################
    # Step 4
    # Scalp Mask
    ##################################################
    def build_scalp_mask(self):
        if self.hair_data is None:
            raise RuntimeError(
                "Hair data missing"
            )
        self.hair_data.build_scalp_mask(
            self.scalp_obj
        )
        self.progress_value=0.55
        self.state=(
            HairState.BUILD_VERTEX_BUFFER
        )
    def build_vertex_buffer(self):
        self.hair_data.build_vertex_buffer()
        self.progress_value=0.6
        self.state=(
            HairState.BUILD_INDICES
        )
    ##################################################
    # Step 5
    # Render / physics indices
    ##################################################
    def build_indices(self):
        self.hair_data.build_runtime_indices()
        self.progress_value=0.65
        self.state=(
            HairState.BUILD_RIGIDITY
        )
    ##################################################
    # Step 6
    # Rigidity
    ##################################################
    def build_rigidity(self):
        self.hair_data.build_rigidities()
        self.progress_value=1.0
        self.state=(
            HairState.FINISHED
        )
    ##################################################
    # Result
    ##################################################
    def get_result(self)->DAZHairData|None:
        if self.state != HairState.FINISHED:
            raise RuntimeError(
                "Hair task not finished"
            )
        self.hair_data.validate_before_export()
        return self.hair_data
    ##################################################
    # Status
    ##################################################
    @property
    def progress(self):
        return self.progress_value
    @property
    def finished(self):
        return (
            self.state ==
            HairState.FINISHED
        )
    @property
    def failed(self):
        return (
            self.state ==
            HairState.FAILED
        )
    @property
    def cancelled(self):
        return (
            self.state ==
            HairState.CANCELLED
        )
def get_particle_hair_segments(eval_psys):
    if eval_psys.settings.type == 'HAIR':
        if len(eval_psys.particles) > 0:
            first_hair = eval_psys.particles[0]
            num_keys = len(first_hair.hair_keys)
            actual_segments = num_keys - 1
            return actual_segments
    return 0
def get_curve_segments(obj)->int:
    if not obj or obj.type != 'CURVE':
        raise RuntimeError("[SEGMENT] get curve segments error, selected object was not Curve.")
    curve = obj.data
    if len(curve.splines) == 0:
        return 0
    spline = curve.splines[0]
    if spline.type == 'BEZIER':
        num_points = len(spline.bezier_points)
    else:
        num_points = len(spline.points)
    if spline.use_cyclic_u:
        segments = num_points
    else:
        segments = max(0, num_points - 1)
    return segments
##################################################
# Factory
##################################################
def create_hair_task(
        scalp_obj,
        hair_obj,
        hair_type
):
    eval_psys= None
    segments=0
    print(hair_type)
    if hair_type == "Particles":
        if not scalp_obj or not scalp_obj.particle_systems:
            raise RuntimeError("Object has no particle system")
        psys = scalp_obj.particle_systems.active
        if psys is None:
            raise RuntimeError("No active particle system")
        if psys.settings.type != 'HAIR':
            raise TypeError("Particle system must be HAIR")
        # -------------------------------------------------------------
        # Key steps: Obtain the dependency graph (Depsgraph) of the current context and the evaluated objects.
        # -------------------------------------------------------------
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj = scalp_obj.evaluated_get(depsgraph)
        # Obtain the activated particle system from the evaluated object.
        eval_psys = eval_obj.particle_systems.active
        segments=get_particle_hair_segments(eval_psys)
    elif hair_type == "Curve":
        segments=get_curve_segments(hair_obj)
    return HairBuildTask(
        scalp_obj=scalp_obj,
        hair_obj=hair_obj,
        eval_psys=eval_psys,
        hair_type=hair_type,
        segments=segments
    )
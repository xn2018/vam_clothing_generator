import bpy
import traceback
from dataclasses import dataclass, field
from enum import Enum, auto
from ..hairlibs.hair_converter import convert_particle_hair_to_dazhair, convert_to_dazhair, find_hair_root
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
                "Genesis missing"
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
        self.hair_roots=find_hair_root(self.scalp_obj,self.eval_psys)
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
        self.root_mapping=(
            self.hair_data.build_particle_hair_root_scalp_mapping(
                self.scalp_obj,
                self.eval_psys
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
        self.hair_data=convert_particle_hair_to_dazhair(
                self.eval_psys,
                self.scalp_obj,
                self.root_mapping
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
##################################################
# Factory
##################################################
def create_hair_task(
        scalp_obj,
        hair_obj,
        segments,
        hair_type = "particles"
):
    eval_psys= None

    if hair_type == "particles":
        if not scalp_obj or not scalp_obj.particle_systems:
            raise RuntimeError("Object has no particle system")
        psys = scalp_obj.particle_systems.active
        if psys is None:
            raise RuntimeError("No active particle system")

        if psys.settings.type != 'HAIR':
            raise TypeError("Particle system must be HAIR")

        # -------------------------------------------------------------
        # 关键步骤：获取当前上下文的依赖图（Depsgraph）和求值后的物体
        # -------------------------------------------------------------
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj = scalp_obj.evaluated_get(depsgraph)

        # 从求值后的物体中获取激活的粒子系统
        eval_psys = eval_obj.particle_systems.active

    return HairBuildTask(
        scalp_obj=scalp_obj,
        hair_obj=hair_obj,
        eval_psys=eval_psys,
        segments=segments
    )
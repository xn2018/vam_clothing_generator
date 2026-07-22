import bpy
import traceback
from dataclasses import dataclass, field
from enum import Enum, auto

from ..hairlibs.hair_converter import convert_to_dazhair, find_hair_root, find_nearest_scalp_vertex

from ..hairlibs.daz_hair_data import DAZHairData

##################################################
# State Machine
##################################################
class HairState(Enum):
    INIT = auto()
    FIND_ROOT = auto()
    FIND_SCALP = auto()
    BUILD_STRANDS = auto()
    BUILD_SCALP_MASK = auto()
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
    genesis_obj:bpy.types.Object
    hair_obj:bpy.types.Object
    ##################################################
    # Options
    ##################################################
    segments:int = 16
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
            elif self.state == HairState.FIND_ROOT:
                self.build_roots()
            elif self.state == HairState.FIND_SCALP:
                self.find_scalp()
            elif self.state == HairState.BUILD_STRANDS:
                self.build_strands()
            elif self.state == HairState.BUILD_SCALP_MASK:
                self.build_scalp_mask()
            elif self.state == HairState.BUILD_INDICES:
                self.build_indices()
            elif self.state == HairState.BUILD_DISTANCE_JOINTS:
                self.build_distance_joints()
            elif self.state == HairState.BUILD_POINT_JOINTS:
                self.build_point_joints()
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
        if self.genesis_obj is None:
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
            HairState.FIND_ROOT
        )
    ##################################################
    # Step 1
    # Find hair roots
    ##################################################
    def build_roots(self):
        self.hair_roots=(
            find_hair_root(
                self.hair_obj
            )
        )
        if len(self.hair_roots)==0:
            raise Exception(
                "No hair roots found"
            )
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
            find_nearest_scalp_vertex(
                self.hair_roots,
                self.genesis_obj
            )
        )
        print(
            "[Hair]",
            "Root mapping:",
            len(self.root_mapping)
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
        self.hair_data=(
            convert_to_dazhair(
                self.hair_obj,
                self.root_mapping,
                self.segments
            )
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
            self.genesis_obj
        )
        self.progress_value=0.55
        self.state=(
            HairState.BUILD_INDICES
        )
    ##################################################
    # Step 5
    # Render / physics indices
    ##################################################
    def build_indices(self):
        self.hair_data.build_indices()
        self.progress_value=0.65
        self.state=(
            HairState.BUILD_DISTANCE_JOINTS
        )
    ##################################################
    # Step 6
    # Distance joints
    ##################################################
    def build_distance_joints(self):
        self.hair_data.build_distance_joints()
        self.progress_value=0.75
        self.state=(
            HairState.BUILD_POINT_JOINTS
        )
    ##################################################
    # Step 7
    # Point joints
    ##################################################
    def build_point_joints(self):
        self.hair_data.build_point_joints()
        self.progress_value=0.85
        self.state=(
            HairState.BUILD_RIGIDITY
        )
    ##################################################
    # Step 8
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
        genesis_obj,
        hair_obj,
        segments=16
):
    return HairBuildTask(
        genesis_obj=genesis_obj,
        hair_obj=hair_obj,
        segments=segments
    )
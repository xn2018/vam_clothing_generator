from typing import cast
import bpy
from dataclasses import dataclass, field
from enum import Enum, auto

from ..wrap.bvh_wrap import calculate_skinwrap_matrix
from ..wrap.build_daz_mesh import build_daz_mesh
from ..wrap.build_wrap_vertices import build_wrap_vertices
from ..wrap.bvh_wrap import build_anchor_triangle_cache, ensure_cache
from ..wrap.wrap_types import (
    DAZBuildResult,
    FlippedTriangles,
    PerSkinWrapCalculationResult,
    SkinWrapVertex,
    WrapInputVertex
)
from ..skinwrap.mesh_validate import check_uv_winding
from ..skinwrap.skinwrap_vertex import (
    calculate_skinwrap_vertex
)
##################################################
# Progress phases
#
# The status bar shows task.progress directly, so every phase must be
# >= the previous one.  The per-vertex phase continues from
# PROGRESS_BUILD_CALC_DATA up to 1.0 (it used to restart at 0.25, which
# made the bar jump backwards right after the cache was built).
##################################################
PROGRESS_VALIDATE_MESH = 0.10
PROGRESS_BUILD_CLOTHING = 0.30
PROGRESS_BUILD_WRAP_VERTICES = 0.40
PROGRESS_BUILD_CALC_DATA = 0.50
##################################################
# State Machine
##################################################
class SkinWrapState(Enum):
    INIT = auto()
    VALIDATE_MESH=auto()
    FIX_UV=auto()
    BUILD_CLOTHING = auto()
    BUILD_WRAP_VERTICES = auto()
    BUILD_CALC_DATA = auto()
    CALCULATE_VERTEX = auto()
    FINISHED = auto()
    FAILED = auto()
    CANCELLED = auto()
##################################################
# Task
##################################################
@dataclass
class SkinWrapTask:
    ##################################################
    # Input
    ##################################################
    genesis_obj:bpy.types.Object
    clothing_obj:bpy.types.Object
    ##################################################
    # Options
    ##################################################
    anchor_only:bool=False
    wrap_check_normals:bool=False
    max_wrap_distance:float=1.0
    ##################################################
    # Runtime
    ##################################################
    state:SkinWrapState=(
        SkinWrapState.INIT
    )
    error:Exception|None=None
    progress_value:float=0.0
    anchor_fallback:bool=False
    ##################################################
    # Prepared Data
    ##################################################
    clothing_data:DAZBuildResult|None=None
    wrap_vertices:list[WrapInputVertex]=field(
        default_factory=list
    )
    calc_data:PerSkinWrapCalculationResult|None=None
    task_id:int=0
    ##################################################
    # uv winding and normal state
    ##################################################
    need_fix_normal:bool=False
    need_fix_uv:bool=False
    flipped_uv_triangles:list[FlippedTriangles]|None=None
    ##################################################
    # Calculation
    ##################################################
    index:int=0
    results:list[SkinWrapVertex|None]=field(default_factory=list)
    ##################################################
    # Statistics
    ##################################################
    empty_count:dict[str,int]=field(
        default_factory=lambda:
        {
            "tri":0,
            "distance":0,
            "tangent1":0,
            "normal":0,
            "tangent2":0,
            "wrap_normal":0
        }
    )
    ##################################################
    # Update
    ##################################################
    def update(self):
        if self.state in (
            SkinWrapState.FINISHED,
            SkinWrapState.FAILED,
            SkinWrapState.CANCELLED
        ):
            return
        try:
            if self.state == SkinWrapState.INIT:
                self.state = (SkinWrapState.VALIDATE_MESH)
            elif self.state == SkinWrapState.VALIDATE_MESH:
                self.validate_mesh()
            elif self.state == SkinWrapState.BUILD_CLOTHING:
                self.build_clothing()
            elif self.state == SkinWrapState.BUILD_WRAP_VERTICES:
                self.build_wrap_vertices()
            elif self.state == SkinWrapState.BUILD_CALC_DATA:
                self.build_calc_data()
            elif self.state == SkinWrapState.CALCULATE_VERTEX:
                self.calculate_vertices()
        except Exception as e:
            self.error=e
            self.state=(
                SkinWrapState.FAILED
            )
            raise
    ##################################################
    # validate mesh uv
    ##################################################
    def validate_mesh(self):
        mesh = cast(bpy.types.Mesh,self.clothing_obj.data)
        winding=check_uv_winding(mesh)

        if winding["ratio"]>0.05:
            self.need_fix_uv=True
            print("The inverted UVs have been found. Please check your clothing mesh UVs.")
        self.progress_value=PROGRESS_VALIDATE_MESH
        self.state=SkinWrapState.BUILD_CLOTHING
    ##################################################
    # Step 1
    ##################################################
    def build_clothing(self):
        self.clothing_data = (
            build_daz_mesh(
                obj=self.clothing_obj,
                is_body=False,
                split_material=True
            )
        )
        self.progress_value=PROGRESS_BUILD_CLOTHING
        self.state=(
            SkinWrapState.BUILD_WRAP_VERTICES
        )
    ##################################################
    # Step 2
    ##################################################
    def build_wrap_vertices(self):
        if self.clothing_data is None:
            raise RuntimeError(
                "Clothing data missing"
            )
        self.wrap_vertices = (
            build_wrap_vertices(
                self.clothing_data.mesh
            )
        )
        self.progress_value=PROGRESS_BUILD_WRAP_VERTICES
        self.state=(
            SkinWrapState.BUILD_CALC_DATA
        )
    ##################################################
    # Step 3
    ##################################################
    def build_calc_data(self):
        if self.clothing_data is None:
            raise RuntimeError("Clothing data missing")

        # 首次 CALC 时 _CACHE 还不存在，get_cache() 会抛错，必须用 ensure_cache()
        cache = ensure_cache(self.genesis_obj)
        anchor_only = self.anchor_only
        self.anchor_fallback = False

        if anchor_only:
            build_anchor_triangle_cache(cache, min_anchor_vertices=3)   # 一次构建，成对写入
            if cache.anchor_bvh is None or not cache.anchor_triangles:
                anchor_only = False
                self.anchor_fallback = True
                print("[SkinWrap] anchor 顶点组为空或过稀，回退全身 BVH")

        self.calc_data = (
            calculate_skinwrap_matrix(
                genesis_obj=
                    self.genesis_obj,
                clothing_obj=
                    self.clothing_data.mesh,
                wrap_vertices=
                    self.wrap_vertices,
                anchor_only=
                    anchor_only,
                wrap_check_normals=
                    self.wrap_check_normals,
                max_wrap_distance=
                    self.max_wrap_distance
            )
        )
        self.results=[
            None
            for _
            in self.wrap_vertices
        ]
        self.progress_value=PROGRESS_BUILD_CALC_DATA
        self.state=(
            SkinWrapState.CALCULATE_VERTEX
        )
    ##################################################
    # Step 4
    ##################################################
    def calculate_vertices(
        self,
        batch_size:int=64
    ):
        if self.calc_data is None:
            raise RuntimeError(
                "Calc data missing"
            )
        total=len(
            self.calc_data.wrap_vertices
        )
        end=min(
            self.index+batch_size,
            total
        )
        for i in range(
            self.index,
            end
        ):
            try:
                result,stat = (
                    calculate_skinwrap_vertex(
                        wrap_vertex=
                            self.calc_data.wrap_vertices[i],
                        clothing_obj=
                            self.calc_data.clothing_obj,
                        local_matrix=
                            self.calc_data.local_matrix,
                        normal_matrix=
                            self.calc_data.normal_matrix,
                        anchor_only=
                            self.calc_data.anchor_only,
                        wrap_check_normals=
                            self.calc_data.wrap_check_normals,
                        max_wrap_distance=
                            self.calc_data.max_wrap_distance
                    )
                )
            except Exception as e:
                self.results[i]=None
                self.error=e
                self.state=SkinWrapState.FAILED
                return
            self.results[i]=result
            for k,v in stat.items():
                self.empty_count[k]+=v
        self.index=end
        if total:
            # Continue from the phase value instead of restarting at 0.25;
            # max() keeps the bar monotonic even if a phase ever reports
            # ahead of the per-vertex ratio.
            self.progress_value = max(
                self.progress_value,
                PROGRESS_BUILD_CALC_DATA
                + (1.0 - PROGRESS_BUILD_CALC_DATA)
                * self.index
                / total
            )
        if self.index>=total:
            self.state=(
                SkinWrapState.FINISHED
            )
            self.progress_value=1.0
    ##################################################
    # Progress
    ##################################################
    @property
    def progress(self):
        return self.progress_value
    ##################################################
    # Status
    ##################################################
    @property
    def finished(self):
        return (
            self.state ==
            SkinWrapState.FINISHED
        )
    @property
    def failed(self):
        return (
            self.state ==
            SkinWrapState.FAILED
        )
    @property
    def cancelled(self):
        return (
            self.state ==
            SkinWrapState.CANCELLED
        )
    ##################################################
    # Cancel
    ##################################################
    def cancel(self):
        self.state=(
            SkinWrapState.CANCELLED
        )
    ##################################################
    # Result
    ##################################################
    def get_result(
        self
    )->list[SkinWrapVertex]:
        if not self.finished:
            raise RuntimeError(
                "SkinWrap not finished"
            )
        result=[]
        for i,v in enumerate(
            self.results
        ):
            if v is None:
                raise RuntimeError(
                    f"Invalid result vertex {i}"
                )
            result.append(v)
        return result
##################################################
# Factory
##################################################
def create_skinwrap_task(
    genesis_obj:bpy.types.Object,
    clothing_hair_obj:bpy.types.Object,
    anchor_only=False,
    wrap_check_normals=False,
    max_wrap_distance=1.0
):

    return SkinWrapTask(
        genesis_obj=genesis_obj,
        clothing_obj=clothing_hair_obj,
        anchor_only=anchor_only,
        wrap_check_normals=wrap_check_normals,
        max_wrap_distance=max_wrap_distance
    )
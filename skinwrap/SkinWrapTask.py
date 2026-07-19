import bpy
from dataclasses import dataclass, field
from ..wrap.bvh_wrap import calculate_skinwrap_matrix
from ..wrap.build_daz_mesh import build_daz_mesh
from ..wrap.build_wrap_vertices import build_wrap_vertices
from ..wrap.wrap_types import (
    PerSkinWrapCalculationResult,
    SkinWrapVertex
)
from .skinwrap_vertex import calculate_skinwrap_vertex
@dataclass
class SkinWrapTask:
    #
    # Prepared data
    #
    calc_data:PerSkinWrapCalculationResult
    #
    # Runtime
    #
    index:int=0
    results:list[SkinWrapVertex|None]=field(
        default_factory=list
    )
    finished:bool=False
    cancelled:bool=False
    empty_count:dict[str,int]=field(
        default_factory=lambda:{
            "tri":0,
            "distance":0,
            "tangent1":0,
            "normal":0,
            "tangent2":0,
            "wrap_normal":0
        }
    )
    def initialize(self):
        self.results=[
            None
            for _ in self.calc_data.wrap_vertices
        ]
    def step(
        self,
        batch_size:int=32
    ):
        if self.finished:
            return
        if self.cancelled:
            return
        end=min(
            self.index+batch_size,
            len(
                self.calc_data.wrap_vertices
            )
        )
        for i in range(
            self.index,
            end
        ):
            try:
                result,stat=calculate_skinwrap_vertex(
                    wrap_vertex=
                        self.calc_data.wrap_vertices[i],
                    clothing_mesh=
                        self.calc_data.clothing_mesh,
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
                self.results[i]=result
                for k,v in stat.items():
                    self.empty_count[k]+=v
            except Exception as e:
                self.results[i]=None
                raise RuntimeError(
                    f"SkinWrap vertex {i} failed: {e}"
                ) from e
        self.index=end
        if self.index >= len(
            self.calc_data.wrap_vertices
        ):
            self.finished=True
    @property
    def progress(self):
        total=len(
            self.calc_data.wrap_vertices
        )
        if total==0:
            return 1.0
        return self.index/total
    
    def cancel(self):
        self.cancelled=True

    def get_result(
        self
    )->list[SkinWrapVertex]:
        if not self.finished:
            raise RuntimeError(
                "Task not finished"
            )
        result=[]
        for i,v in enumerate(self.results):
            if v is None:
                raise RuntimeError(
                    f"SkinWrap vertex {i} failed"
                )
            result.append(v)
        return result
    
def create_skinwrap_task(
    genesis_obj:bpy.types.Object,
    clothing_obj:bpy.types.Object,
    anchor_only:bool=False,
    wrap_check_normals:bool=False,
    max_wrap_distance:float=1.0
)->SkinWrapTask:
    ##################################################
    # Build clothing mesh
    ##################################################
    clothing_data = build_daz_mesh(
        obj=clothing_obj,
        is_body=False,
        split_material=True
    )
    mesh = clothing_data.mesh
    ##################################################
    # Build UV vertices
    ##################################################
    wrap_vertices = build_wrap_vertices(
        mesh
    )
    ##################################################
    # Prepare calculation data
    ##################################################
    calc_data = calculate_skinwrap_matrix(
        genesis_obj=genesis_obj,
        clothing_mesh=mesh,
        wrap_vertices=wrap_vertices,
        anchor_only=anchor_only,
        wrap_check_normals=wrap_check_normals,
        max_wrap_distance=max_wrap_distance
    )
    ##################################################
    # Create Task
    ##################################################
    task = SkinWrapTask(
        calc_data=calc_data
    )
    task.initialize()
    return task
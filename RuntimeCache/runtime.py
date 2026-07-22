from dataclasses import field
from ..hairlibs.daz_hair_data import DAZHairData
from ..wrap.wrap_types import DAZBuildResult, DAZMeshData, DAZTopology, FlippedTriangles, SkinWrapVertex
class VAMRuntime:
    skinwrap_running: bool = False
    calc_ready: bool = False 
    skinwrap_result: list[SkinWrapVertex]
    progress: float = 0.0
    skinwrap_task = None
    skinwrap_source_object = None
    skinwrap_context = {
        "genesis":None,
        "clothing":None,
        "mesh":None
    }
    #
    # Mesh Cache
    #
    clothing_daz_mesh:DAZBuildResult=DAZBuildResult(
        mesh=field(default_factory=DAZMeshData),
        topology=field(default_factory=DAZTopology)
    )
    clothing_object_name:str=""
    clothing_obj_dirty:bool=False
    clothing_flipped: list[FlippedTriangles]=field(
        default_factory=list
    )
    genesis_daz_mesh:DAZBuildResult=DAZBuildResult(
        mesh=field(default_factory=DAZMeshData),
        topology=field(default_factory=DAZTopology)
    )
    genesis_object_name:str=""
    #
    # hair
    #
    hair_running=False
    hair_progress=0.0
    hair_result:DAZHairData|None = None

runtime=VAMRuntime()
from enum import auto
from typing import Optional

from ..wrap.wrap_types import DAZBuildResult, DAZMeshData, DAZTopology, SkinWrapVertex

class VAMRuntime:
    skinwrap_running: bool = False
    skinwrap_ready: bool = False 
    skinwrap_result: Optional[
        list[SkinWrapVertex]
    ] = None
    skinwrap_progress: float = 0.0
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
        mesh=DAZMeshData(),
        topology=DAZTopology()
    )
    clothing_object_name:str=""
    clothing_mesh_dirty:bool=False
    genesis_daz_mesh:DAZBuildResult=DAZBuildResult(
        mesh=DAZMeshData(),
        topology=DAZTopology()
    )
    genesis_object_name:str=""

runtime=VAMRuntime()
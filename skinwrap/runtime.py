from typing import Optional

from ..wrap.wrap_types import SkinWrapVertex

class VAMRuntime:
    skinwrap_running: bool = False
    skinwrap_ready: bool = False 
    skinwrap_result: Optional[
        list[SkinWrapVertex]
    ] = None
    skinwrap_task = None
    skinwrap_source_object = None
    skinwrap_context = {
        "genesis":None,
        "clothing":None,
        "mesh":None
    }

runtime=VAMRuntime()
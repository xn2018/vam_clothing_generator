import os

import bpy

from bpy.props import PointerProperty
from .properties import VAMGEN_Properties
from .ui import VAMGEN_PT_MainPanel
from .operators.generate_package import VAM_OT_SELECTTRIANGLES, VAM_OT_SELECTVERT, VAM_OT_SPLIT, VAM_OT_GeneratePackage,VAM_OT_IMPORT

bl_info = {
    "name": "VaM Clothing Generator",
    "author": "shyuecc",
    "version": (1, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > VaM Tool",
    "description": "generating VaM clothing packages",
    "category": "Interface",
}

# ------------------------------------------------------------------------
#    Registration
# ------------------------------------------------------------------------
classes = (
    VAMGEN_Properties,
    VAMGEN_PT_MainPanel,
    VAM_OT_GeneratePackage,
    VAM_OT_IMPORT,
    VAM_OT_SPLIT,
    VAM_OT_SELECTVERT,
    VAM_OT_SELECTTRIANGLES
)

def register():

    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.vamgen_props = PointerProperty( # type: ignore
        type=VAMGEN_Properties
    )


def unregister():

    if hasattr(bpy.types.Scene, "vamgen_props"):
        del bpy.types.Scene.vamgen_props # type: ignore

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


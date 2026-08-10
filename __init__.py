import os
import bpy
from bpy.props import PointerProperty
from .RuntimeCache.runtime import runtime
from .operators.operators_calulation import VAM_OT_SKINWRAPCALC
from .properties import VAMGEN_Properties
from .ui import VAMGEN_PT_MainPanel
from .operators.generate_package import VAM_OT_RESAMPLE_HAIR, VAM_OT_SELECTTRIANGLES, VAM_OT_SELECTVERT, VAM_OT_SETSPLINEROOT, VAM_OT_GeneratePackage,VAM_OT_IMPORT
bl_info = {
    "name": "Vam Clothing Generator",
    "author": "shyuecc",
    "version": (1, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > VaM Tool",
    "description": "generating VaM clothing and hair packages",
    "category": "Interface",
}
classes = (
    VAMGEN_Properties,
    VAMGEN_PT_MainPanel,
    VAM_OT_GeneratePackage,
    VAM_OT_IMPORT,
    VAM_OT_SKINWRAPCALC,
    VAM_OT_SELECTVERT,
    VAM_OT_SELECTTRIANGLES,
    VAM_OT_SETSPLINEROOT,
    VAM_OT_RESAMPLE_HAIR
)
def draw_skinwrap_progress(self,context):
    if not runtime.progress:
        return
    progress=runtime.progress
    row=self.layout.row()
    row.progress(
        factor=progress,
        type="BAR",
        text=f"SkinWrap {progress*100:.1f}%"
    )
    row.scale_x=2
def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.vamgen_props = PointerProperty( # type: ignore
        type=VAMGEN_Properties
    )
    bpy.types.STATUSBAR_HT_header.append(draw_skinwrap_progress)
def unregister():
    bpy.types.STATUSBAR_HT_header.remove(draw_skinwrap_progress)
    if hasattr(bpy.types.Scene, "vamgen_props"):
        del bpy.types.Scene.vamgen_props # type: ignore
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
	register()

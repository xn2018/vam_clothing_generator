from .runtime import runtime
from ..wrap.build_daz_mesh import build_daz_mesh

def get_clothing_daz_mesh(
    obj
):
    #
    # Object changed
    #
    if (
        runtime.clothing_daz_mesh is None
        or
        runtime.clothing_object_name != obj.name
    ):
        print("Build Clothing DAZ Mesh")
        runtime.clothing_daz_mesh = (
            build_daz_mesh(
                obj=obj,
                is_body=False,
                split_material=True
            )
        )
        runtime.clothing_object_name=obj.name
    return runtime.clothing_daz_mesh

def get_genesis_daz_mesh(
    obj
):
    if (
        runtime.genesis_daz_mesh is None
        or
        runtime.genesis_object_name != obj.name
    ):
        runtime.genesis_daz_mesh=(
            build_daz_mesh(
                obj=obj,
                is_body=True,
                split_material=True
            )
        )
        runtime.genesis_object_name=obj.name
    return runtime.genesis_daz_mesh
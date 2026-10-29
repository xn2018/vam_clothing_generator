import os

import bpy
from bpy.types import Object

from ..wrap.wrap_types import DAZMeshData, DAZTopology, SkinWrapVertex
from ..writers.vab_file_writer import (vab_file_writer)

def generate_vab(
            genesis: Object,
            clothing_obj: Object,
            clothing_hair_id: str,
            topology: DAZTopology,
            daz_mesh: DAZMeshData,
            wrap_data: list[SkinWrapVertex],
            author_name: str,
            output_dir: str,
            body_base_count: int | None = None,
            body_triangle_count: int | None = None
        ):

    """
    props = context.scene.vamgen_props
    """

    if genesis is None:
        raise Exception(
            "Genesis2Female not selected"
        )

    if clothing_obj is None:
        raise Exception(
            "Clothing mesh not selected"
        )

    print("")
    print("===================================")
    print("Generating SkinWrap")
    print("===================================")

    filename = (clothing_hair_id + ".vab")

    output_path = os.path.join(
        output_dir,
        filename
    )
    
    vab_file_writer(
        filepath=output_path,
        clothing_obj=clothing_obj,
        wrap_data= wrap_data,
        author_name=author_name,
        clothing_hair_id=clothing_hair_id,
        topology=topology,
        daz_mesh=daz_mesh,
        body_base_count=body_base_count,
        body_triangle_count=body_triangle_count
    )

    print("")
    print(
        f"[VAB] {output_path}"
    )

    return output_path
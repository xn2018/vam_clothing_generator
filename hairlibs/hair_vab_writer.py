import struct
from .hair_geometry_writer import (
    serialize_runtime_hair_geometry
)
def write_vam_string(f,text):
    data=text.encode("utf-8")
    f.write(
        struct.pack(
            "B",
            len(data)
        )
    )
    f.write(data)
def vab_hair_file_writer(
        filepath,
        genesis,
        hair_obj,
        hair_data,
        author_name,
        hair_id
):
    with open(
        filepath,
        "wb"
    ) as f:
        #
        # Global Header
        #
        write_vam_string(
            f,
            "DynamicStore"
        )
        write_vam_string(
            f,
            "1.0"
        )
        #
        # RuntimeHairGeometryCreator
        #
        serialize_runtime_hair_geometry(
            f,
            hair_data
        )
        #
        # material
        #
        write_hair_material(
            f,
            hair_data,
            author_name,
            hair_id
        )
        #
        # no cloth physics
        #
        f.write(
            struct.pack(
                "?",
                False
            )
        )
        f.flush()
    print(
        "[+] Hair VAB completed"
    )
def write_hair_material(
        f,
        hair_data,
        author,
        hair_id
):
    #
    # 对应:
    #
    # PonytailV3UdaneScalpMaterial
    #
    write_vam_string(
        f,
        "MaterialOptions"
    )
    write_vam_string(
        f,
        "1.0"
    )
    name = (
        "+"
        +
        hair_data.material_name
    )
    write_vam_string(
        f,
        name
    )
    f.write(
        struct.pack(
            "?",
            True
        )
    )
    f.write(
        struct.pack(
            "8B",
            *([0]*8)
        )
    )
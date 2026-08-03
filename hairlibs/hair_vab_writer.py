import struct
from ..writers.binary_writer import write_string
from .hair_geometry_writer import (
    serialize_runtime_hair_geometry
)
def vab_hair_file_writer(
        filepath,
        hair_data
):
    with open(filepath,"wb") as f:
        write_string(
            f,
            "DynamicStore"
        )
        write_string(
            f,
            "1.0"
        )
        #
        # RuntimeHairGeometryCreator exists
        #
        f.write(
            struct.pack(
                "?",
                True
            )
        )
        serialize_runtime_hair_geometry(
            f,
            hair_data
        )
        #
        # no cloth
        #
        f.write(
            struct.pack(
                "?",
                False
            )
        )
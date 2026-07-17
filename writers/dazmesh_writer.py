import struct
from ..wrap.wrap_types import DAZTopology,DAZMeshData

# ============================================================
# Unity BinaryWriter
# ============================================================

def write7bit_int(f, value: int):

    while value >= 0x80:
        f.write(bytes([(value & 0x7F) | 0x80]))
        value >>= 7

    f.write(bytes([value]))


def write_string(f, text: str):

    encoded = text.encode("utf-8")

    write7bit_int(f, len(encoded))

    f.write(encoded)


# ============================================================
# Official DAZMesh Writer V2
# ============================================================

def serialize_dazmesh_block(
    f,
    topology: DAZTopology,
    daz_mesh: DAZMeshData
):

    #
    # =====================================================
    # Header
    # =====================================================
    #

    write_string(f, "DAZMesh")
    write_string(f, "1.0")

    write_string(f, topology.name)
    write_string(f, topology.name + "-1")

    write_string(f, "geometry")
    write_string(f, "geometry-1")

    #
    # =====================================================
    # Base Vertices
    # =====================================================
    #

    base_vertices = topology.base_vertices

    f.write(
        struct.pack(
            "<i",
            len(base_vertices),
        )
    )

    for v in base_vertices:

        f.write(

            struct.pack(

                "<fff",

                float(v.x),
                float(v.y),
                float(v.z),

            )

        )

    #
    # =====================================================
    # Materials
    # =====================================================
    #

    material_names = []

    if topology.data.materials:

        for mat in topology.data.materials:

            if mat is None:
                material_names.append("Material")
            else:
                material_names.append(mat.name)

    else:

        material_names.append("Material")

    f.write(

        struct.pack(

            "<i",

            len(material_names),

        )

    )

    for name in material_names:

        write_string(f, name)

    #
    # =====================================================
    # Base Poly List
    # =====================================================
    #

    base_poly_list = topology.base_poly_list

    f.write(

        struct.pack(

            "<i",

            len(base_poly_list),

        )

    )

    for poly in base_poly_list:

        f.write(

            struct.pack(

                "<i",

                poly.materialNum,

            )

        )

        f.write(

            struct.pack(

                "<i",

                len(poly.vertices),

            )

        )

        for index in poly.vertices:

            f.write(

                struct.pack(

                    "<i",

                    index,

                )

            )

    #
    # =====================================================
    # UV Poly List
    # =====================================================
    #

    uv_poly_list=daz_mesh.uv_poly_list

    #
    # The official documentation does not mention Count again.
    #

    for poly in uv_poly_list:

        f.write(

            struct.pack(

                "<i",

                poly.materialNum,

            )

        )

        f.write(

            struct.pack(

                "<i",

                len(poly.vertices),

            )

        )

        for index in poly.vertices:

            f.write(

                struct.pack(

                    "<i",

                    index,

                )

            )

    #
    # =====================================================
    # UV Count
    # =====================================================
    #

    uv=daz_mesh.orig_uv

    f.write(

        struct.pack(

            "<i",

            len(uv),

        )

    )

    #
    # =====================================================
    # UV Coordinates
    # =====================================================
    #

    for coord in uv:

        f.write(

            struct.pack(

                "<ff",

                float(coord.x),
                float(coord.y),

            )

        )

    #
    # =====================================================
    # VertexMaps
    # =====================================================
    #

    vertex_maps = daz_mesh.vertex_maps

    f.write(

        struct.pack(

            "<i",

            len(vertex_maps),

        )

    )

    for vm in vertex_maps:
        f.write(
            struct.pack(
                "<iii",
                vm.fromvert,
                vm.tovert,
                vm.polyindex,

            )

        )

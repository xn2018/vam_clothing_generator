import struct
# =========================================================
# VaM string
# =========================================================
def write_string(f, text):
    data = text.encode("utf-8")
    f.write(
        struct.pack(
            "B",
            len(data)
        )
    )
    f.write(data)
# =========================================================
# Vector3
# =========================================================
def write_vector3(f, v):
    f.write(
        struct.pack(
            "<fff",
            v.x,
            v.y,
            v.z
        )
    )
# =========================================================
# RuntimeHairGeometryCreator
# =========================================================
def serialize_runtime_hair_geometry(
        f,
        hair
):
    #
    # header
    #
    write_string(
        f,
        "RuntimeHairGeometryCreator"
    )
    #
    # version
    #
    if hair.rigidities:
        write_string(
            f,
            "1.1"
        )
    else:
        write_string(
            f,
            "1.0"
        )
    #
    # scalp provider name
    #
    write_string(
        f,
        hair.scalp_provider_name
    )
    #
    # segments
    #
    f.write(
        struct.pack(
            "<i",
            hair.segments
        )
    )
    #
    # SegmentLength
    #
    f.write(
        struct.pack(
            "<f",
            hair.segment_length
        )
    )
    #
    # ScalpMask
    #
    write_string(
        f,
        hair.scalp_mask_name
    )
    f.write(
        struct.pack(
            "<i",
            len(hair.scalp_mask)
        )
    )
    for value in hair.scalp_mask:
        f.write(
            struct.pack(
                "?",
                value
            )
        )
    #
    # strands
    #
    f.write(
        struct.pack(
            "<i",
            len(hair.strands)
        )
    )
    for strand in hair.strands:
        #
        # scalpIndex
        #
        f.write(
            struct.pack(
                "<i",
                strand.scalp_index
            )
        )
        #
        # vertex count
        #
        f.write(
            struct.pack(
                "<i",
                len(strand.vertices)
            )
        )
        for v in strand.vertices:
            write_vector3(
                f,
                v
            )
    #
    # indices
    #
    f.write(
        struct.pack(
            "<i",
            len(hair.indices)
        )
    )
    for index in hair.indices:
        f.write(
            struct.pack(
                "<i",
                index
            )
        )
    #
    # vertices
    #
    f.write(
        struct.pack(
            "<i",
            len(hair.vertices)
        )
    )
    for v in hair.vertices:
        write_vector3(
            f,
            v
        )
    #
    # rigidities
    #
    if hair.rigidities:
        f.write(
            struct.pack(
                "<i",
                len(hair.rigidities)
            )
        )
        for r in hair.rigidities:
            f.write(
                struct.pack(
                    "<f",
                    r
                )
            )
    #
    # hairRootToScalpIndices
    #
    f.write(
        struct.pack(
            "<i",
            len(
                hair.hair_root_to_scalp_indices
            )
        )
    )
    for index in hair.hair_root_to_scalp_indices:
        f.write(
            struct.pack(
                "<i",
                index
            )
        )
    #
    # nearbyVertexGroups
    #
    serialize_nearby_groups(
        f,
        hair.nearby_vertex_groups
    )
# =========================================================
# Nearby groups
# =========================================================
def serialize_nearby_groups(
        f,
        groups
):
    if groups is None:
        f.write(
            struct.pack(
                "<i",
                0
            )
        )
        return
    f.write(
        struct.pack(
            "<i",
            len(groups)
        )
    )
    for group in groups:
        vectors = group
        f.write(
            struct.pack(
                "<i",
                len(vectors)
            )
        )
        for v in vectors:
            f.write(
                struct.pack(
                    "<ffff",
                    v.x,
                    v.y,
                    v.z,
                    v.w
                )
            )
# =========================================================
# Aux data
# =========================================================
def serialize_runtime_hair_aux(
        f,
        hair
):
    write_string(
        f,
        "RuntimeHairGeometryCreatorAux"
    )
    if hair.rigidities:
        write_string(
            f,
            "1.1"
        )
    else:
        write_string(
            f,
            "1.0"
        )
    #
    # vertices
    #
    f.write(
        struct.pack(
            "<i",
            len(hair.vertices)
        )
    )
    for v in hair.vertices:
        write_vector3(
            f,
            v
        )
    #
    # rigidity
    #
    if hair.rigidities:
        f.write(
            struct.pack(
                "<i",
                len(hair.rigidities)
            )
        )
        for r in hair.rigidities:
            f.write(
                struct.pack(
                    "<f",
                    r
                )
            )
    #
    # nearby groups
    #
    serialize_nearby_groups(
        f,
        hair.nearby_vertex_groups
    )
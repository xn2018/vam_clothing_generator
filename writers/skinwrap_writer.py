import struct

from ..wrap.bvh_wrap import SkinWrapVertex

from .dazmesh_writer import write_string


# =========================================================
# Core Module 3: Composite nested packing components (DAZSkinWrap + DAZSkinWrapStore)
# =========================================================
def serialize_skinwrap_composite_block(f, wrap_name, skinwrap_results:list[SkinWrapVertex]):
    """
    Serialize a double-wrapped composite following the official
    DAZSkinWrap.StoreToBinaryWriter and DAZSkinWrapStore stream format.
    """
    # -----------------------------------------------------
    # LAYER A: DAZSkinWrap outer shell component layer
    # -----------------------------------------------------
    write_string(f, "DAZSkinWrap")
    write_string(f, "1.0")
    write_string(f, wrap_name)  # Core alignment: Fills in the previously missing wrapName string stream bias.

    # -----------------------------------------------------
    # LAYER B: DAZSkinWrapStore internal feature matrix layer
    # -----------------------------------------------------
    write_string(f, "DAZSkinWrapStore")
    write_string(f, "1.0")

    num_wrap_verts = len(skinwrap_results)
    f.write(struct.pack("<i", num_wrap_verts))

    # 4 Ints + 6 Floats = 40 bytes per row, tightly packed
    for data in skinwrap_results:
        f.write(struct.pack(
        "<iiiiffffff",

        data.closestTriangle,

        data.Vertex1,
        data.Vertex2,
        data.Vertex3,

        data.surfaceNormalProjection,
        data.surfaceTangent1Projection,
        data.surfaceTangent2Projection,

        data.surfaceNormalWrapNormalDot,
        data.surfaceTangent1WrapNormalDot,
        data.surfaceTangent2WrapNormalDot,
    ))
        
    # Core alignment: fills the previously missing wrapName string stream offset
    print(f"[+] [DAZSkinWrapStore block] Composite component serialized successfully; wrote {num_wrap_verts} feature rows")
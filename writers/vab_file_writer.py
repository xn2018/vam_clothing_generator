import struct
import re
import bpy
from ..wrap.wrap_types import DAZMeshData, DAZTopology, SkinWrapVertex
from ..operators.generate_vaj import get_muti_mats_dict
from .dazmesh_writer import write_string
from .dazmesh_writer import serialize_dazmesh_block
from .skinwrap_writer import serialize_skinwrap_composite_block

import struct

def write_vam_string(f, text):
    """
    VaM binary string: 7-bit encoded UTF-8 byte length, then the bytes.

    Unity's BinaryWriter.Write(string) is variable length; a single-byte
    length only happens to work for strings shorter than 128 bytes.
    Delegates to the shared writer so both paths stay identical.
    """
    write_string(f, text)

def split_mats_id(id)->str:
    mat_name=""
    match = re.search(r':.*?(Material.*)$', id)
    if match:
        mat_name = match.group(1)
    
    return mat_name

def material_slot_indices(clothing_obj) -> list[int]:
    """
    Renderer material slot indices that actually hold a material.

    get_muti_mats_dict() skips empty slots, so its list index is not the
    slot index once a slot is empty; this keeps the two in sync.
    """
    return [
        index
        for index, slot in enumerate(clothing_obj.material_slots)
        if slot.material is not None
    ]

def write_material_options_section(f, mats, slot_indices):
    """
    MaterialOptions.StoreToBinaryWriter (VAMSource/MaterialOptions.cs:109):

        string  "MaterialOptions"
        string  "1.0"
        string  overrideId              # "+Material<name>"
        int32   paramMaterialSlots.Length
        int32[] paramMaterialSlots       # renderer material slot indices

    There is no bool and no padding: the old "True + 8 zero bytes" was
    really int32(1) + int32(0), which only worked for a single material.
    """
    if len(slot_indices) != len(mats):
        raise RuntimeError(
            f"MaterialOptions 数量不一致: slots={len(slot_indices)} "
            f"mats={len(mats)}"
        )

    for material_index, mat in zip(slot_indices, mats):
        write_string(f, "MaterialOptions")
        write_string(f, "1.0")
        write_string(f, "+" + split_mats_id(mat["id"]))
        f.write(struct.pack("<i", 1))
        f.write(struct.pack("<i", material_index))

def validate_skinwrap_data(
    wrap_data: list[SkinWrapVertex],
    uv_vertex_count: int | None = None,
    body_base_count: int | None = None,
    body_triangle_count: int | None = None,
) -> None:
    """
    Fail fast on wrap data that VaM would silently mis-render.

    Checks:
      * one row per clothing UV vertex,
      * every row has a valid closest triangle,
      * Vertex1..3 stay inside the body's *base* vertex range
        (UV duplicate indices are exactly what breaks at the seams),
      * closestTriangle is a valid body triangle index.
    """
    problems: list[str] = []

    if not wrap_data:
        raise RuntimeError("SkinWrap 数据为空，无法写入 VAB")

    if uv_vertex_count is not None and len(wrap_data) != uv_vertex_count:
        problems.append(
            f"wrap 行数 {len(wrap_data)} != 服装 UV 顶点数 {uv_vertex_count}"
        )

    negative = [
        index
        for index, data in enumerate(wrap_data)
        if data is None or data.closestTriangle < 0
    ]
    if negative:
        problems.append(
            f"{len(negative)} 个顶点没有包裹结果 (closestTriangle < 0)，"
            f"例如 {negative[:8]}"
        )

    if body_base_count is not None:
        over = [
            index
            for index, data in enumerate(wrap_data)
            if data is not None
            and max(data.Vertex1, data.Vertex2, data.Vertex3) >= body_base_count
        ]
        if over:
            problems.append(
                f"{len(over)} 个顶点引用了 UV 复制顶点 "
                f"(>= body base {body_base_count})，例如 {over[:8]}；"
                "接缝处会错，请重新 CALC"
            )

    if body_triangle_count is not None:
        invalid = [
            index
            for index, data in enumerate(wrap_data)
            if data is not None
            and not (0 <= data.closestTriangle < body_triangle_count)
        ]
        if invalid:
            problems.append(
                f"{len(invalid)} 个顶点的 closestTriangle 越界 "
                f"(应 < {body_triangle_count})，例如 {invalid[:8]}"
            )

    if problems:
        raise RuntimeError(
            "SkinWrap 数据校验失败:\n- " + "\n- ".join(problems)
        )


def vab_file_writer(
        filepath:str, 
        clothing_obj:bpy.types.Object, 
        wrap_data:list[SkinWrapVertex], 
        author_name:str, 
        clothing_hair_id:str, 
        topology:DAZTopology, 
        daz_mesh: DAZMeshData,
        body_base_count: int | None = None,
        body_triangle_count: int | None = None
    ):
    """
    Final dispatcher: perfectly reconstruct the official binary stream and complete the clothing physics footer.
    """
    validate_skinwrap_data(
        wrap_data,
        uv_vertex_count=len(daz_mesh.uv_vertices),
        body_base_count=body_base_count,
        body_triangle_count=body_triangle_count,
    )

    with open(filepath, 'wb') as f:
        # 1. Global header
        write_string(f, "DynamicStore")
        write_string(f, "1.0")
        
        # 2. Write mesh data (DAZMesh)
        serialize_dazmesh_block(f, topology, daz_mesh)
        
        # 3. Write wrap data (DAZSkinWrap)
        serialize_skinwrap_composite_block(f, clothing_obj.name, wrap_data)
        
        mats = get_muti_mats_dict(clothing_obj, author_name, clothing_hair_id)
        slot_indices = material_slot_indices(clothing_obj)
        # 4. Write material options section (MaterialOptions)
        write_material_options_section(f, mats, slot_indices)
        
        # 5. Core fix: write the clothing-specific ClothSettings (Physics) flag
        # Write a little-endian False boolean (0x00) to tell VaM: "This item has no extra cloth physics bake data"
        f.write(struct.pack("?", False))
        
        f.flush()
        
    print("[+] VAB compilation flawlessly completed! All dynamic footers aligned.")
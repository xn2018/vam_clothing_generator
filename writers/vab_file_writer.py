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
    """Standard VaM binary string writer."""
    encoded = text.encode('utf-8')
    f.write(struct.pack('B', len(encoded)))
    f.write(encoded)

def split_mats_id(id)->str:
    mat_name=""
    match = re.search(r':.*?(Material.*)$', id)
    if match:
        mat_name = match.group(1)
    
    return mat_name

def write_material_options_section(f, mats):
    """
    Write multiple MaterialOptions blocks sequentially based on the dynamically extracted materials list.
    Supports single-material and multi-material modes.
    """
    total_materials = len(mats)
    
    for index, mat in enumerate(mats):
        # 1. Write fixed header
        write_vam_string(f, "MaterialOptions")
        write_vam_string(f, "1.0")

        # 2. Dynamically prepend '+' and write the material name
        mat_name = split_mats_id(mat['id'])
        full_mat_id = f"+{mat_name}"
        write_vam_string(f, full_mat_id)
        
        # 3. Write active flag (True)
        f.write(struct.pack('?', True))
        
        # 4. Write footer alignment bytes (adapt to the total number of materials)
        if total_materials == 1:
            # 🟢 Perfect ending for single-material mode: 9 bytes total (1 True + 8 zero bytes)
            # Because True was already written as one byte, add 8 zeros here
            f.write(struct.pack('8B', 0, 0, 0, 0, 0, 0, 0, 0))
            
        else:
            # 🔵 Multi-material mode
            if index < total_materials - 1:
                # Not the last material block, follow with 7 zero bytes
                f.write(struct.pack('7B', 0, 0, 0, 0, 0, 0, 0))
            else:
                # Last material block: perfectly align the multi-material ending 00 00 00 01 00 00 00 00
                f.write(struct.pack('8B', 0, 0, 0, 1, 0, 0, 0, 0))

def vab_file_writer(
        filepath:str, 
        clothing_obj:bpy.types.Object, 
        wrap_data:list[SkinWrapVertex], 
        author_name:str, 
        clothing_hair_id:str, 
        topology:DAZTopology, 
        daz_mesh: DAZMeshData
    ):
    """
    Final dispatcher: perfectly reconstruct the official binary stream and complete the clothing physics footer.
    """
    with open(filepath, 'wb') as f:
        # 1. Global header
        write_string(f, "DynamicStore")
        write_string(f, "1.0")
        
        # 2. Write mesh data (DAZMesh)
        serialize_dazmesh_block(f, topology, daz_mesh)
        
        # 3. Write wrap data (DAZSkinWrap)
        serialize_skinwrap_composite_block(f, clothing_obj.name, wrap_data)
        
        mats = get_muti_mats_dict(clothing_obj, author_name, clothing_hair_id)
        # 4. Write material options section (MaterialOptions)
        write_material_options_section(f, mats)
        
        # 5. Core fix: write the clothing-specific ClothSettings (Physics) flag
        # Write a little-endian False boolean (0x00) to tell VaM: "This item has no extra cloth physics bake data"
        f.write(struct.pack("?", False))
        
        f.flush()
        
    print("[+] VAB compilation flawlessly completed! All dynamic footers aligned.")
# generator_vaj.py

import bpy
import json
import os

from pathlib import Path

TEXTURE_MAP = {
    "Base Color": "customTexture_MainTex",
    "Specular": "customTexture_SpecTex",
    "Roughness": "customTexture_GlossTex",  # Usually Roughness may be inverted or correspond directly to the Gloss channel
    "Alpha": "customTexture_AlphaTex",
    "Normal": "customTexture_BumpMap"
}

mat_section = []

def clean_texture_path(raw_path):
    """
    Convert an absolute path to a relative path starting from 'Custom',
    and normalize backslashes to forward slashes.
    Example: 'D:\\Games\\Blender\\Custom\\Clothing\\Female\\...\\tex.png'
    becomes: 'Custom/Clothing/Female/.../tex.png'
    """
    if not raw_path:
        return "NULL"
        
    # 1. First normalize backslashes to forward slashes for easier handling
    normalized_path = raw_path.replace("\\", "/")
    
    # 2. Find the starting position of "/Custom/" or "Custom/"
    keyword = "Custom/"
    if keyword in normalized_path:
        # Extract the substring from Custom to the end
        custom_index = normalized_path.find(keyword)
        return normalized_path[custom_index:]
    
    # Fallback: if no Custom directory is present, return the normalized absolute path
    return normalized_path

def get_muti_mats_dict(obj, creator, clothing_hair_id)->list[str]:
    if len(mat_section) > 0:
        return mat_section
    
    storables = []
    textures_dict = {}
    if obj and obj.type == 'MESH':
        # Retrieve the previously extracted material->texture dictionary
        textures_dict = get_mesh_textures_dict(obj)
    
    # Begin iterating through the object's material slots
    for i, slot in enumerate(obj.material_slots):
        mat = slot.material
        if not mat:
            continue
            
        slot_key = mat.name

        slot_textures = textures_dict.get(slot_key, {})
        
        creatorid=creator

        number = i+1

        if isinstance(creator, tuple):
            creatorid = creator[0]
        
        if len(obj.material_slots) < 2:
            number = ""
        # Simulate the m[0] property logic
        mat_id = f"{creatorid}:{clothing_hair_id}Material{slot.material.name}{number}" 
        
        # --- 2. Create base template ---
        storable_item = {
            "id": mat_id,
            "hideMaterial": "false",
            "renderQueue": "2400",
            "Specular Texture Offset": "0.6473253",
            "Specular Intensity": "1",
            "Gloss": "8",
            "Specular Fresnel": "0.6677907",
            "Gloss Texture Offset": "0.3187263",
            "Global Illumination Filter": "0.0",
            "Alpha Adjust": "0",
            "Diffuse Texture Offset": "0",
            "Diffuse Bumpiness": "0.5",
            "Specular Bumpiness": "0.1307653",
            "customTexture1TileX": "1", "customTexture1TileY": "1",
            "customTexture1OffsetX": "0", "customTexture1OffsetY": "0",
            "customTexture2TileX": "60", "customTexture2TileY": "30",
            "customTexture2OffsetX": "0", "customTexture2OffsetY": "0",
            "customTexture3TileX": "30", "customTexture3TileY": "30",
            "customTexture3OffsetX": "0", "customTexture3OffsetY": "0",
            "customTexture4TileX": "1", "customTexture4TileY": "1",
            "customTexture4OffsetX": "0", "customTexture4OffsetY": "0",
            "customTexture5TileX": "1", "customTexture5TileY": "1",
            "customTexture5OffsetX": "0", "customTexture5OffsetY": "0",
            "customTexture6TileX": "1", "customTexture6TileY": "1",
            "customTexture6OffsetX": "0", "customTexture6OffsetY": "0",
            
            "customTexture_MainTex": "NULL",
            "customTexture_SpecTex": "NULL",
            "customTexture_GlossTex": "NULL",
            "customTexture_AlphaTex": "NULL",
            "customTexture_BumpMap": "NULL",
            "customTexture_DecalTex": "NULL",
            "simTexture": "NULL",

            "Diffuse Color": {"h": "0", "s": "0", "v": "0.05078577"},
            "Specular Color": {"h": "0", "s": "0", "v": "0.5827865"},
            "Subsurface Color": {"h": "0", "s": "0", "v": "0.2011163"}
        }
        
        # --- 3. Automatically clean and populate texture paths ---
        for blender_channel, target_key in TEXTURE_MAP.items():
            if blender_channel in slot_textures:
                absolute_path = slot_textures[blender_channel]
                
                # Key change: call the clean function here to convert to a relative path with forward slashes
                storable_item[target_key] = clean_texture_path(absolute_path)
                
        storables.append(storable_item)
        mat_section.append(storable_item)

    return storables

def get_mesh_textures_dict(obj):
    """
    Iterate through all material slots of a mesh object and return a nested dict:
    {
        "Material_Name (Slot_Index)": {
            "Channel_Name": "Absolute_Texture_Path"
        }
    }
    """
    result_dict = {}
    
    if not obj or obj.type != 'MESH':
        print("Error: provided object is not a valid mesh object")
        return result_dict

    def trace_image_node(socket):
        """Recursively trace an input socket until an image node is found."""
        if not socket.is_linked:
            return None
        
        from_node = socket.links[0].from_node
        
        # Case A: found an image node
        if from_node.type == 'TEX_IMAGE':
            return from_node
        
        # Case B: traverse intermediate converter nodes (e.g., Normal Map, Color Ramp, Mix)
        for input_socket in from_node.inputs:
            if input_socket.is_linked:
                img_node = trace_image_node(input_socket)
                if img_node:
                    return img_node
        return None

    # 1. Iterate through all material slots of the object
    for index, slot in enumerate(obj.material_slots):
        mat = slot.material
        if not mat or not mat.use_nodes or not mat.node_tree:
            continue
            
        nodes = mat.node_tree.nodes
        
        # 2. Find the Principled BSDF node
        principled_node = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if not principled_node:
            continue
            
        # Build a sub-dictionary for the current material slot (use material name as key)
        slot_key = mat.name
        mat_textures = {}
        
        # 3. Check common inputs that may have textures (Blender 4.x)
        target_inputs = [
            'Base Color', 'Subsurface Color', 'Metallic', 'Specular', 
            'Roughness', 'Anisotropic', 'Sheen', 'Clearcoat', 
            'Transmission', 'Emission Color', 'Alpha', 'Normal'
        ]
        
        for input_name in target_inputs:
            if input_name in principled_node.inputs:
                socket = principled_node.inputs[input_name]
                
                # 4. Trace the socket to obtain an image node
                image_node = trace_image_node(socket)
                if image_node and image_node.image:
                    abs_path = bpy.path.abspath(image_node.image.filepath)
                    if abs_path:
                        # Record in the current material dict: { "Base Color": "D:/path/to/tex.png" }
                        mat_textures[input_name] = abs_path
        
        # If textures were collected for this material, write them to the result dict
        if mat_textures:
            result_dict[slot_key] = mat_textures

    return result_dict



def generate_vaj(props, output_path):
    """
    Generate a VaM Clothing VAJ file.

    Expected props fields:
    props.author_name
    props.clothing_hair_id
    props.enable_plugin
    props.plugin_path
    """

    prefix = f"{props.author_name}:{props.clothing_hair_id}"

    storables = []

    clothing_hair_obj = props.clothing_hair_obj
    creator = props.author_name
    clothing_hair_id = props.clothing_hair_id
    mats = get_muti_mats_dict(clothing_hair_obj, creator, clothing_hair_id)

    # --------------------------------------------------
    # Style
    # --------------------------------------------------

    storables.append({
        "id": f"{prefix}Style"
    })

    # --------------------------------------------------
    # Wrap
    # --------------------------------------------------

    storables.append({
        "id": f"{prefix}WrapControl",
        "wrapToSmoothedVerts": "false",
        "surfaceOffset": "0.0003",
        "additionalThicknessMultiplier": "0",
        "smoothIterations": "0"
    })

    # --------------------------------------------------
    # Sim
    # --------------------------------------------------

    storables.append({
        "id": f"{prefix}Sim",
        "simEnabled": "false",
        "integrateEnabled": "true",
        "collisionEnabled": "true",
        "allowDetach": "false",
        "collisionRadius": "0.01",
        "drag": "0.06",
        "weight": "1",
        "distanceScale": "1",
        "stiffness": "0.5",
        "compressionResistance": "0.5",
        "friction": "0.5",
        "staticMultiplier": "2",
        "collisionPower": "0.5",
        "gravityMultiplier": "1",
        "iterations": "3",
        "detachThreshold": "0.005",
        "jointStrength": "1",
        "force": [
            "0",
            "0",
            "0"
        ]
    })

    # --------------------------------------------------
    # ItemControl
    # --------------------------------------------------

    storables.append({
        "id": f"{prefix}ItemControl",
        "disableAnatomy": "false",
        "enableJointSpringAndDamperAdjust": "true",
        "enableBreastJointAdjust": "false",
        "enableGluteJointAdjust": "false",
        "breastJointSpringAndDamperMultiplier": "3",
        "gluteJointSpringAndDamperMultiplier": "3"
    })

    # --------------------------------------------------
    # Materials
    # --------------------------------------------------
    #
    # Note: materials can be auto-populated from Blender materials in the future
    #

    for m in mats:
        storables.append(m)

    # --------------------------------------------------
    # Plugin
    # --------------------------------------------------

    if props.enable_plugin:

        storables.append({
            "id": prefix,
            "plugins": {
                "plugin#0": props.plugin_path
            }
        })

    # --------------------------------------------------
    # Root
    # --------------------------------------------------

    vaj_data = {
        "components": [
            {
                "type": "DAZMesh"
            },
            {
                "type": "DAZSkinWrap"
            },
            {
                "type": "DAZSkinWrapMaterialOptions"
            },
            {
                "type": "MVRPluginManager"
            }
        ],
        "storables": storables
    }

    output_path = Path(output_path)

    vaj_path = os.path.join(output_path,f"{props.clothing_hair_id}.vaj")

    with open(vaj_path, "w", encoding="utf-8") as f:
        json.dump(
            vaj_data,
            f,
            indent=4
        )

    return str(output_path)
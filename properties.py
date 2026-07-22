import bpy
from bpy.props import (
    IntProperty,
    PointerProperty,
    BoolProperty,
    StringProperty,
    EnumProperty,
)


PACKAGE_TYPES = [
    ("None", "None", ""),
    ("Custom", "Custom", ""),
    ("ClothingFemale", "ClothingFemale", ""),
    ("ClothingMale", "ClothingMale", ""),
    ("ClothingNeutral", "ClothingNeutral", ""),
    ("Atom", "Atom", ""),
    ("HairFemale", "HairFemale", ""),
    ("HairMale", "HairMale", ""),
    ("HairNeutral", "HairNeutral", ""),
]


class VAMGEN_Properties(bpy.types.PropertyGroup):

    # --------------------------------------------------
    # Mesh
    # --------------------------------------------------

    genesis_obj: bpy.props.PointerProperty(
        name="Genesis2Female",
        type=bpy.types.Object,
    ) # type: ignore

    clothing_hair_obj: PointerProperty(
        name="Clothing/Hair",
        type=bpy.types.Object,
    ) # type: ignore

    anchor_only: BoolProperty(
        name="Use Vertex Group",
        default=True,
    ) # type: ignore

    # --------------------------------------------------
    # VAM
    # --------------------------------------------------

    author_name: StringProperty(
        name="Creator",
        default="shyuecc"
    ) # type: ignore

    clothing_hair_id: StringProperty(
        name="Clothing/Hair ID",
        default=""
    ) # type: ignore

    package_type: EnumProperty(
        name="Package Type",
        items=PACKAGE_TYPES,
        default="ClothingFemale"
    ) # type: ignore

    # --------------------------------------------------
    # VAJ
    # --------------------------------------------------

    enable_plugin: BoolProperty(
        name="Enable Clothing Plugin",
        default=True,
    ) # type: ignore

    plugin_path: StringProperty(
        name="Plugin",
        default="Stopper.ClothingPluginManager.7:/Custom/Scripts/Stopper/ClothingPluginManager/ClothingPluginManager.cs",
    ) # type: ignore

    # --------------------------------------------------
    # Output
    # --------------------------------------------------

    output_folder: StringProperty(
        name="Output Folder",
        subtype="DIR_PATH",
    ) # type: ignore

    vertex_id: IntProperty(
        name="Vertex ID",
        default=0,
        min=0
    ) # type: ignore
    
    triangles_id: IntProperty(
        name="Vertex ID",
        default=0,
        min=0
    ) # type: ignore
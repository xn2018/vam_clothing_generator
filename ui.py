import bpy
class VAMGEN_PT_MainPanel(bpy.types.Panel):
    bl_label = "VaM Clothing Generator"
    bl_idname = "VAMGEN_PT_MainPanel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "VaM"
    def draw(self, context):
        layout = self.layout
        props = context.scene.vamgen_props
        if layout is None:
            return
        # --------------------------------------------------
        # Mesh
        # --------------------------------------------------
        box = layout.box()
        layout.label(
            text="Mesh Selection",
            icon="MESH_DATA"
        )
        box.prop(
            props,
            "genesis_obj"
        )
        box.prop(
            props,
            "clothing_hair_obj"
        )
        box.prop(
            props,
            "anchor_only"
        )
        # --------------------------------------------------
        # VAM
        # --------------------------------------------------
        box = layout.box()
        box.label(
            text="VAM Package",
            icon="FILE_TEXT"
        )
        box.prop(
            props,
            "author_name"
        )
        box.prop(
            props,
            "clothing_hair_id"
        )
        box.prop(
            props,
            "package_type"
        )
        # --------------------------------------------------
        # VAJ
        # --------------------------------------------------
        box = layout.box()
        box.label(
            text="VAJ Settings",
            icon="PREFERENCES"
        )
        box.prop(
            props,
            "enable_plugin"
        )
        col = box.column()
        col.enabled = props.enable_plugin
        col.prop(
            props,
            "plugin_path"
        )
        # --------------------------------------------------
        # Output
        # --------------------------------------------------
        box = layout.box()
        box.label(
            text="Output",
            icon="FILE_FOLDER"
        )
        box.prop(
            props,
            "output_folder"
        )
        # --------------------------------------------------
        # Generate
        # --------------------------------------------------
        box_gen = layout.box()
        box_gen.label(
            text="Generate",
            icon="PACKAGE"
        )
        split = box_gen.split(factor=0, align=True)
        split.scale_y = 2.0
        col1 = split.column()
        col1.operator(
            "vam.ot_loadatom",
            icon="IMPORT",
            text="Load Atom"
        )
        col2 = split.column()
        col2.operator(
            "vam.ot_skinwrapcalc",
            icon="STICKY_UVS_LOC",
            text="CALC"
        )
        col3 = box_gen.column()
        col3.scale_y = 2.0
        col3.operator(
            "vam.generate_package",
            icon="BLENDER",
            text="Generate VAB / VAJ / VAM"
        )
        # --------------------------------------------------
        # Dev Utils
        # --------------------------------------------------
        box_gen = layout.box()
        box_gen.label(
            text="Dev Utils",
            icon="MESH_DATA"
        )
        split_vert_dev = box_gen.split(factor=0, align=True)
        col1 = split_vert_dev.column()
        col1.prop(props,"vertex_id")
        col2 = split_vert_dev.column()
        col2.operator(
            "vam.ot_selectvert",
            icon="SNAP_VERTEX",
            text="Select Vertex by ID"
        )
        split_tri_dev = box_gen.split(factor=0, align=True)
        col1 = split_tri_dev.column()
        col1.prop(props,"triangles_id")
        col2 = split_tri_dev.column()
        col2.operator(
            "vam.ot_selecttri",
            icon="SNAP_FACE",
            text="Select Traingles by ID"
        )
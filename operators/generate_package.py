from typing import cast
import bpy
import bmesh
import os

from ..skinwrap.runtime import runtime

from .operators_types import OperatorReturn

from ..wrap.build_daz_mesh import build_daz_mesh
from .generate_vab import generate_vab
from .generate_vaj import generate_vaj
from .generate_vam import generate_vam

class VAM_OT_GeneratePackage(
    bpy.types.Operator
):
    bl_idname = "vam.generate_package"
    bl_label = "Generate VaM Package"
    @classmethod
    def poll(
        cls,
        context
    ):
        """
        控制按钮是否可点击
        SkinWrap没有完成:
            禁用按钮
        SkinWrap完成:
            启用按钮
        """
        return (
            runtime.skinwrap_ready
            and
            not runtime.skinwrap_running
        )
    def execute(
        self,
        context: bpy.types.Context
    ) -> set[OperatorReturn]:
        props = context.scene.vamgen_props
        ##################################################
        # Validate
        ##################################################
        genesis = props.genesis_mesh
        clothing_obj = props.clothing_mesh
        if genesis is None:
            self.report(
                {'ERROR'},
                "Genesis mesh not selected"
            )
            return {
                'CANCELLED'
            }
        if clothing_obj is None:
            self.report(
                {'ERROR'},
                "Clothing mesh not selected"
            )
            return {
                'CANCELLED'
            }
        ##################################################
        # Get SkinWrap Cache
        ##################################################
        from ..skinwrap.runtime import runtime
        wrap_data = runtime.skinwrap_result
        if wrap_data is None:
            self.report({'ERROR'},"SkinWrap result missing")
            #
            # 防止状态错误
            #
            runtime.skinwrap_ready=False
            return {
                'CANCELLED'
            }
        ##################################################
        # Output Directory
        ##################################################
        output_dir = bpy.path.abspath(
            props.output_folder
        )
        if not os.path.exists(output_dir):
            os.makedirs(
                output_dir
            )
        clothing_id = props.clothing_id
        author_name = props.author_name
        ##################################################
        # Build Mesh Data
        #
        # 注意:
        # 这里仍然需要，因为SkinWrap只保存计算结果
        #
        ##################################################
        self.report(
            {'INFO'},
            "Building mesh data..."
        )
        dazmesh = build_daz_mesh(
            obj=clothing_obj,
            is_body=False,
            split_material=True
        )
        ##################################################
        # Generate VAB
        ##################################################
        self.report(
            {'INFO'},
            "Generating VAB..."
        )
        generate_vab(
            genesis,
            clothing_obj,
            clothing_id,
            dazmesh.topology,
            dazmesh.mesh,
            wrap_data,
            author_name,
            output_dir,
        )
        ##################################################
        # Generate VAJ
        ##################################################
        self.report(
            {'INFO'},
            "Generating VAJ..."
        )
        generate_vaj(
            props,
            output_dir
        )
        ##################################################
        # Generate VAM
        ##################################################
        self.report(
            {'INFO'},
            "Generating VAM..."
        )
        generate_vam(
            props,
            output_dir
        )
        ##################################################
        # Done
        ##################################################
        self.report(
            {'INFO'},
            "VaM package generated successfully"
        )
        return {
            'FINISHED'
        }
# 1. Define the first button's operator
class VAM_OT_IMPORT(bpy.types.Operator):
    bl_idname = "vam.ot_loadatom"
    bl_label = "Load Atom"
    def execute(self, context: bpy.types.Context)-> set[OperatorReturn]:
        current_dir = os.path.dirname(os.path.realpath(__file__))
        addon_root_dir = os.path.abspath(os.path.join(current_dir, ".."))
        obj_relative_path = os.path.join("DAZExtraData", "model.obj")
        target_path = os.path.join(addon_root_dir, obj_relative_path)
        if not os.path.exists(target_path):
            self.report({'ERROR'}, f"Model file not found: {target_path}\nPlease check the path is correct!")
            return {'CANCELLED'}
        try:
            # 4. Execute import operation (Blender 4.0+ new API)
            bpy.ops.wm.obj_import(filepath=target_path)
            self.report({'INFO'}, f"Successfully imported: {obj_relative_path}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Import failed: {str(e)}")
            return {'CANCELLED'}
        
class VAM_OT_SELECTVERT(bpy.types.Operator):
    bl_idname = "vam.ot_selectvert"
    bl_label = "SELECT VERT"
    def execute(self, context: bpy.types.Context)-> set[OperatorReturn]:
        props = context.scene.vamgen_props
        vertex_id = props.vertex_id
        selected_objs = context.selected_objects
        if selected_objs is None:
            self.report({'WARNING'}, "Please select a mesh object!")
            return {'CANCELLED'}
        # Must select only one object
        if len(selected_objs) != 1:
            self.report({'WARNING'}, "Please select only one mesh object!")
            return {'CANCELLED'}
        active_obj = selected_objs[0]
        # Must be of type MESH
        if active_obj.type != 'MESH':
            self.report({'WARNING'}, "Selected object is not a mesh (MESH)!")
            return {'CANCELLED'}
        # Ensure the object is the active object
        context.view_layer.objects.active = active_obj
        # --- Step 2: Ensure we are in Edit Mode ---
        if active_obj.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')
        # Ensure tool settings switch to vertex select mode
        context.tool_settings.mesh_select_mode = (True, False, False)
        # --- Step 3: Use bmesh to select vertex ---
        # Get mesh data in Edit Mode
        me = cast(bpy.types.Mesh,active_obj.data)
        bm = bmesh.from_edit_mesh(me)
        # Ensure vertex index cache is up-to-date to avoid out-of-bounds after edits
        bm.verts.ensure_lookup_table()
        # Check if input index is out of bounds
        total_verts = len(bm.verts)
        if vertex_id >= total_verts:
            self.report({'ERROR'}, f"Index out of range! This mesh only has {total_verts} vertices (indices 0 to {total_verts - 1})")
            return {'CANCELLED'}
        # Deselect all vertices first (clear previous selection)
        for v in bm.verts:
            v.select = False
        # Select the target vertex
        target_vert = bm.verts[vertex_id]
        target_vert.select = True
        # Sync view/history with new selection
        bm.select_history.clear()
        bm.select_history.add(target_vert)
        # Write changes back to mesh and refresh view
        bmesh.update_edit_mesh(me)
        self.report({'INFO'}, f"Successfully selected vertex Index: {vertex_id}")
        return {'FINISHED'}
    
class VAM_OT_SELECTTRIANGLES(bpy.types.Operator):
    bl_idname = "vam.ot_selecttri"
    bl_label = "SELECT TRI"
    def execute(self, context: bpy.types.Context)-> set[OperatorReturn]:
        props = context.scene.vamgen_props
        triangles_id = props.triangles_id
        selected_objs = context.selected_objects
        if selected_objs is None:
            self.report({'WARNING'}, "Please select a mesh!")
            return {'CANCELLED'}
        # Must select only one object
        if len(selected_objs) != 1:
            self.report({'WARNING'}, "Please select only one mesh object!")
            return {'CANCELLED'}
        active_obj = selected_objs[0]
        # Must be of type MESH
        if active_obj.type != 'MESH':
            self.report({'WARNING'}, "The selected object is not a mesh (MESH)!")
            return {'CANCELLED'}
        # Ensure the object is the active object
        context.view_layer.objects.active = active_obj
        # --- Step 2: Ensure we are in Edit Mode ---
        if active_obj.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')
        # Ensure tool settings switch to face select mode
        context.tool_settings.mesh_select_mode = (False, False, True)
        # --- Step 3: Use bmesh to select face ---
        # Get mesh data in Edit Mode
        me = cast(bpy.types.Mesh,active_obj.data)
        bm = bmesh.from_edit_mesh(me)
        # Ensure face index cache is up-to-date to avoid out-of-bounds after edits
        bm.faces.ensure_lookup_table()
        # Check if input index is out of bounds
        total_face = len(bm.faces)
        if triangles_id >= total_face:
            self.report({'ERROR'}, f"Index out of bounds! This mesh only has {total_face} face (index 0 to {total_face - 1})")
            return {'CANCELLED'}
        # Deselect all faces first (clear previous selection)
        for v in bm.faces:
            v.select = False
        # Select the target face
        target_face = bm.faces[triangles_id]
        target_face.select = True
        # Sync view/history with new selection
        bm.select_history.clear()
        bm.select_history.add(target_face)
        # Write changes back to mesh and refresh view
        bmesh.update_edit_mesh(me)
        self.report({'INFO'}, f"Successfully selected face Index: {triangles_id}")
        return {'FINISHED'}
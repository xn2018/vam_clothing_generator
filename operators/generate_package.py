import bpy
import bmesh
import os
from typing import cast
from .generate_hair_vaj import generate_hair_vaj
from .generate_hair_vab import generate_hair_vab
from .generate_hair_vam import generate_hair_vam
from ..skinwrap.runtime_mesh_cache import get_clothing_daz_mesh
from ..RuntimeCache.runtime import runtime
from .operators_types import OperatorReturn
from .generate_vab import generate_vab
from .generate_vaj import generate_vaj
from .generate_vam import generate_vam
from ..hairlibs.curve_resampler import (
    resample_curve_object
)
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
        Control button clickability
        SkinWrap not complete:
        Disable button
        SkinWrap complete:
        Enable button
        """
        return (
            runtime.calc_ready
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
        genesis = props.genesis_obj
        clothing_hair_obj = props.clothing_hair_obj
        package_type = props.package_type
        if genesis is None:
            self.report(
                {'ERROR'},
                "Genesis mesh not selected"
            )
            return {
                'CANCELLED'
            }
        if clothing_hair_obj is None:
            self.report(
                {'ERROR'},
                "Clothing mesh not selected"
            )
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
        clothing_hair_id = props.clothing_hair_id
        author_name = props.author_name
        ##################################################
        # Hair Packing pipeline
        ##################################################
        if package_type == "HairFemale":
            hair_data = runtime.hair_result
            if hair_data is None:
                self.report({'ERROR'},"hair result missing")
                #
                # Preventing status errors
                #
                runtime.calc_ready=False
                return {
                    'CANCELLED'
                }
            ##################################################
            # Generate VAB
            ##################################################
            self.report(
                {'INFO'},
                "Generating Hair VAB..."
            )
            generate_hair_vab(
                genesis,
                clothing_hair_obj,
                clothing_hair_id,
                hair_data,
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
            generate_hair_vaj(
                hair_data,
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
            generate_hair_vam(
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
        ##################################################
        # clothes Packing pipeline
        ##################################################
        else:
            ##################################################
            # Get SkinWrap Cache
            ##################################################
            # from ..RuntimeCache.runtime import runtime
            wrap_data = runtime.skinwrap_result
            if wrap_data is None:
                self.report({'ERROR'},"SkinWrap result missing")
                #
                # Preventing status errors
                #
                runtime.calc_ready=False
                return {
                    'CANCELLED'
                }
            ##################################################
            # Build Mesh Data
            #
            # This is still necessary because SkinWrap only saves the calculation results.
            #
            ##################################################
            self.report(
                {'INFO'},
                "Building mesh data..."
            )
            dazmesh = get_clothing_daz_mesh(
                clothing_hair_obj
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
                clothing_hair_obj,
                clothing_hair_id,
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
class VAM_OT_RESAMPLE_HAIR(
        bpy.types.Operator
):
    bl_idname="vam.resample_curve_hair"
    bl_label="Resample Hair"
    def execute(self, context: bpy.types.Context)-> set[OperatorReturn]:
        scene = context.scene
        props = scene.vamgen_props
        target_segments = props.hair_segments
        selected_objs = context.selected_objects
        if not selected_objs:
            self.report({'WARNING'}, "No Curve objects are selected.")
            return {'CANCELLED'}
        for obj in selected_objs:
            was_in_editmode = (obj.mode == 'EDIT')
            if was_in_editmode:
                bpy.ops.object.mode_set(mode='OBJECT')
            resample_curve_object(obj, target_segments)
            if was_in_editmode:
                bpy.ops.object.mode_set(mode='EDIT')

        self.report({'INFO'}, f"Resampling successful, current Segment number: {target_segments}")
        return {'FINISHED'}
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
class VAM_OT_SETSPLINEROOT(bpy.types.Operator):
    """Set the selected vertex in curve editing mode as the starting point of the current spline."""
    bl_idname = "vam.ot_setsplineroot"
    bl_label = "Set Selected Point as Root"
    bl_options = {'REGISTER', 'UNDO'}
    @classmethod
    def poll(cls, context):
        return (context.active_object is not None and 
                context.active_object.type == 'CURVE' and 
                context.mode == 'EDIT_CURVE')
    def execute(self, context: bpy.types.Context)-> set[OperatorReturn]:
        selected_objs = context.selected_objects
        if not selected_objs or len(selected_objs) != 1:
            self.report({'WARNING'}, "Please ensure that only one curve object is selected.")
            return {'CANCELLED'}
        curve_obj = selected_objs[0]
        if curve_obj.type != 'CURVE' or not isinstance(curve_obj.data, bpy.types.Curve):
            self.report({'WARNING'}, "The selected object is not a curve. (Curve)！")
            return {'CANCELLED'}
        curve_data = curve_obj.data
        # You must first switch back to OBJECT mode to refresh the data stream, and then switch back to EDIT mode after processing is complete.
        bpy.ops.object.mode_set(mode='OBJECT')
        modified_count = 0
        for spline in curve_data.splines:
            target_index = -1
            # 1. Find the index of the selected vertex in the current spline.
            if spline.type == 'BEZIER':
                for i, pt in enumerate(spline.bezier_points):
                    if pt.select_control_point:
                        target_index = i
                        break
            else:  # POLY or NURBS
                for i, pt in enumerate(spline.points):
                    if pt.select:
                        target_index = i
                        break
            # No point is selected, or the selected point is already the starting point (Index 0).
            if target_index <= 0:
                continue
            # 2. Processing depends on whether the curve is closed (use_cyclic_u) and the Spline type.
            if spline.use_cyclic_u:
                if spline.type == 'BEZIER':
                    self.shift_bezier_spline(spline, target_index)
                else:
                    self.shift_poly_spline(spline, target_index)
            else:
                # Non-closed curve: Reverse the direction of the entire curve (invert the beginning and end).
                if spline.type == 'BEZIER':
                    self.reverse_bezier_spline(spline)
                else:
                    self.reverse_poly_spline(spline)
            modified_count += 1
        # Return to edit mode
        bpy.ops.object.mode_set(mode='EDIT')
        if modified_count > 0:
            self.report({'INFO'}, f"Successfully reset the starting point of the {modified_count} spline!")
        else:
            self.report({'WARNING'}, "No selected vertex for which the starting point needs to be updated was found (or the selected vertex is already the starting point).")
        return {'FINISHED'}
    def reverse_bezier_spline(self, spline):
        """Non-closed Bézier curve: The entire line sequence is flipped, and the left and right handles are swapped."""
        pts = list(spline.bezier_points)
        # Extract point attribute data
        data = []
        for p in pts:
            data.append({
                'co': p.co.copy(),
                # Key Points: When reversing the curve direction, the original left handle becomes the right handle, and the right handle becomes the left handle.
                'handle_left': p.handle_right.copy(),
                'handle_right': p.handle_left.copy(),
                'handle_left_type': p.handle_right_type,
                'handle_right_type': p.handle_left_type,
                'hide': p.hide,
                'radius': p.radius,
                'select_control_point': p.select_control_point,
                'select_left_handle': p.select_right_handle,
                'select_right_handle': p.select_left_handle,
                'tilt': -p.tilt,  # Tilt angle reversed
                'weight_softbody': p.weight_softbody
            })
        # Sequence Reversal
        data.reverse()
        # Write back data
        for i, p in enumerate(pts):
            d = data[i]
            p.co = d['co']
            p.handle_left = d['handle_left']
            p.handle_right = d['handle_right']
            p.handle_left_type = d['handle_left_type']
            p.handle_right_type = d['handle_right_type']
            p.hide = d['hide']
            p.radius = d['radius']
            p.select_control_point = d['select_control_point']
            p.select_left_handle = d['select_left_handle']
            p.select_right_handle = d['select_right_handle']
            p.tilt = d['tilt']
            p.weight_softbody = d['weight_softbody']
    def reverse_poly_spline(self, spline):
        """Non-closed Poly/NURBS curves: The entire line sequence is flipped."""
        pts = list(spline.points)
        data = []
        for p in pts:
            data.append({
                'co': p.co.copy(),
                'hide': p.hide,
                'radius': p.radius,
                'select': p.select,
                'tilt': -p.tilt,
                'weight': p.weight,
                'weight_softbody': p.weight_softbody
            })
        # Sequence Reversal
        data.reverse()
        for i, p in enumerate(pts):
            d = data[i]
            p.co = d['co']
            p.hide = d['hide']
            p.radius = d['radius']
            p.select = d['select']
            p.tilt = d['tilt']
            p.weight = d['weight']
            p.weight_softbody = d['weight_softbody']
    def shift_bezier_spline(self, spline, root_idx):
        """Closed Bézier curve: cyclic shift by index"""
        pts = list(spline.bezier_points)
        data = []
        for p in pts:
            data.append({
                'co': p.co.copy(),
                'handle_left': p.handle_left.copy(),
                'handle_right': p.handle_right.copy(),
                'handle_left_type': p.handle_left_type,
                'handle_right_type': p.handle_right_type,
                'hide': p.hide,
                'radius': p.radius,
                'select_control_point': p.select_control_point,
                'select_left_handle': p.select_left_handle,
                'select_right_handle': p.select_right_handle,
                'tilt': p.tilt,
                'weight_softbody': p.weight_softbody
            })
        new_data = data[root_idx:] + data[:root_idx]
        for i, p in enumerate(pts):
            d = new_data[i]
            p.co = d['co']
            p.handle_left = d['handle_left']
            p.handle_right = d['handle_right']
            p.handle_left_type = d['handle_left_type']
            p.handle_right_type = d['handle_right_type']
            p.hide = d['hide']
            p.radius = d['radius']
            p.select_control_point = d['select_control_point']
            p.select_left_handle = d['select_left_handle']
            p.select_right_handle = d['select_right_handle']
            p.tilt = d['tilt']
            p.weight_softbody = d['weight_softbody']
    def shift_poly_spline(self, spline, root_idx):
        """Close Poly/NURBS curves: Cyclic shift by index"""
        pts = list(spline.points)
        data = []
        for p in pts:
            data.append({
                'co': p.co.copy(),
                'hide': p.hide,
                'radius': p.radius,
                'select': p.select,
                'tilt': p.tilt,
                'weight': p.weight,
                'weight_softbody': p.weight_softbody
            })
        new_data = data[root_idx:] + data[:root_idx]
        for i, p in enumerate(pts):
            d = new_data[i]
            p.co = d['co']
            p.hide = d['hide']
            p.radius = d['radius']
            p.select = d['select']
            p.tilt = d['tilt']
            p.weight = d['weight']
            p.weight_softbody = d['weight_softbody']
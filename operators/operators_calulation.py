from typing import Optional, Union, cast
import bpy
import traceback
from ..tasks.HairTask import create_hair_task
from .operators_types import OperatorReturn
from ..tasks.SkinWrapTask import SkinWrapTask
from ..tasks.HairTask import HairBuildTask
from ..tasks.SkinWrapTask import (
    create_skinwrap_task
)
from ..RuntimeCache.runtime import runtime
class VAM_OT_SKINWRAPCALC(
    bpy.types.Operator
):
    bl_idname="vam.ot_skinwrapcalc"
    bl_label="calculate"
    task: Optional[
        Union[
            SkinWrapTask,
            HairBuildTask
        ]
    ]
    ##################################################
    # Init
    ##################################################
    def __init__(self):
        self.task=None
        self.timer=None
        self.package_type="ClothingFemale"
    ##################################################
    # progress refresh
    ##################################################
    def update_progress(
        self,
        context
    ):
        for window in (
            context.window_manager.windows
        ):
            if window.screen is None:
                continue
            for area in window.screen.areas:
                if area.type=="STATUSBAR":
                    area.tag_redraw()
    ##################################################
    # UI refresh
    ##################################################       
    def refresh_ui(self,context):
        for window in context.window_manager.windows:
            screen=window.screen
            if screen is None:
                continue
            for area in screen.areas:
                area.tag_redraw()
    ##################################################
    # Cleanup
    ##################################################
    def cleanup(
        self,
        context,
        reset_ready=True,
        reset_progress=True
    ):
        wm=context.window_manager
        #
        # Timer
        #
        if self.timer:
            try:
                wm.event_timer_remove(
                    self.timer
                )
            except Exception:
                pass
            self.timer=None
        #
        # Status text
        #
        try:
            context.workspace.status_text_set(
                None
            )
        except Exception:
            pass
        #
        # Runtime state
        #
        runtime.skinwrap_running=False
        if reset_ready:
            runtime.calc_ready=False
        if reset_progress:
            runtime.progress=0.0
        self.task=None
        self.update_progress(
            context
        )
    ##################################################
    # Execute
    ##################################################
    def execute(
        self,
        context
    )->set[OperatorReturn]:
        props=context.scene.vamgen_props
        self.package_type = props.package_type
        if runtime.skinwrap_running:
            self.report(
                {'WARNING'},
                "SkinWrap already running"
            )
            return {
                'CANCELLED'
            }
        if props.genesis_obj is None:
            self.report(
                {'ERROR'},
                "Genesis missing"
            )
            return {
                'CANCELLED'
            }
        if props.clothing_hair_obj is None:
            self.report(
                {'ERROR'},
                "Clothing missing"
            )
            return {
                'CANCELLED'
            }
        #
        # Runtime state
        #
        runtime.calc_ready=False
        runtime.skinwrap_running=True
        runtime.progress=0.0
        #
        # Create task
        #
        #
        # 注意:
        # 这里现在不会执行build_daz_mesh
        # 不会阻塞
        #
        try:
            if props.package_type=="HairFemale":
                self.task=create_hair_task(
                    props.genesis_obj,
                    props.clothing_hair_obj
                )
            else:
                self.task=create_skinwrap_task(
                    props.genesis_obj,
                    props.clothing_hair_obj,
                    props.anchor_only
                )
        except Exception as e:
            traceback.print_exc()
            self.cleanup(
                context
            )
            self.report(
                {'ERROR'},
                f"SkinWrap create failed: {e}"
            )
            return {
                'CANCELLED'
            }
        #
        # Timer
        #
        wm=context.window_manager
        self.timer=wm.event_timer_add(
            0.01,
            window=context.window
        )
        wm.modal_handler_add(
            self
        )
        self.update_progress(
            context
        )
        return {
            'RUNNING_MODAL'
        }
    ##################################################
    # Modal
    ##################################################
    def modal(
        self,
        context,
        event
    )->set[OperatorReturn]:
        #
        # Cancel
        #
        if event.type=="ESC":
            if self.task:
                self.task.cancel()
            self.cleanup(
                context
            )
            self.report(
                {'WARNING'},
                "SkinWrap cancelled"
            )
            return {
                'CANCELLED'
            }
        #
        # Timer
        #
        if event.type=="TIMER":
            if self.task is None:
                self.cleanup(context)
                return {'CANCELLED'}
            try:
                #
                # State machine tick
                #
                self.task.update()
                #
                # Progress
                #
                progress=(
                    self.task.progress
                )
                if abs(
                    progress-runtime.progress
                )>0.005:
                    runtime.progress=(progress)
                    self.update_progress(context)
                #
                # Status bar
                #
                context.workspace.status_text_set(
                    f"{self.task.state.name} "
                    f"{progress*100:.1f}%"
                )
                #
                # Failed
                #
                if self.task.failed:
                    raise RuntimeError(
                        str(
                            self.task.error
                        )
                    )
                #
                # Finished
                #
                if self.task.finished:
                    if self.package_type=="HairFemale":
                        task = cast(HairBuildTask,self.task)
                        runtime.hair_result=(task.get_result())
                    else:
                        task = cast(SkinWrapTask,self.task)
                        runtime.skinwrap_result=(task.get_result())
                    runtime.calc_ready=True
                    runtime.skinwrap_running=False
                    runtime.progress=1.0
                    self.refresh_ui(context)
                    self.cleanup(
                        context,
                        reset_ready=False
                    )
                    self.report(
                        {'INFO'},
                        "SkinWrap calculation completed"
                    )
                    return {
                        'FINISHED'
                    }
            except Exception as e:
                traceback.print_exc()
                if self.task:
                    self.task.cancel()
                self.cleanup(
                    context
                )
                self.report(
                    {'ERROR'},
                    f"SkinWrap failed: {e}"
                )
                return {
                    'CANCELLED'
                }
        return {
            'RUNNING_MODAL'
        }
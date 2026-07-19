import bpy
import traceback
from .operators_types import OperatorReturn
from ..skinwrap.SkinWrapTask import create_skinwrap_task
from ..skinwrap.runtime import runtime
class VAM_OT_SKINWRAPCALC(
    bpy.types.Operator
):
    bl_idname = "vam.ot_skinwrapcalc"
    bl_label = "calculate skinWrap"

    def __init__(self):
        self.task=None
        self.timer=None
    ##################################################
    # Cleanup
    ##################################################
    def cleanup(
        self,
        context
    ):
        wm=context.window_manager
        #
        # stop state
        #
        runtime.skinwrap_running=False
        #
        # progress bar
        #
        try:
            wm.vam_skinwrap_progress=0.0
        except:
            pass
        #
        # timer
        #
        if self.timer:
            try:
                wm.event_timer_remove(
                    self.timer
                )
            except:
                pass
            self.timer=None
        #
        # status bar
        #
        try:
            context.workspace.status_text_set(
                None
            )
        except:
            pass
        #
        # task reset
        #
        self.task=None
    ##################################################
    # Execute
    ##################################################
    def execute(
        self,
        context
    )->set[OperatorReturn]:
        scene = context.scene
        props = scene.vamgen_props
        if runtime.skinwrap_running:
            self.report(
                {'WARNING'},
                "skinWrap already running"
            )
            return {
                'CANCELLED'
            }
        if props.genesis_mesh is None:
            self.report(
                {'ERROR'},
                "genesis missing"
            )
            return {
                'CANCELLED'
            }
        if props.clothing_mesh is None:
            self.report(
                {'ERROR'},
                "clothing missing"
            )
            return {
                'CANCELLED'
            }
        #
        # state
        #
        runtime.skinwrap_ready=False
        runtime.skinwrap_running=True
        try:
            self.task=create_skinwrap_task(
                props.genesis_mesh,
                props.clothing_mesh,
                props.anchor_only
            )
        except Exception as e:
            traceback.print_exc()
            self.cleanup(
                context
            )
            self.report(
                {'ERROR'},
                f"skinWrap init failed: {e}"
            )
            return {
                'CANCELLED'
            }
        #
        # progress
        wm=context.window_manager
        wm.vam_skinwrap_progress=0.0
        self.timer=wm.event_timer_add(
            0.01,
            window=context.window
        )
        wm.modal_handler_add(
            self
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
        scene=context.scene
        #
        # ESC cancel
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
                self.cleanup(
                    context
                )
                return {
                    'CANCELLED'
                }
            try:
                self.task.step(
                    batch_size=64
                )
                
                progress=self.task.progress
                context.window_manager.vam_skinwrap_progress=(progress)

                #
                # finished
                #
                if self.task.finished:

                    result=self.task.get_result()

                    if any(
                        r is None
                        for r in result
                    ):
                        raise RuntimeError(
                            "SkinWrap result contains None"
                        )

                    runtime.skinwrap_result=result
                    runtime.skinwrap_ready=True
                    runtime.skinwrap_running=False
                    #
                    # Force UI refresh
                    #
                    context.window_manager.vam_skinwrap_progress=1.0

                    self.cleanup(context)

                    self.report(
                        {'INFO'},
                        "SkinWrap calculation completed"
                    )

                    return {
                        'FINISHED'
                    }
            except Exception as e:
                #
                # important:
                # 捕获计算阶段异常
                #
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
def draw_skinwrap_progress(self,context):
    progress=(
        context.window_manager.vam_skinwrap_progress
    )
    if progress <= 0:
        return
    row=self.layout.row()
    row.progress(
        factor=progress,
        type="BAR",
        text=f"SkinWrap "f"{progress*100:.1f}%"
    )
    row.scale_x=2
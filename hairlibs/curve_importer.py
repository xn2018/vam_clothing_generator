from typing import cast

import bpy
from .curve_tools import (
    resample_polyline,
    sample_spline_polyline,
)
from .daz_hair_data import DAZHairStrand
class CurveHairImporter:
    """
    Blender Curve Hair importer
    Blender Curve
        |
        +-- spline
        |
        +-- points
        |
        v
    DAZHairStrand
        |
        +-- vertices
        +-- weights
    """
    def __init__(
        self,
        obj:bpy.types.Object
    ):
        if obj.type != "CURVE":
            raise TypeError(
                "CurveHairImporter requires CURVE object"
            )
        self.obj=obj
        self.segments=0
    ##################################################
    # extract
    ##################################################
    def extract(
        self,
        root_mapping:list[int],
        segments
    ):
        result=[]
        self.segments=segments
        curve=cast(bpy.types.Curve,self.obj.data)
        spline_count=len(
            curve.splines
        )
        if len(root_mapping)!=spline_count:
            raise RuntimeError(
                f"Curve spline count {spline_count} "
                f"!= root mapping {len(root_mapping)}"
            )
        for index,spline in enumerate(
            curve.splines
        ):
            scalp_index=root_mapping[index]
            if scalp_index < 0:
                continue
            vertices=self.sample_spline(
                spline,
                segments
            )
            if len(vertices)<2:
                continue
            weights=self.build_default_weights(
                len(vertices)
            )
            strand=DAZHairStrand()
            strand.scalp_index=scalp_index
            strand.root=vertices[0]
            strand.vertices=vertices
            strand.weights=weights
            result.append(
                strand
            )
        return result
    ##################################################
    # sample spline
    ##################################################
    def sample_spline(
        self,
        spline,
        segments
    ):
        """
        Sample one spline into ``segments`` evenly spaced points.

        BEZIER splines are evaluated through every segment (handles
        included) and then resampled by arc length, so all strands get
        the same point count regardless of their control point density.
        """
        count=max(2,int(segments))
        points=sample_spline_polyline(spline)
        if len(points)<2:
            return []
        points=resample_polyline(points,count)
        #
        # local -> world
        #
        return [
            self.obj.matrix_world @ p
            for p in points
        ]
    ##################################################
    # default rigidity
    ##################################################
    def build_default_weights(
        self,
        count
    ):
        weights=[]
        for i in range(count):
            if i==0:
                w=1.0
            else:
                t=i/(count-1)
                #
                # root -> tip
                #
                w=(
                    1.0-t
                )
            weights.append(
                w
            )
        return weights
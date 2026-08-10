from typing import cast

import bpy
from mathutils import Vector
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
        points=[]
        #
        # Bezier
        #
        if spline.type=="BEZIER":
            points=self.sample_bezier(
                spline,
                segments
            )
        #
        # Poly
        #
        else:
            src=[]
            for p in spline.points:
                src.append(
                    Vector(
                        (
                            p.co.x,
                            p.co.y,
                            p.co.z
                        )
                    )
                )
            points=self.resample_polyline(
                src,
                segments
            )
        #
        # local -> world
        #
        return [
            self.obj.matrix_world @ p
            for p in points
        ]
    ##################################################
    # Bezier sampling
    ##################################################
    def sample_bezier(
        self,
        spline,
        count
    ):
        points=[]
        bezier=spline.bezier_points
        if len(bezier)<2:
            return points
        p0=bezier[0]
        p3=bezier[-1]
        for i in range(count):
            t=i/(count-1)
            a=(
                p0.co *
                (1-t)**3
            )
            b=(
                p0.handle_right *
                3 *
                (1-t)**2 *
                t
            )
            c=(
                p3.handle_left *
                3 *
                (1-t) *
                t*t
            )
            d=(
                p3.co *
                t**3
            )
            points.append(
                a+b+c+d
            )
        return points
    ##################################################
    # Polyline resample
    ##################################################
    def resample_polyline(
        self,
        points,
        count
    ):
        if len(points)<2:
            return points
        result=[]
        total=len(points)-1
        for i in range(count):
            t=i/(count-1)
            pos=t*total
            index=int(pos)
            factor=pos-index
            if index>=total:
                result.append(
                    points[-1]
                )
            else:
                result.append(
                    points[index].lerp(
                        points[index+1],
                        factor
                    )
                )
        return result
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
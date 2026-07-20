import os
from typing import cast
import bpy
from mathutils import Vector
from ..reader.daz_surface_normals import load_surface_normals
from .wrap_types import (
    BaseMeshData,
    MeshtoUVMapping,
    MeshPoly
)
from collections import defaultdict
from ..paths import PLUGIN_ROOT

def build_base_mesh(
    mesh: bpy.types.Mesh,
) -> BaseMeshData:
    base_vertices = [
        v.co.copy()
        for v in mesh.vertices
    ]
    base_poly_list = []
    for poly in mesh.polygons:
        base_poly_list.append(
            MeshPoly(
                materialNum=poly.material_index,
                vertices=list(poly.vertices) # type: ignore
            )
        )

    return BaseMeshData(
        base_vertices=base_vertices,
        base_poly_list=base_poly_list
    )
def update_duplicate_uv_normals(
    base_normals: list[Vector],
    vertex_maps: list[MeshtoUVMapping],
    uv_vertex_count: int,
) -> list[Vector]:
    """
    Official:
    _morphedUVNormals
    _updateDuplicateMorphedUVNormals()
    """
    #
    # Pre-BaseVertex section
    #
    uv_normals = [
        n.copy()
        for n in base_normals
    ]
    #
    # If UVVertex is more than BaseVertex
    #
    if len(uv_normals) < uv_vertex_count:
        uv_normals.extend(
            Vector((0,0,1))
            for _ in range(
                uv_vertex_count-len(uv_normals)
            )
        )
    #
    # Official:
    #
    # duplicate UV normals
    #
    for vm in vertex_maps:
        src=uv_normals[vm.fromvert]
        uv_normals[vm.tovert]=src.copy()
    return uv_normals
def build_uv_mesh(
    mesh: bpy.types.Mesh,
    uv_layer: bpy.types.MeshUVLoopLayer,
):
    base_vertex_count = len(mesh.vertices)
    #
    # UVVertices
    #
    uv_vertices = [
        mesh.vertices[i].co.copy()
        for i in range(base_vertex_count)
    ]
    #
    # OrigUV
    #
    orig_uv = [
        Vector((0.0, 0.0))
        for _ in range(base_vertex_count)
    ]
    #
    # VertexMap
    #
    vertex_maps = []
    #
    # (baseIndex,u,v)->uvIndex
    #
    uv_map = {}
    #
    # first uv vertex of base vertex
    #
    first_uv = {}
    #
    # UV PolyList
    #
    uv_poly_list = []
    #
    # build
    #
    for poly in mesh.polygons:
        uv_indices = []
        for loop_index in poly.loop_indices:
            loop = mesh.loops[loop_index]
            base_index = loop.vertex_index
            uv = uv_layer.data[loop_index].uv
            key = (
                base_index,
                round(uv.x, 8),
                round(uv.y, 8),
            )
            #
            # already exists
            #
            if key in uv_map:
                uv_index = uv_map[key]
            else:
                #
                # first uv vertex
                #
                if base_index not in first_uv:
                    uv_index = base_index
                    first_uv[base_index] = uv_index
                    uv_map[key] = uv_index
                    orig_uv[uv_index] = uv.copy()
                #
                # duplicated uv vertex
                #
                else:
                    uv_index = len(uv_vertices)
                    uv_map[key] = uv_index
                    #
                    # DAZ:
                    # duplicate vertex position
                    #
                    uv_vertices.append(
                        mesh.vertices[base_index].co.copy()
                    )
                    orig_uv.append(
                        uv.copy()
                    )
                    vertex_maps.append(
                        MeshtoUVMapping(
                            fromvert=first_uv[base_index],
                            tovert=uv_index,
                            polyindex=poly.index,
                        )
                    )
            uv_indices.append(uv_index)
        uv_poly_list.append(
            MeshPoly(
                materialNum=poly.material_index,
                vertices=uv_indices,
            )
        )
    #
    # Official:
    # duplicate positions
    #
    for vm in vertex_maps:
        uv_vertices[vm.tovert] = uv_vertices[vm.fromvert].copy()

    return (
        uv_vertices,
        orig_uv,
        vertex_maps,
        uv_poly_list,
    )
from collections import defaultdict
def recover_vertex_normal(
    uv_index,
    uv_triangles,
    surface_normals
):
    for i in range(0,len(uv_triangles),3):
        if uv_index in uv_triangles[i:i+3]:
            return surface_normals[i//3].copy()
    return None
def flatten_material_triangles(
    material_triangles:list[list[int]]
)->list[int]:
    result=[]
    for tris in material_triangles:
        result.extend(tris)
    return result
def poly_list_to_triangle_indexes(
    poly_list: list[MeshPoly],
    split_material: bool = False
)->list[int]|list[list[int]]:
    """
    DAZMesh.PolyListToTriangleIndexes
    return:
        split_material=False:
            list[int]
        split_material=True:
            list[list[int]]
    """
    material_triangles = defaultdict(list)
    for poly in poly_list:
        verts = poly.vertices
        if len(verts) < 3:
            continue
        material = poly.materialNum
        #
        # Triangle Fan
        #
        root = verts[0]
        for i in range(1, len(verts)-1):
            material_triangles[material].extend(
                [
                    root,
                    verts[i],
                    verts[i+1]
                ]
            )
    #
    # Material grouping is not required
    #
    if not split_material:
        triangles:list[int]|list[list[int]]=[]
        for mat in sorted(material_triangles.keys()):
            triangles.extend(
                material_triangles[mat]
            )
        return triangles
    #
    # Material SubMesh mode
    #
    max_material=max(material_triangles.keys(),default=-1)
    result: list[int]|list[list[int]]=[
        []
        for _ in range(max_material+1)
    ]
    for mat,tri in material_triangles.items():
        result[mat]=tri
    return result

def calculate_surface_normals(
    vertices: list[Vector],
    triangles: list[int]
) -> list[Vector]:
    surface_normals=[]
    for i in range(0,len(triangles),3):
        v1=vertices[triangles[i]]
        v2=vertices[triangles[i+1]]
        v3=vertices[triangles[i+2]]
        n=cast(Vector,(v2-v1).cross(v3-v1))
        #
        # DAZ:
        # Degenerate triangle
        #
        if n.length_squared < 1e-12:
            n = Vector((0,0,0))
        surface_normals.append(n)
    return surface_normals

def calculate_vertex_normals(
    vertex_count: int,
    triangles: list[int],
    surface_normals: list[Vector],
    EPS:float = 1e-12,
) -> list[Vector]:
    normals = [
        Vector((0.0,0.0,0.0))
        for _ in range(vertex_count)
    ]
    marker = [
        False
        for _ in range(vertex_count)
    ]
    ##################################################
    # Build vertex -> triangles map
    ##################################################
    vertex_triangles = [
        []
        for _ in range(vertex_count)
    ]
    for tri_id in range(
        len(surface_normals)
    ):
        i = tri_id * 3
        a = triangles[i]
        b = triangles[i+1]
        c = triangles[i+2]
        vertex_triangles[a].append(tri_id)
        vertex_triangles[b].append(tri_id)
        vertex_triangles[c].append(tri_id)
    ##################################################
    # Accumulate normals
    ##################################################
    for tri_id,n in enumerate(surface_normals):
        i = tri_id * 3
        a = triangles[i]
        b = triangles[i+1]
        c = triangles[i+2]
        if not marker[a]:
            normals[a]=n.copy()
            marker[a]=True
        else:
            normals[a]+=n
        if not marker[b]:
            normals[b]=n.copy()
            marker[b]=True
        else:
            normals[b]+=n
        if not marker[c]:
            normals[c]=n.copy()
            marker[c]=True
        else:
            normals[c]+=n
 
    ##################################################
    # fallback
    ##################################################
    for i in range(vertex_count):
        if not marker[i]:
            if i>0:
                normals[i]=normals[i-1].copy()
            else:
                normals[i]=Vector((0,0,1))
        elif normals[i].length_squared < EPS:
            if i>0:
                normals[i]=normals[i-1].copy()
            else:
                normals[i]=Vector((0,0,1))
    return normals

def recalculate_normals(
    triangles: list[int],
    vertices: list[Vector],
    is_body: bool,
) -> tuple[list[Vector], list[Vector]]:
    """
    Complete correspondence:
    is_body: bool = True read surfaceNormals.bin, use it for human surfaceNormals
    is_body: bool = False Generate new surfaceNormals for clothing mesh
    """
    surface_normals:list[Vector]=[]
    if is_body:
        target_path = os.path.join(PLUGIN_ROOT,"DAZExtraData", "surfaceNormals.bin")
        if not os.path.exists(target_path):
            raise RuntimeError("surfaceNormals.bin file not found: {target_path}\nPlease check if the file exists!")
        surface_normals = load_surface_normals(target_path)
    else:
        surface_normals = calculate_surface_normals(
            vertices,
            triangles
        )

    vertex_normals = calculate_vertex_normals(
        len(vertices),
        triangles,
        surface_normals
    )
    return (
        vertex_normals,
        surface_normals,
    )
def recalculate_tangents_fast(
    triangles: list[int],
    vertices: list[Vector],
    normals: list[Vector],
    uv: list[Vector],
):
    """
    Python port of:
    RecalculateTangents.recalculateTangentsFast()
    DAZ / VaM version
    """
    num_vertices = len(vertices)
    #
    # Vector4 replacement
    #
    tangents = [
        Vector((0.0,0.0,0.0,0.0))
        for _ in range(num_vertices)
    ]
    #
    # markerArray
    #
    marker = [
        False
        for _ in range(num_vertices)
    ]
    #
    # Triangle pass
    #
    for i in range(0,len(triangles),3):
        i1 = triangles[i]
        i2 = triangles[i+1]
        i3 = triangles[i+2]
        #
        # Position delta
        #
        x1 = vertices[i2].x - vertices[i1].x
        y1 = vertices[i2].y - vertices[i1].y
        z1 = vertices[i2].z - vertices[i1].z
        x2 = vertices[i3].x - vertices[i1].x
        y2 = vertices[i3].y - vertices[i1].y
        z2 = vertices[i3].z - vertices[i1].z
        #
        # UV delta
        #
        s1 = uv[i2].x - uv[i1].x
        s2 = uv[i3].x - uv[i1].x
        t1 = uv[i2].y - uv[i1].y
        t2 = uv[i3].y - uv[i1].y
        #
        # determinant
        #
        det = s1*t2 - s2*t1
        #
        # Official:
        #
        # if(num20==0)
        #     num20=0.0001f
        #
        if det == 0:
            det = 0.0001
        r = 1.0 / det
        #
        # tangent
        #
        tx = (
            (t2*x1 - t1*x2)
            *
            r
        )
        ty = (
            (t2*y1 - t1*y2)
            *
            r
        )
        tz = (
            (t2*z1 - t1*z2)
            *
            r
        )
        tangent = Vector(
            (
                tx,
                ty,
                tz
            )
        )
        #
        # accumulate
        #
        for index in (i1,i2,i3):
            if not marker[index]:
                marker[index]=True
                tangents[index].x = tx
                tangents[index].y = ty
                tangents[index].z = tz
            else:
                tangents[index].x += tx
                tangents[index].y += ty
                tangents[index].z += tz
    #
    # Normalize
    # Gram-Schmidt
    #
    for k in range(num_vertices):
        if not marker[k]:
            continue
        n = normals[k]
        t = tangents[k]
        #
        # dot(normal,tangent)
        #
        dot = (
            n.x*t.x+
            n.y*t.y+
            n.z*t.z
        )
        #
        # tangent orthogonalize
        #
        tangent = Vector(
            (
                t.x - n.x*dot,
                t.y - n.y*dot,
                t.z - n.z*dot
            )
        )
        #
        # normalize
        #
        # if tangent.length > 1e-12:
        #     tangent.normalize()
        # else:
        #     tangent = Vector(
        #         (1,0,0)
        #     )
        #
        # official:
        #
        # tangents[k].w=-1
        #
        tangents[k].x = tangent.x
        tangents[k].y = tangent.y
        tangents[k].z = tangent.z
        tangents[k].w = -1.0
        marker[k]=False
    return tangents

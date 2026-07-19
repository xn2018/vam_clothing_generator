from dataclasses import dataclass, field
from typing import Optional, Sequence
import bpy
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
from mathutils import Matrix, Vector
# ============================================================
# Triangle Info
# ============================================================
@dataclass
class SkinWrapVertex:
    closestTriangle:int
    Vertex1:int
    Vertex2:int
    Vertex3:int
    surfaceNormalProjection:float
    surfaceTangent1Projection:float
    surfaceTangent2Projection:float
    surfaceNormalWrapNormalDot:float
    surfaceTangent1WrapNormalDot:float
    surfaceTangent2WrapNormalDot:float
@dataclass(slots=True)
class TriangleInfo:
    #
    # Triangle ID (corresponding to closestTriangle)
    #
    triangle_id: int
    original_triangle_id:int
    #
    # UV Vertex Indices
    #
    vertex1: int
    vertex2: int
    vertex3: int
    #
    # Vertex Positions
    #
    v1: Vector
    v2: Vector
    v3: Vector
    #
    # Cached
    #
    center: Vector
    normal: Vector
@dataclass(slots=True)
class UVTriangleInfo:
    triangle_id:int
    vertex1:int
    vertex2:int
    vertex3:int
    center:Vector
    normal:Vector
    material:int
# ============================================================
# MeshPoly
# ============================================================
@dataclass(slots=True)
class MeshPoly:
    materialNum: int
    vertices: list[int]
# ============================================================
# Genesis Mesh Cache
# ============================================================
@dataclass
class MeshtoUVMapping:
    fromvert:int
    tovert:int
    polyindex:int
@dataclass(slots=True)
class DAZMeshData:
    #=========================================================
    # Original Mesh
    #=========================================================
    base_vertices: list[Vector] = field(default_factory=list)
    uv_vertices: list[Vector] = field(default_factory=list)
    orig_uv: list[Vector] = field(default_factory=list)
    vertex_maps: list[MeshtoUVMapping] = field(default_factory=list)
    base_poly_list: list[MeshPoly] = field(default_factory=list)
    uv_poly_list: list[MeshPoly] = field(default_factory=list)
    base_vertex_count:int = 0
    uv_vertex_count:int = 0
    base_polygon_count:int = 0
    uv_polygon_count:int = 0
    base_material_vertices: list[list[int]] = field(default_factory=list)
    #=========================================================
    # Derived Triangles
    #=========================================================
    base_triangles: list[int] = field(default_factory=list)
    uv_triangles: list[int] = field(default_factory=list)
    #=========================================================
    # Base Normals
    #=========================================================
    base_normals: list[Vector] = field(default_factory=list)
    base_surface_normals: list[Vector] = field(default_factory=list)
    #=========================================================
    # Morphed Base
    #=========================================================
    morphed_base_vertices: list[Vector] = field(default_factory=list)
    morphed_base_normals: list[Vector] = field(default_factory=list)
    morphed_base_surface_normals: list[Vector] = field(default_factory=list)
    #=========================================================
    # UV Mesh
    #=========================================================
    uv_normals: list[Vector] = field(default_factory=list)
    uv_tangents: list[Vector] = field(default_factory=list)
    #=========================================================
    # Morphed UV
    #=========================================================
    morphed_uv_vertices: list[Vector] = field(default_factory=list)
    visible_morphed_uv_vertices: list[Vector] = field(default_factory=list)
    smoothed_morphed_uv_vertices: list[Vector] = field(default_factory=list)
    morphed_uv_normals: list[Vector] = field(default_factory=list)
    morphed_uv_tangents: list[Vector] = field(default_factory=list)
    #=========================================================
    # Dirty Flags
    #=========================================================
    morphed_base_dirty_vertices: list[bool] = field(default_factory=list)
    morphed_uv_dirty_vertices: list[bool] = field(default_factory=list)
    matrix_world: Matrix = field(default_factory=Matrix)
@dataclass(slots=True)
class UVMeshBuildResult:
    uv_vertices:list[Vector]
    orig_uv:list[Vector]
    vertex_maps:list[MeshtoUVMapping]
    uv_poly_list:list[MeshPoly]
@dataclass(slots=True)
class SkinWrapCache:
    object_name: str = ""
    #
    # Genesis body mesh
    #
    body_mesh: Optional[DAZMeshData] = None
    #
    # Clothing mesh
    # Corresponds to the DAZSkinWrapStore wrap source
    #
    cloth_mesh: Optional[DAZMeshData] = None
    #
    # Body triangle cache
    #
    body_triangles: list[TriangleInfo] = field(default_factory=list)
    #
    # BVH
    #
    bvh: Optional[BVHTree] = None
    body_bvh: Optional[BVHTree] = None
    bvh_to_triangle: list[int] = field(default_factory=list)
    #
    # Triangle center KDTree
    #
    center_tree: Optional[BVHTree] = None
    #
    # anchor
    #
    anchor_vertices:set[int] = field(
        default_factory=set
    )
    anchor_triangles:list[TriangleInfo] = field(
        default_factory=list
    )
    anchor_bvh: BVHTree | None = None
    #
    # Statistics
    #
    vertex_count:int = 0
    triangle_count:int = 0
    mesh_pointer:int = 0
    initialized:bool=False
@dataclass(slots=True)
class BaseMeshData:
    base_vertices: list[Vector]
    base_poly_list: list[MeshPoly]
# ============================================================
# VertexMap
#
# The current Genesis.obj is already UVVertex,
# so clothing typically does not produce UV splits.
# Keep this structure only for compatibility with the official DAZMesh.
# ============================================================
@dataclass(slots=True)
class DAZVertexMap:
    fromvert: int
    tovert: int
    polyindex: int
# ============================================================
# DAZTopology
# ============================================================
@dataclass(slots=True)
class DAZTopology:
    #
    # Object
    #
    object: bpy.types.Object
    #
    # Mesh
    #
    data: bpy.types.Mesh
    #
    # Name
    #
    name: str
    #
    # Base Vertices
    #
    base_vertices: list[Vector] = field(default_factory=list)
    #
    # Base Polygon List
    #
    base_poly_list: list[MeshPoly] = field(default_factory=list)
    uv_vertices: list[Vector] = field(default_factory=list)
    uv_poly_list: list[MeshPoly] = field(default_factory=list)
    orig_uv: list[Vector] = field(default_factory=list)
    vertex_maps: list[DAZVertexMap] = field(default_factory=list)
@dataclass
class UVVerticesData:
    #
    # Base Mesh
    #
    BaseVertices:list[Vector]
    BasePolyList:list[MeshPoly]
    BaseTriangles:list[int]
    #
    # UV Mesh
    #
    UVVertices:list[Vector]
    UVPolyList:list[MeshPoly]
    UVTriangles:list[int]
    #
    # Mapping
    #
    vertex_maps:list[MeshtoUVMapping]
    orig_uv:list[Vector]
    #
    # Normals
    #
    BaseNormals:list[Vector]
    BaseSurfaceNormals:list[Vector]
    UVNormals:list[Vector]
@dataclass(slots=True)
class WrapInputVertex:
    #
    # DAZ UV Vertex Index
    #
    index:int
    #
    # UV mapped position
    #
    co:Vector
    #
    # UV normal
    #
    normal:Vector
    #
    # optional tangent
    #
    tangent:Vector|None = None
@dataclass(slots=True)
class DAZBuildResult:
    mesh: DAZMeshData
    topology: DAZTopology

@dataclass(slots=True)
class WorkerTriangle:
    triangle_id:int
    original_triangle_id:int
    vertex1:int
    vertex2:int
    vertex3:int
    v1:tuple[float,float,float]
    v2:tuple[float,float,float]
    v3:tuple[float,float,float]
    center:tuple[float,float,float]
    normal:tuple[float,float,float]
@dataclass(slots=True)
class WorkerBVHData:
    triangles:list[WorkerTriangle]
    anchor_triangles:list[WorkerTriangle]
# ============================================================
# Data Types
# ============================================================
@dataclass
class WorkerWrapVertex:
    index:int
    co:tuple
    normal:tuple

@dataclass(slots=True)
class PerSkinWrapCalculationResult:
    wrap_vertices:list[WrapInputVertex]
    clothing_mesh:DAZMeshData
    local_matrix:Matrix
    normal_matrix:Matrix
    anchor_only:bool=False
    wrap_check_normals:bool=False
    max_wrap_distance:float=1.0
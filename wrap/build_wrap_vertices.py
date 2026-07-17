from .wrap_types import WrapInputVertex
from .wrap_types import DAZMeshData
# ============================================================
# Build Wrap Vertices
#
# Equivalent:
#
# DAZMesh._UVVertices
# DAZMesh._UVNormals
#
# One WrapVertex == One UVVertex
#
# ============================================================
def build_wrap_vertices(
    mesh:DAZMeshData
)->list[WrapInputVertex]:
    count=len(mesh.uv_vertices)
    if len(mesh.uv_normals)!=count:
        raise RuntimeError("UVVertices / UVNormals count mismatch")
    if mesh.uv_tangents:
        if len(mesh.uv_tangents)!=count:
            raise RuntimeError("UVVertices / UVTangents count mismatch")
    results=[]
    for i in range(count):
        tangent=None
        if mesh.uv_tangents:
            tangent=mesh.uv_tangents[i].copy()
        results.append(
            WrapInputVertex(
                index=i,
                co=mesh.uv_vertices[i].copy(),
                normal=mesh.uv_normals[i].copy(),
                tangent=tangent
            )
        )

    return results
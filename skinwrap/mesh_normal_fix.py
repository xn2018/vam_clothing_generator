def flip_triangle_winding(
    mesh_data,
    triangle_ids
):
    triangles = mesh_data.base_triangles
    for tid in triangle_ids:
        i=tid*3
        a=triangles[i]
        b=triangles[i+1]
        c=triangles[i+2]
        triangles[i]=a
        triangles[i+1]=c
        triangles[i+2]=b
        
def find_flipped_triangles(
    mesh_data
):
    result=[]
    verts=mesh_data.base_vertices
    tris=mesh_data.base_triangles
    uvs=mesh_data.uv_vertices
    for i in range(
        0,
        len(tris),
        3
    ):
        tid=i//3
        a=tris[i]
        b=tris[i+1]
        c=tris[i+2]
        p1=verts[a]
        p2=verts[b]
        p3=verts[c]
        n=(
            p2-p1
        ).cross(
            p3-p1
        )
        uv1=uvs[a]
        uv2=uvs[b]
        uv3=uvs[c]
        uv_cross=(
            (uv2-uv1).x *
            (uv3-uv1).y
            -
            (uv2-uv1).y *
            (uv3-uv1).x
        )
        if n.z * uv_cross <0:
            result.append(tid)
    return result
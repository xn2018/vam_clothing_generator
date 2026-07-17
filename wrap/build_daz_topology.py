import bpy

from .wrap_types import DAZTopology, MeshPoly


# ============================================================
# Build DAZ Topology
# ============================================================

def build_daz_topology(obj)->DAZTopology:

    depsgraph=bpy.context.evaluated_depsgraph_get()
    eval_obj=obj.evaluated_get(depsgraph)
    mesh=eval_obj.to_mesh()

    if mesh is None:
        raise RuntimeError("No mesh")


    persistent_mesh=mesh.copy()

    topology=DAZTopology(
        object=obj,
        data=persistent_mesh,
        name=obj.name
    )

    #
    # base vertices
    #

    topology.base_vertices=[
        v.co.copy()
        for v in mesh.vertices
    ]


    #
    # base polygons
    #

    for poly in mesh.polygons:

        topology.base_poly_list.append(
            MeshPoly(
                materialNum=poly.material_index,
                vertices=list(poly.vertices)
            )
        )


    eval_obj.to_mesh_clear()


    print("======== DAZ Topology ========")
    print("Vertices:",len(topology.base_vertices))
    print("Faces:",len(topology.base_poly_list))


    return topology
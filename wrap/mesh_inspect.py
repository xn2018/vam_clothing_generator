# ============================================================
# Genesis Mesh Inspection
#
# Read-only helpers shared by the SkinWrap cache builder and the
# cache validator.
#
# They intentionally read ``obj.data`` (the original mesh, not the
# evaluated depsgraph mesh), because build_daz_mesh() also reads
# ``obj.data``.  Reading the evaluated mesh here would make vertex
# indices / triangle order diverge from DAZMeshData.base_vertices.
#
# IMPORTANT
# ---------
# This module must stay dependency-free (bpy + stdlib only).
# bvh_wrap imports build_mesh_cache_from_object(), so those two can
# not import each other.  Both import the helpers below instead,
# which keeps the import graph acyclic.
# ============================================================
import hashlib
from array import array

import bpy

# ------------------------------------------------------------
# Vertex group marking the body region the clothing may wrap to
# (the skin covered by the cloth).  Only body triangles whose three
# vertices are all inside this group are used when anchor_only is
# enabled, see bvh_wrap.build_anchor_triangle_cache().
# ------------------------------------------------------------
ANCHOR_GROUP_NAME = "anchor"

# Weight threshold used by DAZ and by the original inline
# implementation: a vertex belongs to the group when its weight is
# strictly greater than this value.
ANCHOR_WEIGHT_THRESHOLD = 0.001


def collect_anchor_vertices(
    genesis_obj: bpy.types.Object | None,
    group_name: str = ANCHOR_GROUP_NAME,
    weight_threshold: float = ANCHOR_WEIGHT_THRESHOLD,
) -> set[int]:
    """
    Collect the vertex indices of the Genesis anchor vertex group.

    Parameters
    ----------
    genesis_obj:
        Genesis body object.  ``None`` is tolerated so callers do not
        have to special-case an unassigned UI slot.
    group_name:
        Vertex group name, ``"anchor"`` by default.
    weight_threshold:
        Minimum weight (exclusive) for a vertex to be considered part
        of the group.

    Returns
    -------
    set[int]
        Indices into ``genesis_obj.data.vertices``.  The set is empty
        when the object is missing, is not a mesh, has no such vertex
        group, or the group only contains zero weights.  Callers are
        expected to fall back to the full body BVH in that case
        (see SkinWrapTask.build_calc_data).

    Notes
    -----
    * The returned indices are indices of ``obj.data`` (the rest
      mesh).  They therefore stay aligned with
      ``DAZMeshData.base_vertices`` and ``SkinWrapCache.body_triangles``,
      both of which are built from the same data.
    * ``vertex.groups`` only holds the groups the vertex actually
      belongs to, and a vertex references a given group at most once,
      hence the ``break``.  The scan is O(vertices x groups per
      vertex), not O(vertices x all groups).
    * Call this in Object Mode.  Weight-paint edits are flushed to
      ``obj.data`` immediately, but vertex edits made in Edit Mode are
      not and would be missed.
    * A different group name can be passed for future UI support; the
      rest of the pipeline currently assumes ``"anchor"``.
    """
    anchor: set[int] = set()

    if genesis_obj is None:
        return anchor

    mesh = genesis_obj.data
    #
    # Only Mesh objects have vertex groups (guard against Curve,
    # which is used as hair object in the hair pipeline).
    #
    if not isinstance(mesh, bpy.types.Mesh):
        return anchor

    group = genesis_obj.vertex_groups.get(group_name)
    if group is None:
        return anchor

    group_index = group.index
    threshold = float(weight_threshold)

    for vertex in mesh.vertices:
        for element in vertex.groups:
            if element.group != group_index:
                continue
            if element.weight > threshold:
                anchor.add(vertex.index)
            break

    return anchor


def get_anchor_signature(
    genesis_obj: bpy.types.Object | None
) -> tuple[int, ...]:
    """
    Order-independent identity of the anchor group content.

    Two states of the object that produce the same signature produce
    exactly the same anchor_triangles / anchor_bvh, so the cache does
    not have to be rebuilt.
    """
    return tuple(
        sorted(
            collect_anchor_vertices(genesis_obj)
        )
    )


def geometry_signature(obj: bpy.types.Object) -> tuple:
    """
    Cheap identity of everything that changes the cached triangle table.

    Covers what object name + vertex count alone can not catch:

    * mesh datablock replacement (``as_pointer``),
    * vertex moves / shape edits (coordinate hash),
    * topology edits that keep the vertex count (polygon count),
    * material reassignment, which reorders the material-grouped
      triangle list and therefore breaks the 1:1 mapping onto
      ``DAZExtraData/surfaceNormals.bin`` (material index hash).
    """
    mesh = obj.data
    if not isinstance(mesh, bpy.types.Mesh):
        raise TypeError(
            "geometry_signature() expects a mesh object, "
            f"got {getattr(obj, 'type', '?')!r} "
            f"on {getattr(obj, 'name', '?')!r}"
        )

    co = array("f", [0.0]) * (len(mesh.vertices) * 3)
    mesh.vertices.foreach_get("co", co)

    mat = array("i", [0]) * len(mesh.polygons)
    mesh.polygons.foreach_get("material_index", mat)

    return (
        mesh.as_pointer(),
        len(mesh.vertices),
        len(mesh.polygons),
        len(mesh.materials),
        hashlib.blake2b(co.tobytes(), digest_size=8).hexdigest(),
        hashlib.blake2b(mat.tobytes(), digest_size=8).hexdigest(),
    )

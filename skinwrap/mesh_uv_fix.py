def fix_uv_tangent_winding(
    tangents,
    affected_uv
):

    for index in affected_uv:

        if index >= len(tangents):
            print(
                "INVALID UV INDEX",
                index
            )
            continue

        tangents[index].w *= -1


    return tangents
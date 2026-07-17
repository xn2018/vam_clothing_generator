import struct
from mathutils import Vector


def load_surface_normals(path):

    normals=[]

    with open(path,"rb") as f:

        count=struct.unpack(
            "<i",
            f.read(4)
        )[0]


        for _ in range(count):

            x,y,z=struct.unpack(
                "<fff",
                f.read(12)
            )

            normals.append(
                Vector((x,y,z))
            )

    return normals
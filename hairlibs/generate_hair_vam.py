import os
import json


def generate_hair_vam(
        props,
        output_dir):

    vam = {
        "itemType":props.package_type,
        "uid":f"{props.author_name}:{props.clothing_hair_id}",
        "displayName":props.clothing_hair_id,
        "creatorName":props.author_name,
        "tags":"hairs"
    }

    path = os.path.join(
        output_dir,
        props.clothing_hair_id + ".vam"
    )

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            vam,
            f,
            indent=4
        )

    print(
        "[VAM]",
        path
    )
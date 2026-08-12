import os
from ..hairlibs.hair_vab_writer import vab_hair_file_writer
def generate_hair_vab(
        genesis,
        hair_obj,
        hair_id,
        hair_data,
        author_name,
        output_dir
):
    if hair_data is None:
        raise Exception(
            "DAZHairData missing"
        )
    print("")
    print("==============================")
    print("Generating Hair VAB")
    print("==============================")
    #
    # prepare scalp provider
    #
    if not hair_data.scalp_provider_name:
        hair_data.scalp_provider_name = (
            genesis.name
        )
    #
    # filename
    #
    filename = (
        hair_id +
        ".vab"
    )
    output_path = os.path.join(
        output_dir,
        filename
    )
    #
    # write vab
    #
    vab_hair_file_writer(
        filepath=output_path,
        hair_data=hair_data
    )
    print(
        "[VAB]",
        output_path
    )
    return output_path
import os
from .hair_vab_writer import vab_hair_file_writer
def generate_hair_vab(
        genesis,
        hair_obj,
        hair_id,
        hair_data,
        author_name,
        output_dir
):
    if genesis is None:
        raise Exception(
            "Genesis object not selected"
        )
    if hair_obj is None:
        raise Exception(
            "Hair curve object not selected"
        )
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
        genesis=genesis,
        hair_obj=hair_obj,
        hair_data=hair_data,
        author_name=author_name,
        hair_id=hair_id
    )
    print(
        "[VAB]",
        output_path
    )
    return output_path
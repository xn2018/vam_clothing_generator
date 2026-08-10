import json
import os
from pathlib import Path
def build_hair_material(
        prefix,
        hair_data,
        props
):
    return {
        "id":
            f"{prefix}{hair_data.material_name}",
        "renderQueue":
            "2423",
        "Specular Texture Offset":
            "0",
        "Specular Intensity":
            "0",
        "Gloss":
            "3.2",
        "Specular Fresnel":
            "0.5",
        "Gloss Texture Offset":
            "0",
        "Global Illumination Filter":
            "0.5",
        "Alpha Adjust":
            "0",
        "Diffuse Texture Offset":
            "1",
        "simTexture":
            "",
        "Diffuse Color":
        {
            "h":"0.1",
            "s":"0.6",
            "v":"0.1"
        },
        "Specular Color":
        {
            "h":"0",
            "s":"0",
            "v":"0.13"
        },
        "Subsurface Color":
        {
            "h":"0",
            "s":"0",
            "v":"0"
        }
    }
def generate_hair_vaj(
        hair_data,
        props,
        output_dir
):
    """
    Generate VaM Hair VAJ
    props:
        author_name
        hair_id
        enable_plugin
        plugin_path
    """
    clothing_hair_id = props.clothing_hair_id
    prefix = clothing_hair_id
    storables=[]
    # ==================================================
    # Sim
    # ==================================================
    storables.append(
    {
        "id":
            f"{prefix}Sim",
        "styleModeShowCurls":"false",
        "styleModeShowTool1":"true",
        "styleModeShowTool2":"true",
        "styleModeShowTool3":"false",
        "styleModeShowTool4":"false",
        "simulationEnabled":"true",
        "collisionEnabled":"true",
        "curlAllowReverse":"true",
        "curlAllowFlipAxis":"true",
        "styleJointsSearchDistance":"0.01",
        "styleModeCollisionRadius":"0.004",
        "styleModeCollisionRadiusRoot":"0.002",
        "styleModeGravityMultiplier":"0",
        "collisionRadius":"0.008",
        "collisionRadiusRoot":"0.004",
        "rootRigidity" : "0.5464537", 
        "mainRigidity" : "0.5692537", 
        "tipRigidity" : "0", 
        "rigidityRolloffPower" : "5.591662",
        "drag":"0.1",
        "friction":"0.2",
        "gravityMultiplier":"1",
        "weight":"1.5",
        "iterations":"2",
        "cling":"0.7",
        "clingRolloff":"1",
        "snap":"0.2",
        "bendResistance":"0.2",
        #
        # render
        #
        "colorRolloff":"3",
        "diffuseSoftness":"0.1",
        "primarySpecularSharpness":"160",
        "secondarySpecularSharpness":"64",
        "specularShift":"0.4",
        "fresnelPower":"8",
        "fresnelAttenuation":"0.2",
        "randomColorPower":"2",
        "randomColorOffset":"0.3",
        "IBLFactor":"0.5",
        "normalRandomize":"0.8",
        #
        # curl
        #
        "curlX":"0",
        "curlY":"0",
        "curlZ":"0",
        "curlScale":"0",
        "curlScaleRandomness":"1",
        "curlFrequency":"1",
        "curlFrequencyRandomness":"1",
        "curlNormalAdjust":"0",
        "curlRoot":"0",
        "curlMid":"1",
        "curlTip":"1",
        "curlMidpoint":"1",
        "curlCurvePower":"1",
        #
        # length
        #
        "length1":"1",
        "length2":"1",
        "length3":"1",
        #
        # density
        #
        "width":"0.0001",
        "curveDensity" : "32", 
        "hairMultiplier" : "16", 
        #
        # spread
        #
        "maxSpread":"0.025",
        "spreadRoot":"1",
        "spreadMid":"1",
        "spreadTip":"1",
        "spreadMidpoint":"0.5",
        "spreadCurvePower":"1",
        "wind":
        [
            "0",
            "0",
            "0"
        ],
        "shaderType":"Quality",
        "rootColor":
        {
            "h":"0.07936508",
            "s":"0.9130435",
            "v":"0.09019608"
        },
        "tipColor":
        {
            "h":"0.07912458",
            "s":"0.6827586",
            "v":"0.5686275"
        },
        "specularColor":
        {
            "h":"0",
            "s":"0",
            "v":"0.6666667"
        }
    })
    # ==================================================
    # Creator
    # ==================================================
    storables.append(
        {
            "id":
            f"{prefix}Creator"
        }
    )
    # ==================================================
    # ItemControl
    # ==================================================
    storables.append(
        {
            "id":
            f"{prefix}ItemControl"
        }
    )
    # ==================================================
    # Material
    # ==================================================
    storables.append(
        build_hair_material(
            prefix,
            hair_data,
            props
        )
    )
    # ==================================================
    # Root
    # ==================================================
    vaj_data={
        "components":[],
        "storables":
            storables
    }
    output=Path(output_dir)
    path=output / f"{clothing_hair_id}.vaj"
    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            vaj_data,
            f,
            indent=4
        )
    return str(path)
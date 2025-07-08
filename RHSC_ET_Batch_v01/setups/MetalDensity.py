import os
import sys
import re
import math
import argparse
import copy

from setups import FakeTotemGen

def arg():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fc_powerfile", type=str, required=False, default="", help="FC power file path")
    parser.add_argument(
        "--outputFolder", type=str, required=False, default="./", help="output folder")
    parser.add_argument(
        "--outputName", type=str, required=False, default="pwd.mhs", help="output name")   

    return parser

def MetalDensityScheme(tileDict, scheme=["NORMAL"]):
    def __scheme(coordStr, mdType, outStr):
        ### Metal density type: [Metal, Via] in % ###
        MDTYPE = {"HIGHMD":["0.8", "0.5"], "MIDMD": ["0.6", "0.2"], "LOWMD": ["0.3", "0.05"]}
        metalStr = " ".join(["Metal_global", coordStr, MDTYPE[mdType][0]])
        viaStr = " ".join(["Via_global", coordStr, MDTYPE[mdType][1]])
        outStr.append(metalStr)
        outStr.append(viaStr)
    
    outStr = []
    for i in tileDict.keys():
        llx = tileDict[i]["llx"]
        lly = tileDict[i]["lly"]
        urx = tileDict[i]["urx"]
        ury = tileDict[i]["ury"]
        pwr = tileDict[i]["PWR"]
        coordStr = "{"+str(llx)+" "+str(lly)+"} {"+str(urx)+" "+str(ury)+"}"
        if scheme[0] == "WORST":
            ### depend on case ###
            if pwr < 0.00025:
                __scheme(coordStr, "HIGHMD", outStr)
            if pwr >= 0.00025 and pwr < 0.001:
                __scheme(coordStr, "MIDMD", outStr)
            if pwr > 0.001:
                __scheme(coordStr, "LOWMD", outStr)
    
    with open("Metal_density_setup", "w") as fid:
        fid.write("\n".join(outStr))


def loadLayerMapping(layermapPath):
    if layermapPath is None:
        return {}, [], []
    if not os.path.isfile(layermapPath):
        print("[ERROR] {} layer mapping file path not found".format(layermapPath))
        return {}, [], []
    
    mapDict = {}
    ignoreTotem, ignoreMD = [], []
    with open(layermapPath, "r") as fid:
        inMapping = False
        inIgnoreTotem, inIgnoreMD = False, False
        for i, ll in enumerate(fid):
            ll = ll.split("\n")[0]
            command = re.match(r"^#.*", ll, re.M|re.I)
            check = re.match(r"^\.(.*):.*", ll, re.M|re.I)

            if command:
                continue

            if check:
                #print(check.groups(), check.group(1))
                if check.group(1) in ["LAYER_MAPPING"]:
                    inMapping = True
                    continue
                
                if check.group(1) in ["IGNORE"]:
                    ignoreType = ll.split(":")[-1]
                    if ignoreType == "Totem-EM":
                        inIgnoreTotem = True
                        continue
                    if ignoreType == "MD_File":
                        inIgnoreMD = True
                        continue

            if ll in [".END"]:
                inMapping = False
                inIgnoreMD = False
                inIgnoreTotem = False
            
            if inMapping:
                lls = ll.split(",")
                mapDict.setdefault(lls[1], lls[0])
            
            if inIgnoreTotem:
                ignoreTotem.append(ll)
            
            if inIgnoreMD:
                ignoreMD.append(ll)
    
    #print(mapDict, ignoreTotem, ignoreMD)
    return mapDict, ignoreTotem, ignoreMD


def translate2MDSetup(givenMD, totemPath, layermapPath=None,
                      outputFolder="./", outputName="metal_density.setup"):
    ## givenMD format: llx,lly,urx,ury,layer,metal_density(%) ##
    
    ### MDPath: metal density file path ###
    ### load files ###
    if not os.path.isfile(totemPath):
        print("[ERROR] {} totem-em path not found".format(totemPath))
        return
    
    if not os.path.isfile(givenMD):
        print("[ERROR] {} metal density file path not found".format(givenMD))
        return
    
    totemTF = FakeTotemGen.parseTotemTF(totemPath)
    totemTF.parsing()
    totemTF.makeStacking()

    outStr = []
    with open(givenMD, "r") as fid:
        if layermapPath is None:
            pass
        else:
            mapDict, ignoreTotem, ignoreMD = loadLayerMapping(layermapPath)
        
        for i, ll in enumerate(fid):
            ll = ll.split("\n")[0]
            lls = ll.split(",")
            llx = lls[0]
            lly = lls[1]
            urx = lls[2]
            ury = lls[3]
            layer = lls[4]
            md = lls[5]
            if layermapPath is None:
                pass
            else:
                if layer in ignoreMD:
                    continue
                else:
                    layer = mapDict[layer]
            
            mdStr = "{},{},{},{},{},{}".format(layer,llx,lly,urx,ury,md)
            outStr.append(mdStr)
    
    outputPath = os.path.join(outputFolder, outputName)
    with open(outputPath, "w") as fid:
        fid.write("\n".join(outStr))
    
    return outputPath


def save2MetalDensitySetup(MDList, outputFolder="./", MDSetupName="metal_density.setup"):
    ### maybe need to check with Totem-EM ###

    outPath = os.path.join(outputFolder, MDSetupName)
    with open(outPath, "w") as fid:
        fid.write("\n".join(MDList))

def loadMetalDensitySetup(totemPath, MDPath, layermapPath, area=[], \
                          outputFolder="./", ETMDName="density.csv"):
    
    def __F2Sprecision(fval, prec=5):
        precStr= "{:."+str(prec)+"f}"
        return precStr.format(fval)
    
    ### MDPath: metal density file path ###
    ### load files ###
    if not os.path.isfile(totemPath):
        print("[ERROR] {} totem-em path not found".format(totemPath))
        return
    
    if not os.path.isfile(MDPath):
        print("[ERROR] {} metal density setup path not found".format(MDPath))
        return
    
    totemTF = FakeTotemGen.parseTotemTF(totemPath)
    totemTF.parsing()
    totemTF.makeStacking()

    mapDict, ignoreTotem, ignoreMD = loadLayerMapping(layermapPath)

    METALS = {"__list__":[]}
    VIAS = {"__list__":[]}
    ### filter criteria, NEED TO BE REFINE ###
    for ly in totemTF.stacking:
        for _ly in ly:
            #isMetal = re.match(r"^([M|m][e|E]?[t|T]?[a|A]?[l|L]?[\d+])", _ly, re.M|re.I)
            #isVIA = re.match(r"^([v|V][i|I]?[a|A]?[\d+])", _ly, re.M|re.I)
            if _ly in ignoreTotem:
                continue

            layerType = totemTF.askLayerType(_ly)
            if layerType == "METAL":
                isMetal = True
                isVIA = False
            if layerType == "VIA":
                isVIA = True
                isMetal = False
            
            if isMetal:
                METALS["__list__"].append(_ly)
                METALS.setdefault(_ly, "0.0")
            if isVIA:
                VIAS["__list__"].append(_ly)
                VIAS.setdefault(_ly, "0.0")
    ##########################################
    #print(METALS, VIAS)

    ### determine offsetX & offsetY ###
    offsetX = float("{:.3f}".format((area[2]-area[0])*0.5))
    offsetY = float("{:.3f}".format((area[3]-area[1])*0.5))
    
    mdDict = {}
    orderList = []
    ### process metal density file ###
    with open(MDPath, "r") as fid:
        for ll in fid:
            ll = ll.split("\n")[0]
            if len(ll) > 0:
                lls = (ll.split("\n")[0]).split(",")
                #coord = re.match(r".*{([-+]?\d*\.?\d+) ([-+]?\d*\.?\d+)} {([-+]?\d*\.?\d+) ([-+]?\d*\.?\d+)}.*", ll)
                layer = lls[0]
                llx = float(lls[1])-offsetX
                lly = float(lls[2])-offsetY
                urx = float(lls[3])-offsetX
                ury = float(lls[4])-offsetY
                val = __F2Sprecision(float(lls[5]), 3)

                llx = __F2Sprecision(llx)
                lly = __F2Sprecision(lly)
                urx = __F2Sprecision(urx)
                ury = __F2Sprecision(ury)
                key = "_".join([llx, lly, urx, ury])

                if key in mdDict.keys():
                    pass
                else:
                    mdDict.setdefault(key, {"METALS":copy.deepcopy(METALS), "VIAS":copy.deepcopy(VIAS)})
                    orderList.append(key)
            
                if layer == "Metal_global":
                    for m in mdDict[key]["METALS"].keys():
                        if m in ["__list__"]:
                            continue
                        mdDict[key]["METALS"][m] = val
            
                elif layer == "Via_global":
                    for v in mdDict[key]["VIAS"].keys():
                        if v in ["__list__"]:
                            continue
                        mdDict[key]["VIAS"][v] = val
                else:
                    if layer in mdDict[key]["METALS"].keys():
                        mdDict[key]["METALS"][layer] = val
                    
                    if layer in mdDict[key]["VIAS"].keys():
                        mdDict[key]["VIAS"][layer] = val
            
                #print("**", llx, lly, urx, ury, val)
    
    #print(mdDict["-110.00000_-105.00000_-109.00000_-104.00000"])
    #sys.exit(1)
    #### output to RHSC_ET density file ####
    MVstacking = []
    for ly in totemTF.stacking:
        for _ly in ly:
            if _ly in METALS["__list__"]+VIAS["__list__"]:
                MVstacking.append(_ly)
    
    _str = "#<Box_ID>,<llx(um)>,<lly(um)>,<urx(um)>,<ury(um)>,"+",".join(MVstacking)
    outStr = [_str]
    
    for i, areaKey in enumerate(orderList):
        area = ",".join(areaKey.split("_"))
        
        _mdsetup = ["{}".format(i+1), area]
        for _ly in MVstacking:
            mdVal = None
            try:
                mdVal = mdDict[areaKey]["METALS"][_ly]
            except:
                pass
            try:
                mdVal = mdDict[areaKey]["VIAS"][_ly]
            except:
                pass
            
            if mdVal is None:
                print("<WARNING> layer:{} cannot find the density value, assign 0%".format(_ly))
                mdVal = "0"
            
            _mdsetup.append(mdVal)
        
        _outstr = ",".join(_mdsetup)
        outStr.append(_outstr)

    #print(outStr)
    if not os.path.isdir(outputFolder):
        os.makedirs(outputFolder)
    
    outPath = os.path.join(outputFolder, ETMDName)
    with open(outPath, "w") as fid:
        fid.write("\n".join(outStr))
    
    return outPath


if __name__ == "__main__":
    ## python FCpowermap.py --fc_powermap=./thermal_case.csv

    totemPath = "./fake.tech"
    mdPath = "./Metal_density"
    area = [0,0,35,35]
    loadMetalDensitySetup(totemPath, mdPath, area=area)

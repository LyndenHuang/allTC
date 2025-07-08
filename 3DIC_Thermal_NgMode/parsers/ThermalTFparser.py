import os
import sys
import re
import json
import argparse

import xml.etree.ElementTree as ET


def arg():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--outputName", type=str, required=False, default="fake.tech", help="name") 
    parser.add_argument(
        "--outputFolder", type=str, required=False, default="./", help="folder place")
    parser.add_argument(
        "--json", type=str, required=False, help="stacking conf")

    return parser

class parseThermalTF:
    def __init__(self, TTFPath, TTFtype="ModuleBase"):
        self.TTFPath = TTFPath

        self.TTFNames = []

        self.MatDict = {}
        self.LayerDict = {}

        self.parsing()
    
    def getDieLayerMaterials(self, dieName, layer):
        matProperties = None
        
        if "MATERIAL_NAME" in self.LayerDict[dieName][layer].keys():
            layer_mat = self.LayerDict[dieName][layer]["MATERIAL_NAME"]
            matProperties = self.MatDict[dieName][layer_mat]
        
        if matProperties is None:
            print("<WARNING> {}/{}: No material properties found".format(dieName, layer))
        
        return matProperties
    

    def parsing(self):
        ### load the top TTF ###
        TTFDir = os.path.dirname(self.TTFPath)
        #print(TTFDir)
        if not os.path.isfile(self.TTFPath):
            print("[ERROR] {} path not found".format(self.TTFPath))
            return

        tree = ET.parse(self.TTFPath)
        root = tree.getroot()
        moduleTF = []
        for cc in root:
            if cc.tag == "INCLUDE":
                for subTF in cc:
                    if subTF.tag == "PATH":
                        moduleTF.append(os.path.join(TTFDir, subTF.text))
        
        #print(moduleTF)
        for ttfpath in moduleTF:
            tree = ET.parse(ttfpath)
            root = tree.getroot()
            dieName = None
            for c in root:
                if c.tag == "DIE":
                    for die in c:
                        if die.tag == "NAME":
                            self.TTFNames.append(die.text)
                            self.MatDict.setdefault(die.text, {})
                            self.LayerDict.setdefault(die.text, {})
                            dieName = die.text
                        
                        if die.tag == "METAL":
                            lyName = None
                            for ly in die:
                                if ly.tag == "LAYERS":
                                    self.LayerDict[dieName].setdefault(ly.text, {"MATERIAL_NAME":None, "BASE_MATERIAL_NAME":None})
                                    lyName = ly.text
                                
                                if ly.tag == "MATERIAL_NAME":
                                    self.LayerDict[dieName][lyName]["MATERIAL_NAME"] = ly.text
                                
                                if ly.tag == "BASE_MATERIAL_NAME":
                                    self.LayerDict[dieName][lyName]["BASE_MATERIAL_NAME"] = ly.text
                
                
                if c.tag == "MATERIAL_LIB":
                    _matlib = self.MatDict[dieName]
                    
                    for mat in c:
                        if mat.tag == "MATERIAL":
                            pcount = 1
                            matName = None
                            for _mat in mat:
                                if _mat.tag == "NAME":
                                    _matlib.setdefault(_mat.text, {})
                                    matName = _mat.text
                                if _mat.tag == "PARAMETERS":
                                    _para = "P"+str(pcount)
                                    _matlib[matName].setdefault(_para, {"REF_TEMP": None,
                                        "THERMAL_CONDUCTIVITY": None, "SPECIFIC_HEAT": None, "DENSITY": None})
                                    
                                    for para in _mat:
                                        if para.tag == "REF_TEMP":
                                            _matlib[matName][_para]["REF_TEMP"] = para.text
                                        if para.tag == "THERMAL_CONDUCTIVITY":
                                            _matlib[matName][_para]["THERMAL_CONDUCTIVITY"] = para.text
                                        if para.tag == "SPECIFIC_HEAT":
                                            _matlib[matName][_para]["SPECIFIC_HEAT"] = para.text
                                        if para.tag == "DENSITY":
                                            _matlib[matName][_para]["DENSITY"] = para.text
                                    
                                    pcount += 1


        
        #print(self.TTFNames)
   


if __name__ == "__main__":
    ### command: python FakeTotemGen.py --conf=./setup.conf 
    ###                          --outputName=<NAME> --outputFolder=<>
    args = arg().parse_args()

    TFsetupPath = "./thermalTF_wTSV.json"
    em = genThermalTF(TFsetupPath, args.outputFolder)
    em.genXMLThermalTF()

    #Totem = "./fake.tech"
    #TotemTF = FakeTotemGen.parseTotemTF(Totem)
    #TotemTF.parsing()
    #TotemTF.makeStacking()
    
    
import os
import sys
import re
import json
import argparse

import xml.etree.ElementTree as ET

import FakeTotemGen

TF_SECTION_TAG =  ["SILICON", "METAL", "MEOL_DIELECTRIC", "FEOL_DIELECTRIC", \
                   "BEOL_DIELECTRIC", "BS_DIELECTRIC", "THROUGH_VIA", "BUMP", "MOLDING_COMPOUND"]
TF_MAT_TAG = ["REF_TEMP", "THERMAL_CONDUCTIVITY", "SPECIFIC_HEAT", "DENSITY"]

def arg():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--outputName", type=str, required=False, default="fake.tech", help="name") 
    parser.add_argument(
        "--outputFolder", type=str, required=False, default="./", help="folder place")
    parser.add_argument(
        "--json", type=str, required=False, help="stacking conf")

    return parser

class genThermalTF:
    def __init__(self, jsonPath, outputFolder="./"):
        self.jsonPath = jsonPath
        self.outputFolder = outputFolder

        self.setupDict = None

        self.__readJson()
    
    def __pretty_print(self, current, parent=None, index=-1, depth=0):
        for i, node in enumerate(current):
            self.__pretty_print(node, current, i, depth+1)
        
        if parent is not None:
            if index == 0:
                parent.text = "\n"+("\t"*depth)
            else:
                parent[index-1].tail = "\n"+("\t"*depth)
            
            if index == len(parent)-1:
                current.tail = "\n"+("\t"*(depth-1))

    
    def __readJson(self):
        if not os.path.isfile(self.jsonPath):
            print("[ERROR] {} path not found".format(self.jsonPath))
            return
        
        print("{} Parsing...".format(self.jsonPath))
        with open(self.jsonPath, "r") as fid:
            self.setupDict = json.load(fid)
        
        print(self.setupDict)
    
    def genMaterialLib(self, xmlRoot, dieMat):
        MatDict = self.setupDict["MATERIAL_LIB"]
        for mat in dieMat:
            mm = ET.SubElement(xmlRoot, "MATERIAL")
            ET.SubElement(mm, "NAME").text = mat
            if "TEMP_VAR" in MatDict[mat].keys():
                tempVars = MatDict[mat]["TEMP_VAR"]
                for i in range(tempVars):
                    idx = "T"+str(i+1)
                    param = ET.SubElement(mm, "PARAMETERS")
                    for attr in TF_MAT_TAG:
                        val = "{:.3f}".format(MatDict[mat][idx][attr])
                        ET.SubElement(param, attr).text = val
            else:
                param = ET.SubElement(mm, "PARAMETERS")
                for attr in TF_MAT_TAG:
                    val = "{:.3f}".format(MatDict[mat][attr])
                    ET.SubElement(param, attr).text = val

    
    def genXMLThermalTF(self, tfType=1):
        ## tfType == 1: module-based ##
        caseName = self.setupDict["NAME"]
        rootFolder = os.path.join(self.outputFolder, caseName)
        if not os.path.isdir(rootFolder):
            os.makedirs(rootFolder, 0o755)
        
        if tfType == 1:
            ### top TF ###
            topPath = os.path.join(rootFolder, "topTF.xml")
            topTF = ET.Element("THERMAL_MODEL")
            ET.SubElement(topTF, "NAME").text = self.setupDict["NAME"]
            ET.SubElement(topTF, "TYPE").text = self.setupDict["TYPE"]
            ET.SubElement(topTF, "VERSION").text = self.setupDict["VERSION"]
            tt = ET.SubElement(topTF, "INCLUDE")
            
            subXML = os.path.join(rootFolder, "XML")
            if not os.path.isdir(subXML):
                os.makedirs(subXML, 0o755)
            
            for d in self.setupDict["DIES"].keys():
                subTFPath = "./XML/"+d+".xml"
                ET.SubElement(tt, "PATH").text = subTFPath
            
            self.__pretty_print(topTF)
            tree = ET.ElementTree(topTF)
            #ET.indent(tree, space="\t", level=0)
            tree.write(topPath)

            ## for each subTF module ##
            for d in self.setupDict["DIES"].keys():
                dieDict = self.setupDict["DIES"][d]
                
                ### load Totem TF ###
                totemPath = dieDict["RCE"]
                TotemTF = FakeTotemGen.parseTotemTF(totemPath)
                TotemTF.parsing()
                TotemTF.makeStacking()
                stacking = TotemTF.stacking
                
                subTF = ET.Element("THERMAL_MODEL")
                ET.SubElement(subTF, "VERSION").text = self.setupDict["DIES"][d]["VERSION"]
                dieTF = ET.SubElement(subTF, "DIE")
                ET.SubElement(dieTF, "NAME").text = d
                ET.SubElement(dieTF, "TYPE").text = dieDict["TYPE"]
                dieMats = []
                for tag in TF_SECTION_TAG:
                    if tag not in dieDict.keys():
                        continue

                    if len(dieDict[tag]) == 0:
                        continue

                    if tag == "SILICON":
                        sec = ET.SubElement(dieTF, tag)
                        ET.SubElement(sec, "THICKNESS_SOURCE").text = dieDict[tag]["THICKNESS_SOURCE"]
                        ET.SubElement(sec, "BASE_MATERIAL_NAME").text = dieDict[tag]["BASE_MATERIAL_NAME"]
                        dieMats.append(dieDict[tag]["BASE_MATERIAL_NAME"])
                        if "THICKNESS" in dieDict[tag].keys():
                            ET.SubElement(sec, "THICKNESS").text = dieDict[tag]["THICKNESS"]

                    if tag in ["FEOL_DIELECTRIC", "BEOL_DIELECTRIC", "BS_DIELECTRIC"]:
                        sec = ET.SubElement(dieTF, tag)
                        ET.SubElement(sec, "BASE_MATERIAL_NAME").text = dieDict[tag]["BASE_MATERIAL_NAME"]
                        dieMats.append(dieDict[tag]["BASE_MATERIAL_NAME"])
                    
                    if tag == "MEOL_DIELECTRIC":
                        sec = ET.SubElement(dieTF, tag)
                        ET.SubElement(sec, "THICKNESS").text = "{:.3f}".format(dieDict[tag]["THICKNESS"])
                        ET.SubElement(sec, "ATTACH_LAYER").text = dieDict[tag]["ATTACH_LAYER"]
                        ET.SubElement(sec, "BASE_MATERIAL_NAME").text = dieDict[tag]["BASE_MATERIAL_NAME"]
                        dieMats.append(dieDict[tag]["BASE_MATERIAL_NAME"])
                    
                    if tag == "THROUGH_VIA":
                        sec = ET.SubElement(dieTF, tag)
                        ET.SubElement(sec, "LAYERS").text = "TSV"
                        ET.SubElement(sec, "ATTACH_LAYER").text = dieDict[tag]["ATTACH_LAYER"]
                        ET.SubElement(msec, "MATERIAL_NAME").text = dieDict[tag]["MATERIAL_NAME"]
                        ET.SubElement(sec, "BASE_MATERIAL_NAME").text = dieDict[tag]["BASE_MATERIAL_NAME"]
                        dieMats.append(dieDict[tag]["BASE_MATERIAL_NAME"])
                    
                    if tag == "METAL":
                        for mTag in dieDict[tag].keys():
                            if "-" in mTag:
                                star, end = mTag.split("-")
                                isStart = False
                                layers = []
                                for ly in stacking:
                                    if star in ly:
                                        isStart = True
                                    
                                    if end in ly:
                                        layers += ly
                                        break
                                    
                                    if isStart:
                                        layers += ly
                                
                                for mm in layers:
                                    msec = ET.SubElement(dieTF, "METAL")
                                    ET.SubElement(msec, "LAYERS").text = mm
                                    ET.SubElement(msec, "MATERIAL_NAME").text = dieDict[tag][mTag]["MATERIAL_NAME"]
                                    ET.SubElement(msec, "BASE_MATERIAL_NAME").text = dieDict[tag][mTag]["BASE_MATERIAL_NAME"]
                                    dieMats.append(dieDict[tag][mTag]["MATERIAL_NAME"])
                                    dieMats.append(dieDict[tag][mTag]["BASE_MATERIAL_NAME"])
                            else:
                                msec = ET.SubElement(dieTF, "METAL")
                                ET.SubElement(msec, "LAYERS").text = mm
                                ET.SubElement(msec, "MATERIAL_NAME").text = dieDict[tag][mTag]["MATERIAL_NAME"]
                                ET.SubElement(msec, "BASE_MATERIAL_NAME").text = dieDict[tag][mTag]["BASE_MATERIAL_NAME"]
                                dieMats.append(dieDict[tag][mTag]["MATERIAL_NAME"])
                                dieMats.append(dieDict[tag][mTag]["BASE_MATERIAL_NAME"])

                ### add material lib ###
                dieMats = list(set(dieMats))  ## remove duplicate materials
                matSec = ET.SubElement(subTF, "MATERIAL_LIB")
                self.genMaterialLib(matSec, dieMats)
            
                ## write out module TF ##
                TFName = d+".xml"
                subPath = os.path.join(subXML, TFName)

                self.__pretty_print(subTF)
                tree = ET.ElementTree(subTF)
                #ET.indent(tree, space="\t", level=0)
                tree.write(subPath)
                
        if tfType == 2:
            pass

class parseThermalTF:
    def __init__(self, TTFPath, TTFtype="ModuleBase"):
        self.TTFPath = TTFPath

        self.layerDict = {"METAL":{}, "VIA":{}}

    
    def parsing(self):
        ### load the top TTF ###
        tree = ET.parse(self.TTFPath)
        root = tree.getroot()
        moduleTF = []
        for cc in root:
            if cc == "INCLUDE":
                for subTF in cc:
                    moduleTF.append(subTF.text)
        
        print(moduleTF)
   


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
    
    
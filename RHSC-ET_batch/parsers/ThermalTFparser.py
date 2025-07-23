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

        self.parsing()

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
            for c in root:
                if c.tag == "DIE":
                    for die in c:
                        if die.tag == "NAME":
                            self.TTFNames.append(die.text)
        
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
    
    
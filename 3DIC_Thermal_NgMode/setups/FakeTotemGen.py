import os
import sys
import re
import argparse

def arg():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--outputName", type=str, required=False, default="TDfake.tech", help="name") 
    parser.add_argument(
        "--outputFolder", type=str, required=False, default="./", help="folder place")
    parser.add_argument(
        "--conf", type=str, required=True, help="stacking conf")

    return parser

class parseTotemTF:
    def __init__(self, totemPath):
        self.totemPath = totemPath

        self.layerDict = {"METAL":{}, "VIA":{}}

        self.lowestMetal = None
        self.topMetal = None
        self.totalMetalVia = 0

        self.stacking = []
    
    def __F2Sprecision(self, fval, precision=5):
        prec = "{:."+str(precision)+"f}"
        return prec.format(fval)
    
    def askLayerType(self, layer):
        if layer in self.layerDict["METAL"].keys():
            return "METAL"
        
        if layer in self.layerDict["VIA"].keys():
            return "VIA"
    
    def getDieHeight(self):
        #print(self.topMetal)
        if self.topMetal:
            low_height = self.layerDict["METAL"][self.lowestMetal]["HEIGHT"]
            top_height = self.layerDict["METAL"][self.topMetal]["HEIGHT"]
            top_thickness = self.layerDict["METAL"][self.topMetal]["THICKNESS"]
            die_height = self.__F2Sprecision(top_height+top_thickness-low_height, 6)
            return die_height
        
        return None
    
    def getLayerThickness(self, layer):
        if layer in self.layerDict["METAL"].keys():
            thickness = self.layerDict["METAL"][layer]["THICKNESS"]
        
        if layer in self.layerDict["VIA"].keys():
            thickness = self.layerDict["VIA"][layer]["THICKNESS"]
        
        thickness = self.__F2Sprecision(thickness, 6)
        return thickness
    
    def getLayerHeight(self, layer):
        if layer in self.layerDict["METAL"].keys():
            height = self.layerDict["METAL"][layer]["THICKNESS"]
        
        if layer in self.layerDict["VIA"].keys():
            height = self.layerDict["VIA"][layer]["THICKNESS"]
        
        height = self.__F2Sprecision(height, 6)
        return height

    
    def parsing(self):
        if not os.path.isfile(self.totemPath):
            print("[ERROR] {} path not found".format(self.totemPath))
            return
        
        print("{} Parsing...".format(self.totemPath))
        lowestH, topH = 100000, -100000
        with open(self.totemPath, "r") as fid:
            inMetal, inVia = False, False
            lyName = None
            for ll in fid:
                lls = (ll.split("\n")[0]).split()
                if "metal" in lls[0]:
                    inMetal = True
                    inVia = False
                    lyName = lls[1]
                    self.layerDict["METAL"].setdefault(lyName, {"THICKNESS":None, "HEIGHT":None})
                    self.totalMetalVia += 1
                    continue

                elif "via" in lls[0]:
                    inVia = True
                    inMetal = False
                    lyName = lls[1]
                    self.layerDict["VIA"].setdefault(lyName, {"UPPER":None, "LOWER":None, "THICKNESS":None,\
                                                              "HEIGHT":None})
                    self.totalMetalVia += 1
                    continue

                elif "}" in lls[0]:
                    inMetal = False
                    inVia = False
                else:
                    pass

                if inMetal:
                    if lls[0] == "THICKNESS":
                        self.layerDict["METAL"][lyName]["THICKNESS"] = float(lls[1])
                    if lls[0] == "HEIGHT":
                        height = float(lls[1])
                        if lowestH > height:
                            lowestH = height
                            self.lowestMetal = lyName
                        if topH < height:
                            topH = height
                            self.topMetal = lyName
                        
                        self.layerDict["METAL"][lyName]["HEIGHT"] = float(lls[1])
                
                if inVia:
                    if lls[0] == "UpperLayer":
                        self.layerDict["VIA"][lyName]["UPPER"] = lls[1]
                    if lls[0] == "LowerLayer":
                        self.layerDict["VIA"][lyName]["LOWER"] = lls[1]
        
        #print(self.layerDict)
    
    def makeStacking(self):
        ### update VIA values ###
        viaDict = self.layerDict["VIA"]
        metalDict = self.layerDict["METAL"]
        for v in viaDict.keys():
            lowerMetal = viaDict[v]["LOWER"]
            height = self.layerDict["METAL"][lowerMetal]["HEIGHT"]+self.layerDict["METAL"][lowerMetal]["THICKNESS"]
            upperMetal = viaDict[v]["UPPER"]
            thickness = self.layerDict["METAL"][upperMetal]["HEIGHT"]-height
            height = float("{:.6f}".format(height))
            thickness = float("{:.6f}".format(thickness))
            viaDict[v]["HEIGHT"] = height
            viaDict[v]["THICKNESS"] = thickness
        
        #print(self.layerDict, self.lowestMetal, self.topMetal, self.totalMetalVia)
        processed = []
        check_height = metalDict[self.lowestMetal]["HEIGHT"]
        while len(processed) < self.totalMetalVia:
            same_heights = []
            lowestH = 100000
            for m in metalDict.keys():
                if m in processed:
                    continue
                if metalDict[m]["HEIGHT"] == check_height:
                    same_heights.append(m)
                    processed.append(m)
            for v in viaDict.keys():
                if v in processed:
                    continue
                if viaDict[v]["HEIGHT"] == check_height:
                    same_heights.append(v)
                    processed.append(v)
            
            self.stacking.append(same_heights)
            ### update next check height ###
            for m in metalDict.keys():
                if m in processed:
                    continue
                if lowestH > metalDict[m]["HEIGHT"]:
                    lowestH = metalDict[m]["HEIGHT"]
            
            for v in viaDict.keys():
                if v in processed:
                    continue
                if lowestH > viaDict[v]["HEIGHT"]:
                    lowestH = viaDict[v]["HEIGHT"]
            
            check_height = lowestH
        
        #print(self.stacking)



class FakeTotemTF:
    def __init__(self, confPath, outputFolder="./", outputName="fakeTotem.tech"):
        self.confPath = confPath
        self.outputFolder = outputFolder
        self.totemName = outputName

        self.stackDict = {"METAL":{"__list__":[]},"VIA":{"__list__":[]},\
                          "DIELECTRIC":{"__list__":[]}}

        self.__parserConf()
    
    def __parserConf(self):
        if not os.path.isfile(self.confPath):
            print("[ERROR] {} path not found".format(self.TMpath))
            return
        
        print("{} Parsing...".format(self.confPath))
        with open(self.confPath, "r") as fid:
            inStacking = False
            inDielectric = False
            stackHeight = 0.0
            for ll in fid:
                #print(ll)
                ## annotation ##
                ll = ll.split("\n")[0]

                if re.match(r"^#.*", ll, re.M|re.I) or len(ll)==0:
                    #print(ll)
                    continue

                if "STACKING" in ll:
                    inStacking = True
                    inDielectric = False
                    continue

                if "DIELECTRIC" in ll:
                    inStacking = False
                    inDielectric = True
                    continue

                if inStacking:
                    if ";" in ll:
                        pass
                    else:
                        lls = ll.split(",")
                        if lls[0] == "METAL":
                            metalDict = self.stackDict["METAL"]
                            if len(lls) == 4:
                                ### include "height" ###
                                name = lls[1]
                                height = float("{:.6f}".format(float(lls[2])))
                                thickness = float("{:.6f}".format(float(lls[3])))
                                stackHeight = height
                            elif len(lls) == 3:
                                name = lls[1]
                                height = stackHeight
                                thickness = float("{:.6f}".format(float(lls[2])))
                                height = float("{:.6f}".format(float(height)))
                            
                            metalDict["__list__"].append(name)
                            stackHeight = stackHeight + thickness
                            thickness = "{:.6f}".format(thickness)
                            height = "{:.6f}".format(height)
                            metalDict.setdefault(name, {"HEIGHT":height, \
                                                        "THICKNESS":thickness})

                        if lls[0] == "VIA":
                            viaDict = self.stackDict["VIA"]
                            name = lls[1]
                            height = stackHeight
                            thickness = float("{:.6f}".format(float(lls[2])))
                            lowerLayer = lls[3]
                        
                            viaDict["__list__"].append(name)
                            stackHeight = stackHeight + thickness
                            thickness = "{:.6f}".format(thickness)
                            height = "{:.6f}".format(height)
                            viaDict.setdefault(name, {"HEIGHT":height, \
                                                      "THICKNESS":thickness,\
                                                      "LOWERLAYER":lowerLayer,\
                                                      "UPPERLAYER":None})

                if inDielectric:
                    lls = ll.split(",")
                    if len(lls) == 4:
                        ### include "height" ###
                        name = lls[0]
                        height = lls[1]
                        thickness = lls[2]
                        const = lls[3]
                        pass
                    elif len(lls) == 3:
                        name = lls[0]
                        height = None
                        thickness = lls[1]
                        const = lls[2]
                    else:
                        pass

                    self.stackDict["DIELECTRIC"]["__list__"].append(name)
                    dielDict = self.stackDict["DIELECTRIC"]
                    if height is None:
                        ## looking for previous dielectric layer ##
                        pre_id = [i-1 for i, e in enumerate(dielDict["__list__"]) if e == name]
                        preName = dielDict["__list__"][pre_id[0]]
                        height = float(dielDict[preName]["HEIGHT"]) + float(dielDict[preName]["THICKNESS"])
                        height = "{:.6f}".format(float(height))
                    else:
                        height = "{:.6f}".format(float(height))
                    
                    thickness = "{:.6f}".format(float(thickness))
                    self.stackDict["DIELECTRIC"].setdefault(name, {"HEIGHT":height, \
                                                                   "THICKNESS":thickness,\
                                                                   "CONST":const})
        
        #print(self.stackDict)
        ### update VIA UpperLayer ###
        viaDict = self.stackDict["VIA"]
        metalDict = self.stackDict["METAL"]
        for v in viaDict["__list__"]:
            top_height = float(viaDict[v]["HEIGHT"]) + float(viaDict[v]["THICKNESS"])
            top_height = "{:.6f}".format(top_height)
            for m in metalDict["__list__"]:
                m_height = metalDict[m]["HEIGHT"]
                if top_height == m_height:
                    #print(v, m)
                    viaDict[v]["UPPERLAYER"] = m
                    break
        
        #print(self.stackDict)
    
    def genFakeTotemTF(self):
        outStr = ["# Fake Totem-EM TF #"]
        for t in ["METAL", "VIA", "DIELECTRIC"]:
            #print(type(self.stackDict[t]["__list__"]))
            for ly in reversed(self.stackDict[t]["__list__"]):
                _str = ""
                name = ly
                if t == "METAL":
                    thickness = self.stackDict[t][ly]["THICKNESS"]
                    height = self.stackDict[t][ly]["HEIGHT"]
                    _str = "metal {}\n".format(name)
                    _str += "{\n"
                    _str += "  MINWIDTH 1\n  MINSPACE 1\n  PITCH 1\n  THICKNESS {}\n  RESISTANCE 1\n  HEIGHT {}\n".format(thickness, height)
                    _str += "}"
                    #print(_str)
                if t == "VIA":
                    lower = self.stackDict[t][ly]["LOWERLAYER"]
                    upper = self.stackDict[t][ly]["UPPERLAYER"]
                    _str = "via {}\n".format(name)
                    _str += "{\n"
                    _str += "  Resistance 1\n  Tnom 25\n  UpperLayer {}\n  LowerLayer {}\n".format(upper, lower)
                    _str += "}"

                if t == "DIELECTRIC":
                    thickness = self.stackDict[t][ly]["THICKNESS"]
                    height = self.stackDict[t][ly]["HEIGHT"]
                    const = self.stackDict[t][ly]["CONST"]
                    _str = "dielectric {}\n".format(name)
                    _str += "{\n"
                    _str += "  constant {}\n  thickness {}\n  height {}\n".format(const, thickness, height)
                    _str += "}"
                
                outStr.append(_str)
        
        if not os.path.isdir(self.outputFolder):
            os.makedirs(self.outputFolder, 0o755)
        
        totemPath = os.path.join(self.outputFolder, self.totemName)
        
        with open(totemPath, "w") as fid:
            fid.write("\n".join(outStr))
        
        print("<INFO> fake path:{}, #METAL:{}, #VIA:{}, #DIELECTRIC:{}".format(totemPath,\
                                            len(self.stackDict["METAL"]["__list__"]),\
                                            len(self.stackDict["VIA"]["__list__"]),\
                                            len(self.stackDict["DIELECTRIC"]["__list__"])))
    


if __name__ == "__main__":
    ### command: python FakeTotemGen.py --conf=./setup.conf 
    ###                          --outputName=<NAME> --outputFolder=<>
    args = arg().parse_args()

    stackingConfPath = "./Top_1P11M_BS.conf"
    em = FakeTotemTF(stackingConfPath, args.outputFolder, args.outputName)
    em.genFakeTotemTF()

    #totemPath = "./fake.tech"
    #totemTF = parseTotemTF(totemPath)
    #totemTF.parsing()
    #totemTF.makeStacking()
    
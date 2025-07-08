import os
import sys
import re
import math
import argparse
import copy

def arg():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fc_powerfile", type=str, required=False, default="", help="FC power file path")
    parser.add_argument(
        "--outputFolder", type=str, required=False, default="./", help="output folder")
    parser.add_argument(
        "--outputName", type=str, required=False, default="pwd.mhs", help="output name")   

    return parser

class FCPowerView:
    def __init__(self, filePath, fType, 
                 outputFolder="./", outputName="pwd.mhs", DesignArea=[]):
        ### fType: IPF & PWRTILE ###
        self.filePath = filePath
        self.fType = fType
        
        self.DesignArea = DesignArea
        self.LLX, self.LLY = 10000.0, 10000.0
        self.URX, self.URY = -10000.0, -10000.0
        
        self.TotalPwr = 0.0
        self.minPwr = 100000.0
        self.maxPwr = -100000.0

        self.dbDict = {}    ### key is instance name, "avgPD" unit: uW/um^2, "PWR" unit: mW
        self.cellDict = {}  ### key is cell name
        self.tileDict = {}
        self.tileDictParams = {}

        self.outputFolder = outputFolder
        self.outputName = outputName

        if self.fType == "IPF":
            self.loadIPF()
        elif self.fType == "PWRTILE":
            self.loadPWRTILE()
        elif self.fType == "ETMHS":
            self.loadETMHS()
        elif self.fType == "CSV":
            if ";" in filePath:
                self.filePath = self.filePath.split(";")
            
            self.loadCSV()
    
    def __F2Sprecision(self, fval, precision=5):
        prec = "{:."+str(precision)+"f}"
        return prec.format(fval)
    
    def __updateValues(self, llx, lly, urx, ury, pwr):
        self.TotalPwr += pwr

        if self.LLX > llx:
            self.LLX = llx
        if self.LLY > lly:
            self.LLY = lly
        if self.URX < urx:
            self.URX = urx
        if self.URY < ury:
            self.URY = ury
        if self.minPwr > pwr:
            self.minPwr = pwr
        if self.maxPwr < pwr:
            self.maxPwr = pwr

    def loadETMHS(self):
        if not os.path.isfile(self.filePath):
            print("[ERROR] {} path not found".format(self.filePath))
            return
        
        with open(self.filePath, "r") as fid:
            for i, ll in enumerate(fid):
                ll = ll.split("\n")[0]
                if re.match(r"^#.*", ll, re.M|re.I):
                    continue

                if len(ll) > 0:
                    lls = ll.split()
                    if lls[0] == "BBOX":
                        self.LLX = float(self.__F2Sprecision(float(lls[1]), 4))
                        self.LLY = float(self.__F2Sprecision(float(lls[2]), 4))
                        self.URX = float(self.__F2Sprecision(float(lls[3]), 4))
                        self.URY = float(self.__F2Sprecision(float(lls[4]), 4))
                        continue
                    
                    instName = lls[0]
                    llx = float(self.__F2Sprecision(float(lls[1]), 4))
                    lly = float(self.__F2Sprecision(float(lls[2]), 4))
                    urx = float(self.__F2Sprecision(float(lls[3]), 4))
                    ury = float(self.__F2Sprecision(float(lls[4]), 4))
                    pwr = float(self.__F2Sprecision(float(lls[5]), 5))
                    
                    self.__updateValues(llx, lly, urx, ury, pwr)

                    self.dbDict.setdefault(instName, {"llx":llx, "lly":lly, "urx":urx, "ury":ury, \
                                                      "PWR":pwr})
        
        strTotalPwr = "{:.3f}".format(self.TotalPwr)
        print("<INFO> Instances Area:{},{},{},{}; Total PWR={}mW".format(self.LLX, self.LLY, self.URX, self.URY, strTotalPwr))
    
    def modifyCSV(self, modifyCells, pwrFactor):
        ### format: inst,stdCell,llx,lly,urx,ury,total_dynamic_pwr(uW),leakage_pwr(uW) ###
        #print(self.filePath)
        if type(self.filePath) is str:
            self.filePath = [self.filePath]
        
        for csv in self.filePath:
            if not os.path.isfile(csv):
                print("<WARNING> {} csv not found, ignore".format(csv))
                continue
            
            outStr = []
            with open(csv, "r") as fid:
                for i, ll in enumerate(fid):
                    ll = ll.split("\n")[0]
                    
                    if i == 0:
                        ### header ###
                        outStr.append(ll)
                        continue
                    
                    try:
                        lls = ll.split(",")
                        instName = lls[0]
                        cellName = lls[1]
                        llx, lly = float(lls[2]), float(lls[3])
                        urx, ury = float(lls[4]), float(lls[5])
                        pwr = float(lls[6])
                    except:
                        print("<WARNING> line:{} {}, pwr cannot be converted".format(i+1, ll))
                        continue
                    
                    if type(modifyCells) == list:
                        if cellName in modifyCells:
                            pwr = pwr*pwrFactor
                            _str = ",".join(lls[0:6]+[str(pwr)])
                            outStr.append(_str)
                        else:
                            outStr.append(ll)
                    
                    if type(modifyCells) == str:
                        if modifyCells in ["ALL"]:
                            pwr = pwr*pwrFactor
                            _str = ",".join(lls[0:6]+[str(pwr)])
                            outStr.append(_str)
            
            outPath = csv+"_modify"
            with open(outPath, "w") as fid:
                fid.write("\n".join(outStr))
    
    
    def loadCSV(self):
        ### format: inst,stdCell,llx,lly,urx,ury,total_pwr(mW),leakage_pwr(mW) ###
        #print(self.filePath)
        if type(self.filePath) is str:
            self.filePath = [self.filePath]
        
        for csv in self.filePath:
            if not os.path.isfile(csv):
                print("<WARNING> {} csv not found, ignore".format(csv))
                continue
            
            with open(csv, "r") as fid:
                for i, ll in enumerate(fid):
                    isWithLeakage = False
                    if i == 0:
                        ### header ###
                        continue
                    
                    ll = ll.split("\n")[0]
                    lls = ll.split(",")
                    if len(lls) > 7:
                        isWithLeakage = True
                    
                    try:
                        instName = lls[0]
                        cellName = lls[1]
                        llx, lly = float(lls[2]), float(lls[3])
                        urx, ury = float(lls[4]), float(lls[5])
                    
                        pwr = 0.0
                        if isWithLeakage:
                            if lls[6] in ["N/A"]:
                                pass
                            else:
                                pwr = float(lls[6])
                            
                            if lls[7] in ["N/A"]:
                                pass
                            else:
                                pwr = pwr + float(lls[7])
                        else:
                            if lls[6] in ["N/A"]:
                                pass
                            else:
                                pwr = float(lls[6])
                    except:
                        print("<WARNING> line:{} {}, pwr cannot be converted".format(i+1, ll))
                        continue

                    pwr_density = float("{:.8f}".format(pwr/((urx-llx)*(ury-lly))))
                    self.__updateValues(llx, lly, urx, ury, pwr)

                    self.dbDict.setdefault(instName, {"llx":llx, "lly":lly, "urx":urx, "ury":ury, \
                                                      "cellName":cellName, "PWR":pwr, "PWR_density":pwr_density}) #"leakage_PWR":leak_pwr})
                    
                    if cellName in self.cellDict.keys():
                        self.cellDict[cellName]["insts"].append(instName)
                        self.cellDict[cellName]["sum_pwr"] += pwr
                    else:
                        self.cellDict.setdefault(cellName, {"insts":[instName], "sum_pwr":pwr})
        
        
        strTotalPwr = "{:.3f}".format(self.TotalPwr)
        print("<INFO> Instances Area:{},{},{},{}; Total PWR={}mW".format(self.LLX, self.LLY, self.URX, self.URY, strTotalPwr))
        if len(self.DesignArea) > 0:
            ### align to given area ###
            self.LLX = self.DesignArea[0]
            self.LLY = self.DesignArea[1]
            self.URX = self.DesignArea[2]
            self.URY = self.DesignArea[3]
    
    def cellDistribution(self, topN=50):
        _cells = [(i, len(self.cellDict[i]["insts"]), self.cellDict[i]["sum_pwr"]) for i in self.cellDict.keys()]
        sortedCells = sorted(_cells, key=lambda x:x[2], reverse=True)

        for i in range(topN):
            print(sortedCells[i])
    
    def getCellsAreaList(self, cellName):
        areaList = []
        if cellName in self.cellDict.keys():
            for inst in self.cellDict[cellName]["insts"]:
                _llx = self.dbDict[inst]["llx"]
                _lly = self.dbDict[inst]["lly"]
                _urx = self.dbDict[inst]["urx"]
                _ury = self.dbDict[inst]["ury"]
                areaList.append([_llx,_lly,_urx,_ury])
        else:
            print("<WARNING> cell:{} not found".format(cellName))
        
        return areaList
                    

    def loadIPF(self):
        if not os.path.isfile(self.filePath):
            print("[ERROR] {} path not found".format(self.filePath))
            return
    
        with open(self.filePath, "r") as fid:
            for i, ll in enumerate(fid):
                ll = ll.split("\n")[0]
                if len(ll) > 0:
                    lls = ll.split()
                    instName = lls[0]
                    coord = re.match(r".*{([-+]?\d*\.?\d+) ([-+]?\d*\.?\d+)} {([-+]?\d*\.?\d+) ([-+]?\d*\.?\d+)}.*", ll)
                    llx, lly = float(coord.group(1)), float(coord.group(2))
                    urx, ury = float(coord.group(3)), float(coord.group(4))
                    #print(i+1, lls[-1])
                    try:
                        pwr = float(lls[-1])
                    except:
                        ### skip this line ###
                        print("<WARNING> line:{} {}, pwr cannot be converted".format(i+1, ll))
                        continue
                
                    pwr = pwr*0.001  ## uW -> mW
                    #print(instName, llx, lly, urx, ury, pwr)
                    #print((i+1), (urx-llx), (ury-lly))
                    self.__updateValues(llx, lly, urx, ury, pwr)

                    self.dbDict.setdefault(instName, {"llx":llx, "lly":lly, "urx":urx, "ury":ury, \
                                                      "PWR":pwr})

        strTotalPwr = "{:.3f}".format(self.TotalPwr)
        print("<INFO> Instances Area:{},{},{},{}; Total PWR={}mW".format(self.LLX, self.LLY, self.URX, self.URY, strTotalPwr))
        if len(self.DesignArea) > 0:
            ### align to given area ###
            self.LLX = self.DesignArea[0]
            self.LLY = self.DesignArea[1]
            self.URX = self.DesignArea[2]
            self.URY = self.DesignArea[3]


    def loadPWRTILE(self):
        if not os.path.isfile(self.filePath):
            print("[ERROR] {} path not found".format(self.filePath))
            return
    
        count = 0
        with open(self.filePath, "r") as fid:
            for i, ll in enumerate(fid):
                ll = ll.split("\n")[0]
                if re.match(r"^{", ll, re.M|re.I):
                    lls = ll.split(",")
                    coord = re.match(r"{([-+]?\d*\.?\d+) ([-+]?\d*\.?\d+)} {([-+]?\d*\.?\d+) ([-+]?\d*\.?\d+)}", ll)
                    llx, lly = float(coord.group(1)), float(coord.group(2))
                    urx, ury = float(coord.group(3)), float(coord.group(4))
                    pd1, pd2 = lls[1:3]
                    avgPD = float("{:.3f}".format((float(pd1)+float(pd2))*0.5))
                    area = (urx-llx)*(ury-lly)
                    pwr = avgPD*area*0.001  ## uW -> mW 
                    self.__updateValues(llx, lly, urx, ury, pwr)
                
                    self.dbDict.setdefault(count, {"llx":llx, "lly":lly, "urx":urx, "ury":ury, \
                                                   "avgPD":avgPD, "PWR":pwr})

                    count += 1
    
        strTotalPwr = "{:.3f}".format(self.TotalPwr)
        print("<INFO> Area:{},{},{},{}; Total PWR={}mW".format(self.LLX, self.LLY, self.URX, self.URY, strTotalPwr))
    

    def RHSCETmhs(self, outputFolder="./", outputName="pwd.mhs"):
        self.outputFolder = outputFolder
        self.outputName = outputName
        ### to RHSC_ET mhs coordination ###
        offsetX = float("{:.5f}".format((self.URX-self.LLX)*0.5))
        offsetY = float("{:.5f}".format((self.URY-self.LLY)*0.5))

        EToutStr = ["#BBOX <llx(um)> <lly(um)> <urx(um)> <ury(um)>", \
                    "#<Box_ID> <llx(um)> <lly(um)> <urx(um)> <ury(um)> <Power(mW)>"]
    
        llx, lly = self.__F2Sprecision(0-offsetX), self.__F2Sprecision(0-offsetY)
        urx, ury = self.__F2Sprecision(0+offsetX), self.__F2Sprecision(0+offsetY)
        bbox = "BBOX {} {} {} {}".format(llx, lly, urx, ury)
        EToutStr.append(bbox)

        for i, k in enumerate(self.dbDict.keys()):
            llx = self.__F2Sprecision(self.dbDict[k]["llx"]-offsetX-self.LLX)
            lly = self.__F2Sprecision(self.dbDict[k]["lly"]-offsetY-self.LLY)
            urx = self.__F2Sprecision(self.dbDict[k]["urx"]-offsetX-self.LLX)
            ury = self.__F2Sprecision(self.dbDict[k]["ury"]-offsetY-self.LLY)
            pwr = self.__F2Sprecision(self.dbDict[k]["PWR"], precision=8)
            _str = "{} {} {} {} {} {}".format(i+1, llx, lly, urx, ury, pwr)
            EToutStr.append(_str)
    
        if not os.path.isdir(self.outputFolder):
            os.makedirs(self.outputFolder, 0o755)
    
        outPath = os.path.join(self.outputFolder, self.outputName)
        with open(outPath, "w") as fid:
            fid.write("\n".join(EToutStr))
        
        return [self.LLX, self.LLY, self.URX, self.URY], outPath
    
    def translate2TilePwr(self, resolution=5):
        ### translate into tile based representation ###
        def __coord2Key(coord, stepSize, offset=0.0):
            return math.floor((coord-offset)/stepSize)
        
        def __calRoI(tileCoord, cellCoord):
            if (cellCoord[0] > tileCoord[2]) or (cellCoord[2] < tileCoord[0]):
                return 0
            if (cellCoord[1] > tileCoord[3]) or (cellCoord[3] < tileCoord[1]):
                return 0
            
            ### overlap area ###
            llx, lly, urx, ury = None, None, None, None
            if cellCoord[0] > tileCoord[0]:
                llx = cellCoord[0]
            else:
                llx = tileCoord[0]
            
            if cellCoord[2] > tileCoord[2]:
                urx = tileCoord[2]
            else:
                urx = cellCoord[2]
            
            if cellCoord[1] > tileCoord[1]:
                lly = cellCoord[1]
            else:
                lly = tileCoord[1]
            
            if cellCoord[3] > tileCoord[3]:
                ury = tileCoord[3]
            else:
                ury = cellCoord[3]
            
            #print("OVERLAP, T:{}, C:{}, {}".format(tileCoord, cellCoord, [llx,lly,urx,ury]))
            RoI = float(self.__F2Sprecision((urx-llx)*(ury-lly)))
            cellArea = (cellCoord[2]-cellCoord[0])*(cellCoord[3]-cellCoord[1])
            ratio = float(self.__F2Sprecision(RoI/cellArea, 8))
            return ratio
        
        ### unit: um, power: mW
        import matplotlib
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle

        import numpy as np
        import matplotlib.cm as cm
        import matplotlib.ticker as mticker

        length = math.ceil((self.URX-self.LLX)/resolution)*resolution
        width = math.ceil((self.URY-self.LLY)/resolution)*resolution

        #print(self.LLX, self.LLY, self.URX, self.URY, length, width)
        Xsize = int(length/resolution)
        Ysize = int(width/resolution)
        Xsteps, Ysteps = [self.LLX], [self.LLY]
        for xi in range(Xsize):
            _x = Xsteps[-1]+resolution
            _x = float(self.__F2Sprecision(_x, 4))
            Xsteps.append(_x)
        for yi in range(Ysize):
            _y = Ysteps[-1]+resolution
            _y = float(self.__F2Sprecision(_y, 4))
            Ysteps.append(_y)
        
        self.tileDict.setdefault(resolution, {})
        self.tileDictParams.setdefault(resolution, {"minPWR":None, "maxPWR":None, \
                                                    "LLX":Xsteps[0], "LLY":Ysteps[0], \
                                                    "URX":Xsteps[-1], "URY":Ysteps[-1]})
        tileDict = self.tileDict[resolution]

        for xi in range(len(Xsteps)-1):
            for yi in range(len(Ysteps)-1):
                _key = "_".join([str(xi), str(yi)])
                tileDict.setdefault(_key, {"llx":float(self.__F2Sprecision(Xsteps[xi], 3)), 
                                           "lly":float(self.__F2Sprecision(Ysteps[yi], 3)),
                                           "urx":float(self.__F2Sprecision(Xsteps[xi+1], 3)), 
                                           "ury":float(self.__F2Sprecision(Ysteps[yi+1], 3)),
                                           "CELLS":[], "PWR":0.0, "_PWR":[]})
        
        #print(Xsteps, Ysteps)
        offsetX = self.LLX
        offsetY = self.LLY
        for i in self.dbDict.keys():
            pwr = self.dbDict[i]["PWR"]
            #print(pwr)
            llx = float(self.__F2Sprecision(self.dbDict[i]["llx"]))
            lly = float(self.__F2Sprecision(self.dbDict[i]["lly"]))
            urx = float(self.__F2Sprecision(self.dbDict[i]["urx"]))
            ury = float(self.__F2Sprecision(self.dbDict[i]["ury"]))
            width = float(self.__F2Sprecision(urx-llx))
            height = float(self.__F2Sprecision(ury-lly))

            llxID = __coord2Key(llx, resolution, offsetX)
            llyID = __coord2Key(lly, resolution, offsetY)
            urxID = __coord2Key(urx, resolution, offsetX)
            uryID = __coord2Key(ury, resolution, offsetY)
            if urxID >= Xsize:
                urxID = Xsize-1
            if uryID >= Ysize:
                uryID = Ysize-1

            #print("Cell:{}, ID:{}".format([llx,lly,urx,ury], [llxID,llyID,urxID,uryID]))
            #print("Cell area: {}".format(width*height))
            
            ### overlap region ###
            for orx in range(llxID, urxID+1):
                for ory in range(llyID, uryID+1):
                    _key = "_".join([str(orx), str(ory)])
                    #print(_key, tileDict[_key])
                    #print(tileDict["0_28"])
                    tileCoord = [tileDict[_key]["llx"], tileDict[_key]["lly"], \
                                 tileDict[_key]["urx"], tileDict[_key]["ury"]]
                    ratio = __calRoI(tileCoord, [llx, lly, urx, ury])
                    pwr_ratio = float(self.__F2Sprecision(pwr*ratio, 8))
                    tileDict[_key]["CELLS"].append([i, ratio])
                    tileDict[_key]["_PWR"].append(pwr_ratio)
                    tileDict[_key]["PWR"] = tileDict[_key]["PWR"]+pwr_ratio
        
        min_val, max_val = 1000000, -1000000
        totalPWR = 0.0
        pwrDist = []
        for i in tileDict.keys():
            #pwrDist.append(tileDict[i]["PWR"])
            totalPWR += tileDict[i]["PWR"]
            if min_val > tileDict[i]["PWR"]:
                min_val = tileDict[i]["PWR"]
            if max_val < tileDict[i]["PWR"]:
                max_val = tileDict[i]["PWR"]
            
            if tileDict[i]["PWR"] > 0.00025:
                pwrDist.append(tileDict[i]["PWR"])
        
        self.tileDictParams[resolution]["minPWR"] = min_val
        self.tileDictParams[resolution]["maxPWR"] = max_val
        self.tileDictParams[resolution]["TotalPWR"] = totalPWR

        ### plot distribution ###
        #print(pwrDist)
        #n_bins = 20

        #fig, ax = plt.subplots(1, 1, figsize=[6, 6])
        #ax.hist(pwrDist, bins=n_bins)
        #plt.show()


    def TilePwrAnalysis(self, resolution, topN=10):
        dbDict = self.tileDict[resolution]
        _cells = [(i, float(self.__F2Sprecision(dbDict[i]["PWR"], 8))) for i in dbDict.keys()]
        sortedCells = sorted(_cells, key=lambda x:x[1], reverse=True)

        topNTiles = []
        topDict = {}
        for i in range(topN):
            tileID = sortedCells[i][0]
            topNTiles.append(tileID)
            #print(dbDict[tileID])
        
        for i in topNTiles:
            for ci, c in enumerate(dbDict[i]["CELLS"]):
                cellName = self.dbDict[c[0]]["cellName"]
                pwr = dbDict[i]["_PWR"][ci]
                if cellName in topDict.keys():
                    topDict[cellName]["count"] += 1
                    topDict[cellName]["sum_pwr"] += pwr
                else:
                    topDict.setdefault(cellName, {"count":1, "sum_pwr":pwr})
        
        _cells = [(i, topDict[i]["count"], topDict[i]["sum_pwr"]) for i in topDict.keys()]
        sortedCells = sorted(_cells, key=lambda x:x[2], reverse=True)  ## sorted by the power value
        #print(sortedCells)

        selectedCells = []
        for i in sortedCells:
            cellName = i[0]
            sum_pwr = float(self.__F2Sprecision(self.cellDict[cellName]["sum_pwr"], 8))
            ratio = float(self.__F2Sprecision((sum_pwr/self.TotalPwr)*100, 4))
            selectedCells.append([cellName, sum_pwr, ratio])
            #print([cellName, sum_pwr, ratio])
        
        return selectedCells
        
        """
        ### summary output ###
        outStr = []
        for i in sortedCells:
            _str = "cell: {}, count: {}, power contribution: {}".format(i[0], i[1], i[2])
            outStr.append(_str)

        for i in topNTiles:
            _str = "## Tile:"+i+" llx: {}, lly: {}, urx: {}, ury: {}, pwr: {}".format(
                                 dbDict[i]["llx"], dbDict[i]["lly"], dbDict[i]["urx"], dbDict[i]["ury"],
                                 dbDict[i]["PWR"])
            outStr.append(_str)
            for ci, c in enumerate(dbDict[i]["CELLS"]):
                cellName = self.dbDict[c[0]]["cellName"]
                _str = "\tinst: {}, cell: {}, power contribution: {}".format(c[0], cellName, dbDict[i]["_PWR"][ci])
                outStr.append(_str)
        
        with open("./test.log", "w") as fid:
            fid.write("\n".join(outStr))
        """

    def getTopNHighPD(self, topN=10):
        
        def cellStr(cell):
            return ",".join([cell]+[self.__F2Sprecision(self.dbDict[cell][_k]) for _k in ["llx", "lly", "urx", "ury", "PWR"]])

        _cells = [(i, float(self.__F2Sprecision(self.dbDict[i]["PWR_density"]))) for i in self.dbDict.keys()]
        sortedCells = sorted(_cells, key=lambda x:x[1], reverse=True)
        #print(sortedCells)

        topNCells = []
        topDict = {}
        for i in range(topN):
            cellName = sortedCells[i][0]
            topNCells.append(cellName)
            topDict.setdefault(cellName, {"llx":self.dbDict[cellName]["llx"],
                                          "lly":self.dbDict[cellName]["lly"],
                                          "urx":self.dbDict[cellName]["urx"],
                                          "ury":self.dbDict[cellName]["ury"],
                                          "0.5": [], "1.0":[], "2.0":[]})
        

        for i in self.dbDict.keys():
            _llx = self.dbDict[i]["llx"]
            _lly = self.dbDict[i]["lly"]
            _urx = self.dbDict[i]["urx"]
            _ury = self.dbDict[i]["ury"]
            for tc in topNCells:
                if i == tc:
                    break

                for dist in [0.5, 1.0, 2.0]:
                    rllx = topDict[tc]["llx"]-dist
                    rlly = topDict[tc]["lly"]-dist
                    rurx = topDict[tc]["urx"]+dist
                    rury = topDict[tc]["ury"]+dist
                    if _llx > rllx and _urx < rurx and _lly > rlly and _ury < rury:
                        topDict[tc][str(dist)].append(i)
        
        ### summary output ###
        outStr = []
        for i in topNCells:
            _str = "##"+cellStr(i)
            outStr.append(_str)
            
            for dist in [0.5, 1.0, 2.0]:
                _tmpStr = []
                _totalPwr = self.dbDict[i]["PWR"]
                for _c in topDict[i][str(dist)]:
                    _str = "  "+cellStr(_c)
                    _tmpStr.append(_str)
                    _totalPwr += self.dbDict[_c]["PWR"]
                
                _totalPwr = self.__F2Sprecision(_totalPwr)
                _str = ",".join([str(dist)]+[self.__F2Sprecision(topDict[i][_k]-dist) for _k in ["llx", "lly", "urx", "ury"]]+[_totalPwr])
                outStr.append(_str)
                outStr = outStr + _tmpStr
            
            outStr.append("")
        
        with open("./test.log", "w") as fid:
            fid.write("\n".join(outStr))


        return topNCells
    
    def plot(self, ptype=["IPF"],
             highlighted=[], saveImg="pwr.png", isShow=False):
        import matplotlib
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle

        import numpy as np
        import matplotlib.cm as cm
        import matplotlib.ticker as mticker
    
        fig, ax = plt.subplots(1, 1, figsize=[8, 8])

        #rng = np.random.default_rng(seed=1900000)
        #data = rng.standard_normal((10, 5))
        #print(data)
        if ptype[0] == "IPF":
            LLX = self.LLX
            LLY = self.LLY
            URX = self.URX
            URY = self.URY
            minPWR = self.minPwr
            maxPWR = self.maxPwr
            TotalPWR = self.TotalPwr
            showDict = self.dbDict
        elif ptype[0] == "TILE":
            LLX = self.tileDictParams[ptype[1]]["LLX"]
            LLY = self.tileDictParams[ptype[1]]["LLY"]
            URX = self.tileDictParams[ptype[1]]["URX"]
            URY = self.tileDictParams[ptype[1]]["URY"]
            minPWR = self.tileDictParams[ptype[1]]["minPWR"]
            maxPWR = self.tileDictParams[ptype[1]]["maxPWR"]
            TotalPWR = self.tileDictParams[ptype[1]]["TotalPWR"]
            showDict = self.tileDict[ptype[1]]
        else:
            pass

        #AreaX = math.ceil(self.URX-self.LLX)
        #AreaY = math.ceil(self.URY-self.LLY)
        Xsteps = np.linspace(LLX, URX, 10)
        Ysteps = np.linspace(LLY, URY, 10)
        #pixels = np.zeros((AreaX+1, AreaY+1))
        pixels = np.zeros((1, 1))

        min_val = float(self.__F2Sprecision(minPWR))
        max_val = float(self.__F2Sprecision(maxPWR))
        mid_val = float("{:.3f}".format((max_val+min_val)*0.5))
        my_cmap = matplotlib.colormaps.get_cmap("coolwarm")
        norm = matplotlib.colors.Normalize(min_val, max_val)

        for i in showDict.keys():
            pwr = showDict[i]["PWR"]
            color_i = my_cmap(norm(pwr))
            llx = float(self.__F2Sprecision(showDict[i]["llx"]))
            lly = float(self.__F2Sprecision(showDict[i]["lly"]))
            urx = float(self.__F2Sprecision(showDict[i]["urx"]))
            ury = float(self.__F2Sprecision(showDict[i]["ury"]))
            width = float(self.__F2Sprecision(urx-llx))
            height = float(self.__F2Sprecision(ury-lly))

            if i in highlighted:
                rect = Rectangle((llx, lly), width=width, height=height, facecolor=color_i, edgecolor="yellow", linewidth=10)
            else:
                rect = Rectangle((llx, lly), width=width, height=height, color=color_i)

            ax.add_patch(rect)

        #xi = 20
        #color_i = my_cmap(norm(xi))
        #print(color_i)
        #rect = Rectangle((1, 1), 2, 2, color=color_i)
        #ax.add_patch(rect)

        im = ax.imshow(pixels, vmin=min_val, vmax=max_val, cmap="coolwarm")
        
        strTotalPwr = "{:.3f}".format(TotalPWR)
        ax.set_title("Total PWR:{} mW".format(strTotalPwr))
        ax.invert_yaxis()
        ax.set_xticks(Xsteps)
        ax.set_yticks(Ysteps)
        
        ## Add colorbar, make sure to specify tick locations to match desired ticklabels ##
        cax = fig.add_axes([ax.get_position().x1+0.02, ax.get_position().y0, 0.02, ax.get_position().height])
        cbar = fig.colorbar(im, cax=cax, ticks=[min_val, mid_val, max_val],
                            format=mticker.FixedFormatter(["<{}".format(min_val), "{}".format(mid_val), ">{}".format(max_val)]), extend="both")
        
        #cbar = fig.colorbar(cax, ticks=[min_val, mid_val, max_val],
        #                    format=mticker.FixedFormatter(["<{}".format(min_val), "{}".format(mid_val), ">{}".format(max_val)]),
        #                    extend="both")
    
        labels = cbar.ax.get_yticklabels()
        labels[0].set_verticalalignment("top")
        labels[-1].set_verticalalignment("bottom")

        imgPath = os.path.join(self.outputFolder, saveImg)
        plt.savefig(imgPath, bbox_inches="tight")
        plt.close(fig)
        return imgPath


if __name__ == "__main__":
    ## python FCpowermap.py --fc_powermap=./thermal_case.csv

    args = arg().parse_args()
    #FCpowermap2RHSCETmhs(args.fc_powermap, args.outputFolder, args.outputName)

    #designArea = [0, 0, 48, 48]
    #FCipf2RHSCETmhs(args.fc_powermap, args.outputFolder, args.outputName, designArea)

    #ipfPath = "./pwd.mhs"
    #plotIPF(ipfPath)

    FCpwrView = FCPowerView(args.fc_powerfile, "CSV")
    FCpwrView.RHSCETmhs()

    #topPwrCells = FCpwrView.getTopNHotSpots()
    topPwrCells = []
    FCpwrView.plot(highlighted=topPwrCells)
    

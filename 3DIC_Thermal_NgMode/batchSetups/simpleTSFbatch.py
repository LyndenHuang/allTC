import os
import sys
import re
import copy
import json
import argparse

from setups import MetalDensity
from setups import FakeTotemGen
from setups import FCpowermap
from setups import utilities

ANSYSLM = "source /nfs/site/disks/x5e2d_gwa_chienchi_001/Tools/licenses/ansys.csh"

CASELIBRARY = {
    "TD+BD_01": "stackDIE_TD_BD.tcl",
}

def arg():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--outputName", type=str, required=False, default="fake.tech", help="name") 
    parser.add_argument(
        "--outputFolder", type=str, required=False, default="./", help="folder place")
    parser.add_argument(
        "--json", type=str, required=False, help="stacking conf")

    return parser

class simpleTFSBatchRun:
    def __init__(self, jsonConf, outputFolder="./BatchRun"):
        self.root = outputFolder
        self.jsonConf = jsonConf

        self.setupDict = None

        self.runCMDDict = {}
        self.runCMDList = []

        self.__readJSON()
    
    def __F2Sprecision(self, fval, precision=5):
        prec = "{:."+str(precision)+"f}"
        return prec.format(fval)
    
    def __readJSON(self):
        if not os.path.isfile(self.jsonConf):
            print("[ERROR] {} path not found".format(self.jsonConf))
            return
        
        print("{} Parsing...".format(self.jsonConf))
        with open(self.jsonConf, "r") as fid:
            self.setupDict = json.load(fid)
        
        print(self.setupDict)
    
    def genSweepCase(self):
        sweepJSON = self.setupDict["SWEEP"]
        caseJSON = copy.deepcopy(self.setupDict["CORE"])

        caseCount = 1
        ### IID & UNION select one ###
        if "IID" in sweepJSON.keys():
            ### IID, up to 2 list ###
            if len(sweepJSON["IID"].keys()) == 1:
                for pi, p in enumerate(sweepJSON["IID"].keys()):
                    ps = p.split(":")
                    for parai, param in enumerate(sweepJSON["IID"][p]):
                        if len(ps) == 1:
                            caseJSON[ps[0]] = param
                        elif len(ps) == 2:
                            caseJSON[ps[0]][ps[1]] = param
                        elif len(ps) == 3:
                            caseJSON[ps[0]][ps[1]][ps[2]] = param
                        else:
                            print("<ERROR> Hier. > 3")
                    
                        #print(caseJSON)
                        #if type(param) is list:
                        #    _param = [str(_p) for _p in param]
                        #    caseFolder = "_".join(["S"+str(caseCount)]+["-".join(ps)]+_param)
                        #else:
                        #    caseFolder = "_".join(["S"+str(caseCount)]+["-".join(ps)]+[str(param)])
                        #print(caseFolder)
                        caseFolder = "_".join(["S"+str(caseCount), "P"+str(pi)+"_"+str(_parai)])
                        
                        self.__genCase(caseJSON, caseFolder)
                        caseCount += 1
        
            elif len(sweepJSON["IID"].keys()) == 2:
                pass
            else:
                print("<ERROR> No support for IID list > 2")
        
        elif "UNION" in sweepJSON.keys():
            params = len(sweepJSON["UNION"][list(sweepJSON["UNION"].keys())[0]])
            for _id in range(params):
                _casename = []
                for pi, p in enumerate(sweepJSON["UNION"].keys()):
                    ps = p.split(":")
                    if len(ps) == 1:
                        caseJSON[ps[0]] = sweepJSON["UNION"][p][_id]
                    elif len(ps) == 2:
                        caseJSON[ps[0]][ps[1]] = sweepJSON["UNION"][p][_id]
                    elif len(ps) == 3:
                        caseJSON[ps[0]][ps[1]][ps[2]] = sweepJSON["UNION"][p][_id]
                    else:
                        print("<ERROR> Hier. > 3")
                
                    #if type(sweepJSON["UNION"][p][_id]) is list:
                    #    _param = [str(_p) for _p in sweepJSON["UNION"][p][_id]]
                    #    _casename.append("-".join(_param))
                    #else:
                    #    _casename.append(str(sweepJSON["UNION"][p][_id]))
                    _casename.append("P{}_{}".format(str(pi), str(_id)))
                
                caseFolder = "_".join(["S"+str(caseCount)]+["_".join(_casename)])
                #print(caseFolder, caseJSON)
                self.__genCase(caseJSON, caseFolder)
                caseCount += 1

    def genStackingCase(self, caseFolder="stack", caseName="MAIN"):
        runStacksCMD = []
        caseDir = os.path.join(self.root, caseFolder)
        caseDB = os.path.join(caseDir, "DB")

        ambT = self.setupDict["SCRIPT_SETUP"]["BOUNDARY_CONDITIONS"]["AMBIENT_T"]
        HTC = self.setupDict["SCRIPT_SETUP"]["BOUNDARY_CONDITIONS"]["HTC"]       ### [TOP_HTC, BOT_HTC, Side_HTC]
        topHTC = HTC[0]
        botHTC = HTC[1]
        sideHTC = HTC[2]

        DIEparaDict = {"RUN_DIR":caseDir, "NAME":caseName, \
                       "TTF":None, \
                       "AMBIENT_T":str(ambT), "TOPBC":str(topHTC), "BOTBC":str(botHTC), "SIDEBC":str(sideHTC) }
        TProfiles = []
        for k in self.setupDict.keys():
            if k in ["SCRIPT_SETUP", "ASSEMBLE", "METAL_DENSITY_LIBRARY"]:
                ## non-die name ##
                pass
            elif "//" in k:
                ## comment line ##
                pass
            else:
                print("DIE: {}".format(k))
                dieName = k
                dieJSON = self.setupDict[k]

                TTFPath = dieJSON["THERMALTF"]["PATH"]
                TFDIE = dieJSON["THERMALTF"]["NAME"]

                dieMapPrefix = self.setupDict["SCRIPT_SETUP"]["DIE_NAME_MAP"][k]
                
                runCMD, die_length, die_width, die_height, CTMpath = self.__genCTM(dieJSON, k, caseFolder)

                DIEparaDict["TTF"] = TTFPath
                DIEparaDict.setdefault("{}LENGTH".format(dieMapPrefix), die_length)
                DIEparaDict.setdefault("{}WIDTH".format(dieMapPrefix), die_width)
                DIEparaDict.setdefault("{}HEIGHT".format(dieMapPrefix), die_height)
                DIEparaDict.setdefault("{}TF".format(dieMapPrefix), TFDIE)
                DIEparaDict.setdefault("{}CTM".format(dieMapPrefix), CTMpath)
                TProfiles.append(k)

                for cmd in runCMD:
                    runStacksCMD.append(cmd)
        
        print("<INFO> DIE setup parameters: {}".format(DIEparaDict))
        refETscript = CASELIBRARY[self.setupDict["SCRIPT_SETUP"]["CASE"]]
        runCMD, TProfiles = self.__genET(caseDir, caseDB, DIEparaDict, refETscript, caseName, TProfiles)

        for cmd in runCMD:
            runStacksCMD.append(cmd)

        ### create jobs ###
        jobName = "J#{}".format(os.path.basename(caseDir))
        self.runCMDDict.setdefault(jobName, {"#runCMD":len(runStacksCMD), "runCMD":runStacksCMD, "status":"READY", "results":TProfiles})
        self.runCMDList.append(jobName)
        print(runStacksCMD, self.runCMDDict)
        
    
    def genCoreCase(self, caseFolder="core"):
        caseJSON = self.setupDict["CORE"]
        self.__genCase(caseJSON, caseFolder)
    
    def runBatch(self):
        for job in self.runCMDList:
            print("<INFO> submit Job: {}".format(job))
            for subID in range(self.runCMDDict[job]["#runCMD"]):
                runCMD = self.runCMDDict[job]["runCMD"][subID]
                isDone = utilities.submitJob(runCMD[0], runcshPath=runCMD[1], progressBar=runCMD[2], checkFiles=runCMD[3])

                if isDone:
                    self.runCMDDict[job]["status"] = "DONE"
    
    def runCases(self, caseList):
        for job in caseList:
            print("<INFO> submit Job: {}".format(job))
            for subID in range(self.runCMDDict[job]["#runCMD"]):
                runCMD = self.runCMDDict[job]["runCMD"][subID]
                isDone = utilities.submitJob(runCMD[0], runcshPath=runCMD[1], progressBar=runCMD[2], checkFiles=runCMD[3])

                if isDone:
                    self.runCMDDict[job]["status"] = "DONE"
    
    def __genET(self, caseDir, caseDB, DIEparaDict, refETscript, caseName, _TProfiles=["DIE"]):
        runCMD = []
        templateScript = os.path.join(os.path.join(os.getcwd(), "ET_scripts"), refETscript)
        ETscript = utilities.createETscript(DIEparaDict, template=templateScript, outputFolder=caseDB, outputName="DEMO_et.tcl")

        ETFolder = os.path.join(caseDir, "{}_et".format(caseName))
        runcmd = ["#!/bin/csh", "rm -rf {}".format(ETFolder), \
                  ANSYSLM, \
                  "redhawk_sc_et -3dic -ng {}".format(ETscript)]
        
        runcshPath = os.path.join(caseDB, "runET.csh")
        TProfiles = []
        for p in _TProfiles:
            TProfile = os.path.join(ETFolder, "ThermalProfile_{}.txt".format(p))
            TProfiles.append(TProfile)
        
        check = [os.path.join(ETFolder, "analysis/STATIC_RUN/thermal/STATIC_RUN.dbg")] + TProfiles
        
        runCMD.append([runcmd, runcshPath, None, check])
        return runCMD, TProfiles


    def __genCTM(self, caseJSON, DIEName, caseFolder):
        runCMD = []
        caseDir = os.path.join(self.root, caseFolder)
        if not os.path.isdir(caseDir):
            os.makedirs(caseDir, 0o755)
        
        caseDB = os.path.join(caseDir, "DB")
        if not os.path.isdir(caseDB):
            os.makedirs(caseDB, 0o755)
        
        totemPath = caseJSON["TOTEMTF"]
        layermapPath = caseJSON["LAYERMAP"]
        resolution = int(caseJSON["RESOLUTION"])

        totemEM = FakeTotemGen.parseTotemTF(totemPath)
        totemEM.parsing()

        LLX, LLY = 0, 0
        if "OFFSET" in caseJSON["DESIGN_AREA"].keys():
            LLX = int(caseJSON["DESIGN_AREA"]["OFFSET"][0])
            LLY = int(caseJSON["DESIGN_AREA"]["OFFSET"][1])

        URX = (int(caseJSON["DESIGN_AREA"]["SIZE"][0])*resolution) + LLX
        URY = (int(caseJSON["DESIGN_AREA"]["SIZE"][1])*resolution) + LLY
        DIE_X = self.__F2Sprecision(URX-LLX, 3)
        DIE_Y = self.__F2Sprecision(URY-LLY, 3)

        ### global power cell ###
        globalPWR = []
        isUsingPowerMap = False
        if "POWER_SOURCE" in caseJSON["DESIGN_AREA"].keys():
            if caseJSON["DESIGN_AREA"]["POWER_SOURCE"]["TYPE"] in ["UNIFORM"]:
                if "POWER_VAL" in caseJSON["DESIGN_AREA"]["POWER_SOURCE"].keys():
                    _pwr = caseJSON["DESIGN_AREA"]["POWER_SOURCE"]["POWER_VAL"]   ## unit: mW
                    _pwr = self.__F2Sprecision(float(_pwr), precision=8)
                    
                elif "POWER_DENSITY" in caseJSON["DESIGN_AREA"]["POWER_SOURCE"].keys():
                    power_density = caseJSON["DESIGN_AREA"]["POWER_SOURCE"]["POWER_DENSITY"]
                    area = float(DIE_X)*float(DIE_Y)
                    _pwr = power_density*area*0.000000000001   # 1e-12 to unit "m"
                    _pwr = _pwr*1000   ## to mW
                    _pwr = self.__F2Sprecision(_pwr, precision=8)
                
                _str = "{},{},{},{},{},{},{}".format("G01","G01",LLX,LLY,URX,URY,_pwr)
                globalPWR.append(_str)
            
            if caseJSON["DESIGN_AREA"]["POWER_SOURCE"]["TYPE"] in ["POWERMAP"]:
                powermapPath = caseJSON["DESIGN_AREA"]["POWER_SOURCE"]["PATH"]
                isUsingPowerMap = True

        
        ### local power cell ###
        localPWRs = []
        pwrCells = []
        for k in caseJSON.keys():
            if "POWER_CELL" in k:
                pwrCells.append(k)
        
        for i, cell in enumerate(pwrCells):
            _llx = caseJSON[cell]["OFFSET"][0]*resolution
            _lly = caseJSON[cell]["OFFSET"][1]*resolution
            _llx = self.__F2Sprecision(float(_llx), precision=4)
            _lly = self.__F2Sprecision(float(_lly), precision=4)
            sizeX = caseJSON[cell]["SIZE"][0]*resolution
            sizeY = caseJSON[cell]["SIZE"][1]*resolution
            _urx = self.__F2Sprecision(float(_llx)+float(sizeX), precision=4)
            _ury = self.__F2Sprecision(float(_lly)+float(sizeY), precision=4)
            if "POWER_DENSITY" in caseJSON[cell].keys():  ## unit: W/m^2
                power_density = caseJSON[cell]["POWER_DENSITY"]
                area = sizeX*sizeY
                #print(area, resolution)
                _pwr = power_density*area*0.000000000001   # 1e-12 to unit "m"
                _pwr = _pwr*1000   ## to mW
                _pwr = self.__F2Sprecision(_pwr, precision=8)
                
            elif "POWER_VAL" in caseJSON[cell].keys():  ## unit: mW
                _pwr = caseJSON[cell]["POWER_VAL"]
                _pwr = self.__F2Sprecision(_pwr, precision=8)
            
            _str = "{},{},{},{},{},{},{}".format("L{}".format(i+1), "L{}".format(i+1), \
                                                 _llx, _lly, _urx, _ury, _pwr)
            localPWRs.append(_str)
        
        #print(localPWRs)
        #sys.exit(1)

        ### setup global metal density ###
        mdSetupPath, ETMDpath = None, None
        MDType = caseJSON["METAL_DENSITY_MODEL"]

        if "FILE_SETUP" in self.setupDict["METAL_DENSITY_LIBRARY"][MDType].keys():
            if self.setupDict["METAL_DENSITY_LIBRARY"][MDType]["FILE_SETUP"]["TYPE"] == "ORIGINAL":
                MDPath_org = self.setupDict["METAL_DENSITY_LIBRARY"][MDType]["FILE_SETUP"]["PATH"]
                mdSetupPath = MetalDensity.translate2MDSetup(givenMD=MDPath_org, totemPath=totemPath, layermapPath=layermapPath,
                                                             outputFolder=caseDB)
            
            elif self.setupDict["METAL_DENSITY_LIBRARY"][MDType]["FILE_SETUP"]["TYPE"] == "SETUP":
                mdSetupPath = self.setupDict["METAL_DENSITY_LIBRARY"][MDType]["FILE_SETUP"]["PATH"]
            
            elif self.setupDict["METAL_DENSITY_LIBRARY"][MDType]["FILE_SETUP"]["TYPE"] == "ETCSV":
                ETMDpath = self.setupDict["METAL_DENSITY_LIBRARY"][MDType]["FILE_SETUP"]["PATH"]
            
            else:
                print("<ERROR> Non supported type: {}".format(self.setupDict["METAL_DENSITY_LIBRARY"][MDType]["FILE_SETUP"]["TYPE"]))

        
        else:
            mdStr = []
            globalMD = []
            METAL = self.setupDict["METAL_DENSITY_LIBRARY"][MDType]["METAL"]
            VIA = self.setupDict["METAL_DENSITY_LIBRARY"][MDType]["VIA"]
            for m in METAL.keys():
                _mdStr = None
                md = METAL[m]["DENSITY"]
                if METAL[m]["LAYERS"] in ["GLOBAL"]:
                    _mdStr = "Metal_global,{},{},{},{},{}".format(LLX,LLY,URX,URY,md)
                    
                if _mdStr:
                    mdStr.append(_mdStr)
                
            for v in VIA.keys():
                _mdStr = None
                md = VIA[v]["DENSITY"]
                if VIA[v]["LAYERS"] in ["GLOBAL"]:
                    _mdStr = "Via_global,{},{},{},{},{}".format(LLX,LLY,URX,URY,md)
                    
                if _mdStr:
                    mdStr.append(_mdStr)
            
            mdSetupPath = os.path.join(caseDB, "{}md.setup".format(DIEName))
            with open(mdSetupPath, "w") as fid:
                fid.write("\n".join(mdStr))

        ### setup local metal density: TODO ###


        ### gen power ipf ###
        pwrStr = ["inst,cell,llx,lly,urx,ury,total_pwr"]

        for p in globalPWR+localPWRs:
            pwrStr.append(p)
        
        pwrPath = None
        if isUsingPowerMap:
            pwrPath = powermapPath
            print("<INFO> power map path: {}".format(pwrPath))
        else:
            pwrPath = os.path.join(caseDB, "{}pwr.csv".format(DIEName))
            with open(pwrPath, "w") as fid:
                fid.write("\n".join(pwrStr))

        ### setup CTM ###
        if pwrPath is None:
            print("<ERROR> No power profile is specified")
            return

        pwrView = FCpowermap.FCPowerView(pwrPath, "CSV", DesignArea=[LLX, LLY, URX, URY])
        designArea, ETmhsPath = pwrView.RHSCETmhs(outputFolder=caseDB, outputName="{}pwd.mhs".format(DIEName))

        if mdSetupPath is None:
            if ETMDpath is None:
                print("<ERROR> No metal density model is specified")
                return
        else:
            MetalDensity.loadMetalDensitySetup(totemPath, mdSetupPath, layermapPath, area=[LLX, LLY, URX, URY], outputFolder=caseDB, ETMDName="{}density.csv".format(DIEName))
            ETMDpath = os.path.join(caseDB, "{}density.csv".format(DIEName))

        ### gen CTM ###
        ctmName = "{}_CTM_{}nm".format(DIEName, str(resolution))
        CTMparaDict = {"RUN_DIR":caseDir, "CTMNAME":ctmName, "DIE_LENGTH":DIE_X, "DIE_WIDTH":DIE_Y, \
                       "RESOLUTION":str(resolution), "PWRMAP":ETmhsPath, "DENSITY":ETMDpath, "TOTEM_TF":totemPath}
        
        templateScript = os.path.join(os.path.join(os.getcwd(), "ET_scripts"), "prototypeCTM.tcl")
        ETscript = utilities.createETscript(CTMparaDict, template=templateScript, outputFolder=caseDB, outputName="genPrototype{}CTM.tcl".format(DIEName))
        
        runcmd = ["#!/bin/csh", "rm -rf {}".format(os.path.join(caseDir, "_CTM*")),\
                  ANSYSLM, \
                  "redhawk_sc_et -3dic -ng {}".format(ETscript)]
        
        runcshPath = os.path.join(caseDB, "gen{}CTM.csh".format(DIEName))
        CTMpath = os.path.join(os.path.join(CTMparaDict["RUN_DIR"], "CTM"), CTMparaDict["CTMNAME"]+".tar.gz")
        check = [CTMpath]
        
        runCMD.append([runcmd, runcshPath, None, check])   ### [runcmd, runcshPath, progressBar, checkFiles]
        #print("runCMD: {}".format(runCMD))

        die_height = totemEM.getDieHeight()

        return runCMD, DIE_X, DIE_Y, die_height, CTMpath
        
    
    def __genCase(self, caseJSON, caseFolder):
        runCMD = []
        caseDir = os.path.join(self.root, caseFolder)
        if not os.path.isdir(caseDir):
            os.makedirs(caseDir, 0o755)
        
        caseDB = os.path.join(caseDir, "DB")
        if not os.path.isdir(caseDB):
            os.makedirs(caseDB, 0o755)
        
        totemPath = caseJSON["TOTEMTF"]
        layermapPath = caseJSON["LAYERMAP"]
        resolution = int(caseJSON["RESOLUTION"])

        totemEM = FakeTotemGen.parseTotemTF(totemPath)
        totemEM.parsing()

        LLX, LLY = 0, 0
        URX = int(caseJSON["DESIGN_AREA"]["SIZE"][0])*resolution
        URY = int(caseJSON["DESIGN_AREA"]["SIZE"][1])*resolution
        DIE_X = self.__F2Sprecision(URX-LLX, 3)
        DIE_Y = self.__F2Sprecision(URY-LLY, 3)

        ### global power cell ###
        globalPWR = []
        isUsingPowerMap = False
        if "POWER_SOURCE" in caseJSON["DESIGN_AREA"].keys():
            if caseJSON["DESIGN_AREA"]["POWER_SOURCE"]["TYPE"] in ["UNIFORM"]:
                if "POWER_VAL" in caseJSON["DESIGN_AREA"]["POWER_SOURCE"].keys():
                    _pwr = caseJSON["DESIGN_AREA"]["POWER_SOURCE"]["POWER_VAL"]   ## unit: mW
                    _pwr = self.__F2Sprecision(float(_pwr), precision=8)
                    
                elif "POWER_DENSITY" in caseJSON["DESIGN_AREA"]["POWER_SOURCE"].keys():
                    power_density = caseJSON["DESIGN_AREA"]["POWER_SOURCE"]["POWER_DENSITY"]
                    area = float(DIE_X)*float(DIE_Y)
                    _pwr = power_density*area*0.000000000001   # 1e-12 to unit "m"
                    _pwr = _pwr*1000   ## to mW
                    _pwr = self.__F2Sprecision(_pwr, precision=8)
                
                _str = "{},{},{},{},{},{},{}".format("G01","G01",LLX,LLY,URX,URY,_pwr)
                globalPWR.append(_str)
            
            if caseJSON["DESIGN_AREA"]["POWER_SOURCE"]["TYPE"] in ["POWERMAP"]:
                powermapPath = caseJSON["DESIGN_AREA"]["POWER_SOURCE"]["PATH"]
                isUsingPowerMap = True

        
        ### local power cell ###
        localPWRs = []
        pwrCells = []
        for k in caseJSON.keys():
            if "POWER_CELL" in k:
                pwrCells.append(k)
        
        for i, cell in enumerate(pwrCells):
            _llx = caseJSON[cell]["OFFSET"][0]*resolution
            _lly = caseJSON[cell]["OFFSET"][1]*resolution
            _llx = self.__F2Sprecision(float(_llx), precision=4)
            _lly = self.__F2Sprecision(float(_lly), precision=4)
            sizeX = caseJSON[cell]["SIZE"][0]*resolution
            sizeY = caseJSON[cell]["SIZE"][1]*resolution
            _urx = self.__F2Sprecision(float(_llx)+float(sizeX), precision=4)
            _ury = self.__F2Sprecision(float(_lly)+float(sizeY), precision=4)
            if "POWER_DENSITY" in caseJSON[cell].keys():  ## unit: W/m^2
                power_density = caseJSON[cell]["POWER_DENSITY"]
                area = sizeX*sizeY
                #print(area, resolution)
                _pwr = power_density*area*0.000000000001   # 1e-12 to unit "m"
                _pwr = _pwr*1000   ## to mW
                _pwr = self.__F2Sprecision(_pwr, precision=8)
                
            elif "POWER_VAL" in caseJSON[cell].keys():  ## unit: mW
                _pwr = caseJSON[cell]["POWER_VAL"]
                _pwr = self.__F2Sprecision(_pwr, precision=8)
            
            _str = "{},{},{},{},{},{},{}".format("L{}".format(i+1), "L{}".format(i+1), \
                                                 _llx, _lly, _urx, _ury, _pwr)
            localPWRs.append(_str)
        
        #print(localPWRs)
        #sys.exit(1)

        ### setup global metal density ###
        mdSetupPath, ETMDpath = None, None
        MDType = caseJSON["METAL_DENSITY_MODEL"]

        if "FILE_SETUP" in self.setupDict["METAL_DENSITY_LIBRARY"][MDType].keys():
            if self.setupDict["METAL_DENSITY_LIBRARY"][MDType]["FILE_SETUP"]["TYPE"] == "ORIGINAL":
                MDPath_org = self.setupDict["METAL_DENSITY_LIBRARY"][MDType]["FILE_SETUP"]["PATH"]
                mdSetupPath = MetalDensity.translate2MDSetup(givenMD=MDPath_org, totemPath=totemPath, layermapPath=layermapPath,
                                                             outputFolder=caseDB)
            
            elif self.setupDict["METAL_DENSITY_LIBRARY"][MDType]["FILE_SETUP"]["TYPE"] == "SETUP":
                mdSetupPath = self.setupDict["METAL_DENSITY_LIBRARY"][MDType]["FILE_SETUP"]["PATH"]
            
            elif self.setupDict["METAL_DENSITY_LIBRARY"][MDType]["FILE_SETUP"]["TYPE"] == "ETCSV":
                ETMDpath = self.setupDict["METAL_DENSITY_LIBRARY"][MDType]["FILE_SETUP"]["PATH"]
            
            else:
                print("<ERROR> Non supported type: {}".format(self.setupDict["METAL_DENSITY_LIBRARY"][MDType]["FILE_SETUP"]["TYPE"]))

        
        else:
            mdStr = []
            globalMD = []
            METAL = self.setupDict["METAL_DENSITY_LIBRARY"][MDType]["METAL"]
            VIA = self.setupDict["METAL_DENSITY_LIBRARY"][MDType]["VIA"]
            for m in METAL.keys():
                _mdStr = None
                md = METAL[m]["DENSITY"]
                if METAL[m]["LAYERS"] in ["GLOBAL"]:
                    _mdStr = "Metal_global,{},{},{},{},{}".format(LLX,LLY,URX,URY,md)
                    
                if _mdStr:
                    mdStr.append(_mdStr)
                
            for v in VIA.keys():
                _mdStr = None
                md = VIA[v]["DENSITY"]
                if VIA[v]["LAYERS"] in ["GLOBAL"]:
                    _mdStr = "Via_global,{},{},{},{},{}".format(LLX,LLY,URX,URY,md)
                    
                if _mdStr:
                    mdStr.append(_mdStr)
            
            mdSetupPath = os.path.join(caseDB, "md.setup")
            with open(mdSetupPath, "w") as fid:
                fid.write("\n".join(mdStr))

        ### setup local metal density: TODO ###


        ### gen power ipf ###
        pwrStr = ["inst,cell,llx,lly,urx,ury,total_pwr"]

        for p in globalPWR+localPWRs:
            pwrStr.append(p)
        
        pwrPath = None
        if isUsingPowerMap:
            pwrPath = powermapPath
        else:
            pwrPath = os.path.join(caseDB, "pwr.csv")
            with open(pwrPath, "w") as fid:
                fid.write("\n".join(pwrStr))

        ### setup CTM ###
        if pwrPath is None:
            print("<ERROR> No power profile is specified")
            return

        pwrView = FCpowermap.FCPowerView(pwrPath, "CSV", DesignArea=[LLX, LLY, URX, URY])
        designArea, ETmhsPath = pwrView.RHSCETmhs(outputFolder=caseDB)

        if mdSetupPath is None:
            if ETMDpath is None:
                print("<ERROR> No metal density model is specified")
                return
        else:
            MetalDensity.loadMetalDensitySetup(totemPath, mdSetupPath, layermapPath, area=[LLX, LLY, URX, URY], outputFolder=caseDB, ETMDName="density.csv")
            ETMDpath = os.path.join(caseDB, "density.csv")

        ### gen CTM ###
        ctmName = "CTM{}nm".format(str(resolution))
        CTMparaDict = {"RUN_DIR":caseDir, "CTMNAME":ctmName, "DIE_LENGTH":DIE_X, "DIE_WIDTH":DIE_Y, \
                       "RESOLUTION":str(resolution), "PWRMAP":ETmhsPath, "DENSITY":ETMDpath, "TOTEM_TF":totemPath}
        
        templateScript = os.path.join(os.path.join(os.getcwd(), "ET_scripts"), "prototypeCTM.tcl")
        ETscript = utilities.createETscript(CTMparaDict, template=templateScript, outputFolder=caseDB, outputName="genPrototypeCTM.tcl")
        
        runcmd = ["#!/bin/csh", "rm -rf {}".format(os.path.join(caseDir, "_CTM*")),\
                  ANSYSLM, \
                  "redhawk_sc_et -3dic -ng {}".format(ETscript)]
        
        runcshPath = os.path.join(caseDB, "genCTM.csh")
        CTMpath = os.path.join(os.path.join(CTMparaDict["RUN_DIR"], "CTM"), CTMparaDict["CTMNAME"]+".tar.gz")
        check = [CTMpath]
        
        runCMD.append([runcmd, runcshPath, None, check])   ### [runcmd, runcshPath, progressBar, checkFiles]

        ### gen ET script ###
        die_height = totemEM.getDieHeight()
        TTFPath = caseJSON["THERMALTF"]["PATH"]
        TFDIE = caseJSON["THERMALTF"]["NAME"]
        ambT = caseJSON["AMBIENT_T"]
        HTC = caseJSON["HTC"]       ### [TOP_HTC, BOT_HTC, Side_HTC]
        topHTC = HTC[0]
        botHTC = HTC[1]
        sideHTC = HTC[2]

        #print(die_height, topHTC, botHTC, sideHTC)
        DIEparaDict = {"RUN_DIR":caseDir, "NAME":"MAIN", "CTM":CTMpath, "DIE_LENGTH":DIE_X, \
                       "DIE_WIDTH":DIE_Y, "DIE_HEIGHT":str(die_height), "TTF":TTFPath, "TFDIE":TFDIE, \
                       "AMBIENT_T":str(ambT), "TOPBC":str(topHTC), "BOTBC":str(botHTC) }
        
        templateScript = os.path.join(os.path.join(os.getcwd(), "ET_scripts"), "signalDIE.tcl")
        ETscript = utilities.createETscript(DIEparaDict, template=templateScript, outputFolder=caseDB, outputName="DEMO_et.tcl")

        ETFolder = os.path.join(caseDir, "MAIN_et")
        runcmd = ["#!/bin/csh", "rm -rf {}".format(ETFolder), \
                  ANSYSLM, \
                  "redhawk_sc_et -3dic -ng {}".format(ETscript)]
        
        runcshPath = os.path.join(caseDB, "runET.csh")
        TProfile = os.path.join(ETFolder, "ThermalProfile_DIE.txt")
        check = [os.path.join(ETFolder, "analysis/STATIC_RUN/thermal/STATIC_RUN.dbg"), \
                 TProfile]
        
        runCMD.append([runcmd, runcshPath, None, check])
        
        jobName = "J#{}".format(caseFolder)

        self.runCMDDict.setdefault(jobName, {"#runCMD":len(runCMD), "runCMD":runCMD, "status":"READY", "results":[TProfile]})
        self.runCMDList.append(jobName)
        


if __name__ == "__main__":
    ### command: python FakeTotemGen.py --conf=./setup.conf 
    ###                          --outputName=<NAME> --outputFolder=<>
    #args = arg().parse_args()

    confPath = "./configures/BD_TD_v010a.json" #"./configures/TSF_org.json"
    tfsBatch = simpleTFSBatchRun(confPath, "StackingT")

    #tfsBatch.genCoreCase(caseFolder="core")
    tfsBatch.genStackingCase()
    

    
    

import os
import sys
import random
import shutil
import numpy as np
import re
import math
import json
import argparse
import copy
import pyqtree

from setups import FCpowermap
from setups import utilities


class BTreeNode:
    def __init__(self, cell_name, x, y, width, height, marker, parent=None):
        self.cell_name = cell_name
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.marker = marker
        
        self.parent = parent
        self.left = None
        self.right = None
    
    def __str__(self):
        return "X:{}, Y:{}, W:{}, H:{}".format(self.x, self.y, self.width, self.height)



class placeCell:
    def __init__(self, cell_list, region, outputFolder="./"):
        self.llx, self.lly, self.urx, self.ury = region
        self.region_width = self.urx - self.llx
        self.region_height = self.ury - self.lly
        self.outputFolder = outputFolder

        self.root = None

        self.frontX, self.frontY = 0.0, 0.0

        self.cell_list = cell_list
        
        self.leafNodes = []
        self.placed_cells = []
        self.unplaced_cells = []

        # Initialize QuadTree
        self.quadtree = pyqtree.Index(bbox=(self.llx, self.lly, self.urx, self.ury))

    def Node2BinDict(self, node):
        llx = node.x
        lly = node.y
        urx = llx + node.width
        ury = lly + node.height
        self.quadtree.insert(node, (llx, lly, urx, ury))


    def checkNodes(self, llx, lly, urx, ury):
        ### adjacent belong to intersect ###
        overlapping_nodes = self.quadtree.intersect((llx, lly, urx, ury))
        actual_overlapping_nodes = []

        for node in overlapping_nodes:
            node_llx = node.x
            node_lly = node.y
            node_urx = node_llx + node.width
            node_ury = node_lly + node.height

            # Check if the nodes actually overlap
            if not (urx <= node_llx or llx >= node_urx or ury <= node_lly or lly >= node_ury):
                actual_overlapping_nodes.append(node)
        
        #print(llx, lly, urx, ury, actual_overlapping_nodes)
        
        return actual_overlapping_nodes
    

    def getPlacedCells(self):
        placedCells = []
        for c in self.placed_cells:
            name = c.cell_name
            llx, lly = c.x, c.y
            width, height = c.width, c.height
            urx = llx + width
            ury = lly + height
            urx = float("{:.6f}".format(urx))
            ury = float("{:.6f}".format(ury))
            placedCells.append([name, llx, lly, urx, ury])
        
        return placedCells
    
    def getUnPlacedCells(self):
        unPlacedCells = []
        for c in self.unplaced_cells:
            name = c[0]
            unPlacedCells.append(name)
        
        return unPlacedCells

    def place_cells(self):
        ## cell: [cell_name, cell_width, cell_height]
        if len(self.cell_list) == 0:
            print("<INFO> Total #inputs: {}".format(len(self.cell_list)))
            print("<INFO> #Placed:{}, #Unplaced:{}".format(len(self.placed_cells), len(self.unplaced_cells)))
            print("<INFO> Unplaced:{}".format(self.unplaced_cells))
            return

        cell = self.cell_list[0]
        cellName = cell[0]
        width, height = cell[1], cell[2]
        marker = cell[3]
        if width <= self.urx and height <= self.ury:
            self.root = BTreeNode(cellName, self.llx, self.lly, width, height, marker)
            self.leafNodes.append(self.root)
            self.placed_cells.append(self.root)
            self.frontX = self.llx + width
            self.frontY = self.lly + height
        
        self.Node2BinDict(self.root)

        for _i, cell in enumerate(self.cell_list[1:]):
            cellName = cell[0]
            width, height = cell[1], cell[2]
            marker = cell[3]
            ### determine where to locate ###
            candidates = []
            for idx, leaf in enumerate(self.leafNodes):
                if not leaf.left:
                    _llx = leaf.x
                    _lly = leaf.y + leaf.height
                    _urx = _llx + width
                    _ury = _lly + height
                    _frontX = self.frontX
                    _frontY = self.frontY
                    if _urx >= self.frontX:
                        _frontX = _urx
                    if _ury >= self.frontY:
                        _frontY = _ury
                    
                    ## check #1
                    if _frontX < self.urx and _frontY < self.ury:
                        ## check cells overlap
                        checkNodeList = self.checkNodes(_llx, _lly, _urx, _ury)
                        if not checkNodeList:
                            _area = (_frontX-self.llx)*(_frontY-self.lly)
                            _area = float("{:.4f}".format(_area))
                            candidates.append([_area, idx, "left"])
                
                if not leaf.right:
                    _llx = leaf.x + leaf.width
                    _lly = leaf.y
                    _urx = _llx + width
                    _ury = _lly + height
                    _frontX = self.frontX
                    _frontY = self.frontY
                    if _urx >= self.frontX:
                        _frontX = _urx
                    if _ury >= self.frontY:
                        _frontY = _ury
                    
                    ## check #1
                    if _frontX < self.urx and _frontY < self.ury:
                        ## check cells overlap
                        checkNodeList = self.checkNodes(_llx, _lly, _urx, _ury)
                        if not checkNodeList:
                            _area = (_frontX-self.llx)*(_frontY-self.lly)
                            _area = float("{:.4f}".format(_area))
                            candidates.append([_area, idx, "right"])
                    
            candidates = sorted(candidates, key=lambda x:x[0])
            #print(candidates)
            #sys.exit(1)

            ### cell cannot be placed ###
            if len(candidates) == 0:
                self.unplaced_cells.append(cell)
                continue

            ### select the first candidate location ###
            selectID = candidates[0][1]
            selectDirection = candidates[0][2]

            node = self.leafNodes[selectID]
            if selectDirection == "left":
                llx = node.x
                lly = node.y + node.height
            elif selectDirection == "right":
                llx = node.x + node.width
                lly = node.y
            else:
                print("<ERROR> CODE_1")

            new_node = BTreeNode(cellName, llx, lly, width, height, marker, parent=node)
            
            if selectDirection == "left":
                node.left = new_node
                new_node.parent = node
                if new_node.y + new_node.height > self.frontY:
                    self.frontY = new_node.y + new_node.height
            
            elif selectDirection == "right":
                node.right = new_node
                new_node.parent = node
                if new_node.x + new_node.width > self.frontX:
                    self.frontX = new_node.x + new_node.width
            else:
                print("<ERROR> CODE_1")
            
            if node.left is not None and node.right is not None:
                del self.leafNodes[selectID]
            
            self.leafNodes.append(new_node)
            self.placed_cells.append(new_node)
            self.Node2BinDict(new_node)
        
        print("<INFO> Total #inputs: {}".format(len(self.cell_list)))
        print("<INFO> #Placed:{}, #Unplaced:{}".format(len(self.placed_cells), len(self.unplaced_cells)))
        print("<INFO> Unplaced:{}".format(self.unplaced_cells))
    
    def plotPlacement(self, saveFile="place.png"):
        import matplotlib
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle

        fig, ax = plt.subplots()

        ax.add_patch(Rectangle((self.llx, self.lly), self.urx-self.llx, self.ury-self.lly, edgecolor='black', facecolor='none'))

        # Add each rectangle to the plot
        for i, cell in enumerate(self.placed_cells):
            cell_name = "C_{}".format(i)
            cell_llx = self.placed_cells[i].x
            cell_lly = self.placed_cells[i].y
            cell_urx = cell_llx + self.placed_cells[i].width
            cell_ury = cell_lly + self.placed_cells[i].height
            cell_marker = self.placed_cells[i].marker
            if cell_marker == 1:
                ax.add_patch(Rectangle((cell_llx, cell_lly), cell_urx - cell_llx, cell_ury - cell_lly, edgecolor='blue', facecolor='lightblue'))
                ax.text(cell_llx + (cell_urx - cell_llx) / 2, cell_lly + (cell_ury - cell_lly) / 2, cell_name, ha='center', va='center')
            if cell_marker == 2:
                ax.add_patch(Rectangle((cell_llx, cell_lly), cell_urx - cell_llx, cell_ury - cell_lly, edgecolor='tan', facecolor='yellow'))
        
        plt.xlim(self.llx, self.urx)
        plt.ylim(self.lly, self.ury)
        plt.gca().set_aspect('equal', adjustable='box')

        # Save the plot to an image file
        imgPath = os.path.join(self.outputFolder, saveFile)
        plt.savefig(imgPath, bbox_inches="tight")
        plt.close(fig)

    
    def animate_placement(self, saveAniName="place_animation.gif"):
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
        import matplotlib.animation as animation
        
        fig, ax = plt.subplots()

        # Draw the placement region
        ax.add_patch(patches.Rectangle((self.llx, self.lly), self.urx-self.llx, self.ury-self.lly, edgecolor='black', facecolor='none'))

        def update(frame):
            ax.clear()
            ax.add_patch(patches.Rectangle((self.llx, self.lly), self.urx-self.llx, self.ury-self.lly, edgecolor='black', facecolor='none'))
            for i in range(frame + 1):
                if i < len(self.placed_cells):
                    cell_name = "C_{}".format(i)  #self.placed_cells[i].cell_name
                    cell_llx = self.placed_cells[i].x
                    cell_lly = self.placed_cells[i].y
                    cell_urx = cell_llx + self.placed_cells[i].width
                    cell_ury = cell_lly + self.placed_cells[i].height
                    cell_marker = self.placed_cells[i].marker
                    if cell_marker == 1:
                        ax.add_patch(patches.Rectangle((cell_llx, cell_lly), cell_urx - cell_llx, cell_ury - cell_lly, edgecolor='blue', facecolor='lightblue'))
                        ax.text(cell_llx + (cell_urx - cell_llx) / 2, cell_lly + (cell_ury - cell_lly) / 2, cell_name, ha='center', va='center')
                    if cell_marker == 2:
                        ax.add_patch(patches.Rectangle((cell_llx, cell_lly), cell_urx - cell_llx, cell_ury - cell_lly, edgecolor='tan', facecolor='yellow'))

            
            plt.xlim(self.llx, self.urx)
            plt.ylim(self.lly, self.ury)
            plt.gca().set_aspect('equal', adjustable='box')

        ani = animation.FuncAnimation(fig, update, frames=300, repeat=False)   #len(self.placed_cells)

        outFile = os.path.join(self.outputFolder, saveAniName)
        ani.save(outFile, fps=2)
        #plt.show()


def WS_ALL(WSALL, unitPD, cell_bbox):
    def calSPAN(cellUX, cellUY, cellAREA, WSXX, WSYY):
        WS_SPANX = cellUX*WSXX
        WS_SPANY = cellUY*WSYY
        overHeadArea = ((2*WSXX+1)*(2*WSYY+1)*cellAREA) - cellAREA
        return [WS_SPANX, WS_SPANY], overHeadArea
    
    WSX = WSALL["X"]
    WSY = WSALL["Y"]
    PD = WSALL["PD"]

    SITE_COL = WSALL["SITE_COL"]   ## 0.05: Intel3  0.05: 18A
    SITE_ROW = WSALL["SITE_ROW"]   ## 0.24: Intel3  0.16: 18A

    cell_XX = float("{:.3f}".format(cell_bbox[2]-cell_bbox[0]))
    cell_YY = float("{:.3f}".format(cell_bbox[3]-cell_bbox[1]))
    cell_AREA = float("{:.6f}".format(cell_XX*cell_YY))
    cellUnitX = math.ceil(cell_XX/SITE_COL)
    cellUnitY = math.ceil(cell_YY/SITE_ROW)

    overHeadArea = 0.0
    if unitPD > PD:
        WS, overHeadArea = calSPAN(cellUnitX, cellUnitY, cell_AREA, WSX, WSY)
    
    else:
        return [0, 0], [SITE_COL, SITE_ROW], cell_bbox, 0.0
    
    llx = float("{:.4f}".format(cell_bbox[0]-(WS[0]*SITE_COL)))
    urx = float("{:.4f}".format(cell_bbox[2]+(WS[0]*SITE_COL)))
    lly = float("{:.4f}".format(cell_bbox[1]-(WS[1]*SITE_ROW)))
    ury = float("{:.4f}".format(cell_bbox[3]+(WS[1]*SITE_ROW)))
    BBOX = [llx, lly, urx, ury]
    return WS, [SITE_COL, SITE_ROW], BBOX, overHeadArea


def WS_LUT_SIMPLE(WSParams, unitPD, cell_bbox):
    ### return: [WS_SPANX, WS_SPANY], [SITE_COL, SITE_ROW], NEW_bbox, overhead_area
    ### power density in W/mm^2 ###
    def calSPAN(cellUX, cellUY, cellAREA, WSXX, WSYY):
        WS_SPANX = cellUX*WSXX
        WS_SPANY = cellUY*WSYY
        overHeadArea = ((2*WSXX+1)*(2*WSYY+1)*cellAREA) - cellAREA
        return [WS_SPANX, WS_SPANY], overHeadArea

    WSLX = WSParams["LX"]
    WSLY = WSParams["LY"]
    PDLH = WSParams["PDLH"]
    PDLL = WSParams["PDLL"]

    WSMX = WSParams["MX"]
    WSMY = WSParams["MY"]
    PDMH = WSParams["PDMH"]
    PDML = WSParams["PDML"]
    
    WSSX = WSParams["SX"]
    WSSY = WSParams["SY"]
    PDSH = WSParams["PDSH"]
    PDSL = WSParams["PDSL"]
    SITE_COL = WSParams["SITE_COL"]   ## 0.05: Intel3  0.05: 18A
    SITE_ROW = WSParams["SITE_ROW"]   ## 0.24: Intel3  0.16: 18A

    cell_XX = float("{:.3f}".format(cell_bbox[2]-cell_bbox[0]))
    cell_YY = float("{:.3f}".format(cell_bbox[3]-cell_bbox[1]))
    cell_AREA = float("{:.6f}".format(cell_XX*cell_YY))
    cellUnitX = math.ceil(cell_XX/SITE_COL)
    cellUnitY = math.ceil(cell_YY/SITE_ROW)
    #print("** PD:{}, cell:{}, XX:{}, YY:{}, X:{}, Y:{}".format(unitPD, cell_bbox, cell_XX, cell_YY, cellUnitX, cellUnitY))
    
    overHeadArea = 0.0
    if unitPD < PDLH and unitPD >= PDLL:
        WS, overHeadArea = calSPAN(cellUnitX, cellUnitY, cell_AREA, WSLX, WSLY)
    
    elif unitPD < PDMH and unitPD >= PDML:
        WS, overHeadArea = calSPAN(cellUnitX, cellUnitY, cell_AREA, WSMX, WSMY)
    
    elif unitPD < PDSH and unitPD >= PDSL:
        WS, overHeadArea = calSPAN(cellUnitX, cellUnitY, cell_AREA, WSSX, WSSY)
    
    else:
        return [0, 0], [SITE_COL, SITE_ROW], cell_bbox, 0.0
    
    llx = float("{:.4f}".format(cell_bbox[0]-(WS[0]*SITE_COL)))
    urx = float("{:.4f}".format(cell_bbox[2]+(WS[0]*SITE_COL)))
    lly = float("{:.4f}".format(cell_bbox[1]-(WS[1]*SITE_ROW)))
    ury = float("{:.4f}".format(cell_bbox[3]+(WS[1]*SITE_ROW)))
    BBOX = [llx, lly, urx, ury]
    return WS, [SITE_COL, SITE_ROW], BBOX, overHeadArea


class UPTRPlace:
    def __init__(self, 
                 confJSON,
                 outputFolder="./CASEs/UPTR_opt"):
        self.version = "v010a"
        self.outputFolder = outputFolder

        self.confJSON = confJSON
        self.setupDict = {}

        self.powerNetlistPath = None
        self.FCPowerView = None


        self.WSRULES = {}   ## White space
        self.WSAPR_COMMAND = ""
        self.WSFUNC = None  ## like founction pointer
    
    def __F2Sprecision(self, fval, prec=6):
        precStr= "{:."+str(prec)+"f}"
        return precStr.format(fval)
    
    def setupInputConf(self):
        if not os.path.isfile(self.confJSON):
            print("[ERROR] {} path not found".format(self.confJSON))
            return
        
        print("{} Parsing...".format(self.confJSON))
        with open(self.confJSON, "r") as fid:
            self.setupDict = json.load(fid)
        
        if "BGPDTABLE" in self.setupDict.keys():
            pass
        
        if "WSRULES" in self.setupDict.keys():
            refDict = self.setupDict["WSRULES"]
            self.WSRULES.setdefault("SITE_COL", refDict["SITE_COL"])
            self.WSRULES.setdefault("SITE_ROW", refDict["SITE_ROW"])
            if refDict["RULES"]["CLASS"] == "SIMPLE":
                self.WSRULES["LX"] = refDict["RULES"]["WS"]["L"]["XX"]
                self.WSRULES["LY"] = refDict["RULES"]["WS"]["L"]["YY"]
                self.WSRULES["PDLH"] = refDict["RULES"]["WS"]["L"]["PD"][0]
                self.WSRULES["PDLL"] = refDict["RULES"]["WS"]["L"]["PD"][1]
                self.WSRULES["MX"] = refDict["RULES"]["WS"]["M"]["XX"]
                self.WSRULES["MY"] = refDict["RULES"]["WS"]["M"]["YY"]
                self.WSRULES["PDMH"] = refDict["RULES"]["WS"]["M"]["PD"][0]
                self.WSRULES["PDML"] = refDict["RULES"]["WS"]["M"]["PD"][1]
                self.WSRULES["SX"] = refDict["RULES"]["WS"]["S"]["XX"]
                self.WSRULES["SY"] = refDict["RULES"]["WS"]["S"]["YY"]
                self.WSRULES["PDSH"] = refDict["RULES"]["WS"]["S"]["PD"][0]
                self.WSRULES["PDSL"] = refDict["RULES"]["WS"]["S"]["PD"][1]
                
                self.WSFUNC = WS_LUT_SIMPLE
        else:
            print("[ERROR] Cannot load White Space Rules")
            return
        
        if "APR_COMMAND" in self.setupDict.keys():
            self.WSAPR_COMMAND = self.setupDict["APR_COMMAND"]
    
    def loadPowerNetlist(self, powerNetlistPath, pType="CSV", designArea=[]):
        self.powerNetlistPath = powerNetlistPath
        self.FCPowerView = FCpowermap.FCPowerView(self.powerNetlistPath, fType="CSV", 
                                      DesignArea=designArea, outputFolder=self.outputFolder)

    def simpleWSInsertion(self, MINPD=20):
        def WSNetlistOut(WSList, outName, outputFolder):
            padOutStr = []
            for wscell in WSList:
                inst = wscell[0]
                WSX, WSY = wscell[1]
                _str = self.WSAPR_COMMAND.format(inst, WSX, WSX, WSY, WSY)
                padOutStr.append(_str)
        
            outPath = os.path.join(outputFolder, outName)
            with open(outPath, "w") as fid:
                fid.write("\n".join(padOutStr))

        
        if self.FCPowerView is None:
            print("<WARNING> FCPowerView not initialize")
            return 
        
        cellReport = self.FCPowerView.cellReportSummary(siteRow=self.WSRULES["SITE_ROW"], 
                                           siteCol=self.WSRULES["SITE_COL"])
        
        cellDB = self.FCPowerView.dbDict

        WSSmall, WSMedium, WSMax, WSbyRule = [], [], [], []
        for inst in cellDB.keys():
            instName = inst
            pwr = cellDB[inst]["PWR"]
            pwr_density = cellDB[inst]["PWR_density"]*1000  ### from mW/um^2 to W/mm^2 -> 1 mW/um^2 = 1*1000 W/m^2
            
            cell_bbox = [cellDB[inst]["llx"], cellDB[inst]["lly"], cellDB[inst]["urx"], cellDB[inst]["ury"]]

            ### Type1: all small size ###
            SMALL = {"X": self.WSRULES["SX"], "Y": self.WSRULES["SY"], "PD": MINPD,
                     "SITE_COL": self.WSRULES["SITE_COL"], "SITE_ROW": self.WSRULES["SITE_ROW"]}
            WS, SITE_RULE, BBOX, overHeadArea = WS_ALL(SMALL, pwr_density, cell_bbox)
            
            if WS[0] > 0 and WS[1] > 0:
                WSSmall.append([instName, WS])
                
            ### Type2: all medium size ###
            MEDIUM = {"X": self.WSRULES["MX"], "Y": self.WSRULES["MY"], "PD": MINPD, 
                      "SITE_COL": self.WSRULES["SITE_COL"], "SITE_ROW": self.WSRULES["SITE_ROW"]}
            WS, SITE_RULE, BBOX, overHeadArea = WS_ALL(MEDIUM, pwr_density, cell_bbox)
            if WS[0] > 0 and WS[1] > 0:
                WSMedium.append([instName, WS])

            ### Type3: all large size ###
            LARGE = {"X": self.WSRULES["LX"], "Y": self.WSRULES["LY"], "PD": MINPD,
                     "SITE_COL": self.WSRULES["SITE_COL"], "SITE_ROW": self.WSRULES["SITE_ROW"]}
            WS, SITE_RULE, BBOX, overHeadArea = WS_ALL(LARGE, pwr_density, cell_bbox)
            if WS[0] > 0 and WS[1] > 0:
                WSMax.append([instName, WS])
            
            ### Type4: By hard rules ###
            WS, SITE_RULE, BBOX, overHeadArea = WS_LUT_SIMPLE(self.WSRULES, pwr_density, cell_bbox)
            if WS[0] > 0 and WS[1] > 0:
                WSbyRule.append([instName, WS])
        
        WSNetlistOut(WSSmall, outName="allSWS.tcl", outputFolder=self.outputFolder)
        WSNetlistOut(WSMedium, outName="allMWS.tcl", outputFolder=self.outputFolder)
        WSNetlistOut(WSMax, outName="allLWS.tcl", outputFolder=self.outputFolder)
        WSNetlistOut(WSbyRule, outName="WSbyRules.tcl", outputFolder=self.outputFolder)



class PowerThermalOpt_v03:
    def __init__(self, confJSON, powerNetlistPath, RMcsvPath, coarseR, fineR, outputFolder="./PTt"):
        self.version = "v02"
        self.outputFolder = outputFolder

        self.confJSON = confJSON
        self.RMcsvPath = RMcsvPath                  ## R-Matrix
        self.powerNetlistPath = powerNetlistPath
        self.setupDict = {}

        ### save the original input cells ###
        self.orgCellNetList = {}
        self.orgCellSeq = []

        ### Resolution ###
        self.coarseR = coarseR
        self.fineR = fineR

        self.designArea = []
        self.coarseTileFC = None
        self.RMatrix = None

        self.coarseDict = {}

        ### run variable in FineAnalysis ###
        self.fineDict = {}

        ### output variables ###
        self.cellsProcessedDict = {}


        ### index counter ###
        self.MaxCoarseTiles, self.MaxFineTiles = 0, 0
        
        ### variables ###
        self.inputCellsArea = 0.0
        self.totalCells = 0
        self.totalInputPwr = 0.0

        self.fineXX, self.fineYY = None, None

        self.areaOverHead = 0.0


        ### RULES ###
        self.MINPD = 20
        self.AREAMARGIN = 1.1
        self.WS_UTILIZATION_RATIO = 0.85
        self.BGDICT = {}    ## LookUp Table
        self.WSRULES = {}   ## White space
        self.WSFUNC = None  ## like founction pointer

        ### Hard Macros ###
        self.FIXMACROS = {}
        self.MACROLIST = []
        self.BLOCKTILES = []


        ## pre-cal parameters ##
        self.coarseArea = self.coarseR*self.coarseR
        self.fineArea = self.fineR*self.fineR

    
    def __F2Sprecision(self, fval, prec=6):
        precStr= "{:."+str(prec)+"f}"
        return precStr.format(fval)
    
    def __TSRV(self, xx, yy, sizeX, sizeY, fineTileDict):
        if xx < 0:
            return 0.0
        if yy < 0:
            return 0.0
        if xx > len(sizeX)-1:
            return 0.0
        if yy > len(sizeY)-1:
            return 0.0

        idx = "{}_{}".format(str(xx), str(yy))
        pd = fineTileDict[idx]["_pd"]
        bgpd = fineTileDict[idx]["_bgpd"]
        tsrv = self.__UPTR_LUT(pd, bgpd, refType="SV")
        return tsrv
    
    def __calTileTSRV(self, tid, sizeX, sizeY, fineTileDict):
        xx = int(str(tid).split("_")[0])
        yy = int(str(tid).split("_")[1])

        tileTSRV = []
        for _x in [-1, 1]:
            for _y in [-1, 1]:
                tileTSRV.append(self.__TSRV(xx+_x, yy+_y, sizeX, sizeY, fineTileDict))

        return tileTSRV
    
    def __UPTR_LUT(self, unitPD, BGPD, refType="PV"):
        ## first order interpolate unit PD ##
        BGPDunitPD = []   ## interpolate ref value at existed BG_PD at unitPD ##
        for k, bg in enumerate(self.BGDICT["BG"]):
            _key = str(k+1)
            xp = self.BGDICT["PD"]
            fp = self.BGDICT["BG_PD"][_key][refType]
            val = np.interp(unitPD, xp, fp)
            val = float("{:.3f}".format(val))
            BGPDunitPD.append(val)

        #print(BGPDunitPD)
        xp = self.BGDICT["BG"]
        fp = BGPDunitPD
        val = np.interp(BGPD, xp, fp)
        val = float("{:.3f}".format(val))
        #print(val)
        return val
    
    def setupInputConf(self):
        if not os.path.isfile(self.confJSON):
            print("[ERROR] {} path not found".format(self.confJSON))
            return
        
        print("{} Parsing...".format(self.confJSON))
        with open(self.confJSON, "r") as fid:
            self.setupDict = json.load(fid)
        
        if "BGPDTABLE" in self.setupDict.keys():
            _path = self.setupDict["BGPDTABLE"]["PATH"]
            _idx = self.setupDict["BGPDTABLE"]["INDEX"]
            if not os.path.isfile(_path):
                print("[ERROR] BGPDTABLE path:{}, not found".format(_path))
                return
            
            with open(_path, "r") as fid:
                self.BGDICT = json.load(fid)[_idx]
            
        else:
            print("[ERROR] Cannot load BGPDTABLE")
            return
        
        if "WSRULES" in self.setupDict.keys():
            refDict = self.setupDict["WSRULES"]
            self.WSRULES.setdefault("SITE_COL", refDict["SITE_COL"])
            self.WSRULES.setdefault("SITE_ROW", refDict["SITE_ROW"])
            if refDict["RULES"]["CLASS"] == "SIMPLE":
                self.WSRULES["LX"] = refDict["RULES"]["WS"]["L"]["XX"]
                self.WSRULES["LY"] = refDict["RULES"]["WS"]["L"]["YY"]
                self.WSRULES["PDLH"] = refDict["RULES"]["WS"]["L"]["PD"][0]
                self.WSRULES["PDLL"] = refDict["RULES"]["WS"]["L"]["PD"][1]
                self.WSRULES["MX"] = refDict["RULES"]["WS"]["M"]["XX"]
                self.WSRULES["MY"] = refDict["RULES"]["WS"]["M"]["YY"]
                self.WSRULES["PDMH"] = refDict["RULES"]["WS"]["M"]["PD"][0]
                self.WSRULES["PDML"] = refDict["RULES"]["WS"]["M"]["PD"][1]
                self.WSRULES["SX"] = refDict["RULES"]["WS"]["S"]["XX"]
                self.WSRULES["SY"] = refDict["RULES"]["WS"]["S"]["YY"]
                self.WSRULES["PDSH"] = refDict["RULES"]["WS"]["S"]["PD"][0]
                self.WSRULES["PDSL"] = refDict["RULES"]["WS"]["S"]["PD"][1]
                
                self.WSFUNC = WS_LUT_SIMPLE
        else:
            print("[ERROR] Cannot load White Space Rules")
            return
    
    
    def initSetup(self, runRoot, designArea):
        ### define designArea, generate coareTilePowerMap, generate RMatrix ###
        self.designArea = designArea
        self.coarseTileFC = FCpowermap.FCPowerView(self.powerNetlistPath, "CSV", outputFolder=self.outputFolder, DesignArea=self.designArea)
        self.coarseTileFC.translate2TilePwr(resolution=self.coarseR)

        TileX = len(self.coarseTileFC.getTileXStep(resolution=self.coarseR))
        TileY = len(self.coarseTileFC.getTileYStep(resolution=self.coarseR))
        self.RMatrix = tPlacement.thermalRMatrix(TileX, TileY, outputFolder=self.outputFolder)
        self.RMatrix.loadRMatrixCSV(self.RMcsvPath)

        ### load cell netlist ###
        with open(self.powerNetlistPath, "r") as fid:
            for i, ll in enumerate(fid):
                if i == 0:  ## header ##
                    continue

                ll = ll.split("\n")[0]
                lls = ll.split(",")
                instName = lls[0]
                llx, lly, urx, ury = lls[2:6]
                llx = float(llx)
                lly = float(lly)
                urx = float(urx)
                ury = float(ury)
                pwr = float(lls[6])
                self.inputCellsArea += (urx-llx)*(ury-lly)

                self.orgCellNetList.setdefault(instName, ll)
                self.orgCellSeq.append(instName)
                self.totalCells += 1
                self.totalInputPwr += float("{:.8f}".format(pwr))
        
        self.inputCellsArea = float(self.__F2Sprecision(self.inputCellsArea, prec=4))

        self.totalInputPwr = float("{:.8f}".format(self.totalInputPwr))
        print("<INFO> Total #Cells: {}, Total Power: {} mW".format(self.totalCells, self.totalInputPwr))

        ### load hard macros ###
        for c in self.FIXMACROS.keys():
            self.MACROLIST.append(c)


    ### evaluate Coarse Tile temperature distribution ###
    def calTbyCoarseRMatrix(self, isfileOut=True, GtThermalProfilePath="",
                           addPowers=[], isAddPowers=False):
        ### TProfile format: {"X_Y": temperature}, X: start from 0, Y: start from 0
        if isfileOut:
            outPVectorName = "PowerVector_{}um.txt".format(str(self.coarseR))
            self.RMatrix.inputTilePower(self.coarseTileFC, resolution=self.coarseR, outPVectorName=outPVectorName, \
                                        addPowers=addPowers, isAddPowers=isAddPowers)

            TProfileName = "TProfile_{}um.txt".format(str(self.coarseR))
            TProfile = self.RMatrix.estiTProfile(TProfileName=TProfileName)
            self.RMatrix.plot(resolutionX=self.coarseR, resolutionY=self.coarseR, TProfile=TProfile, saveImg="RMatrixTMap.png")

            if os.path.isfile(GtThermalProfilePath):
                GtTProfile = self.RMatrix.loadResultTProfile(TProfile=GtThermalProfilePath)
                self.RMatrix.plot(resolutionX=self.coarseR, resolutionY=self.coarseR, TProfile=GtTProfile, saveImg="GtTMap.png")
        
        else:
            self.RMatrix.inputTilePower(self.coarseTileFC, resolution=self.coarseR, isfileOut=False, \
                                        addPowers=addPowers, isAddPowers=isAddPowers)
            TProfile = self.RMatrix.estiTProfile(isTProfileOut=False)
        
        return TProfile
    
    ### evaluate Coarse Tile stress distribution ###
    def evalSbyCoarseRMatrix(self):
        pass



    def CoarseAnalysis(self, TProfile, steps=0, isCoarseTPimgOut=True):
        def initCoarse(coarseDict, TProfile):
            for coor in TProfile.keys():
                ### T: temperature, S: stress/strain 
                coarseDict.setdefault(coor, {"T":TProfile[coor], "isFIXED":False, "S":None})
        
        def costFunction(tt, ss):
            if ss is None:
                return tt
            else:
                cost = tt+ss
                return cost
        
        if steps == 0:
            initCoarse(self.coarseDict, TProfile)
            self.MaxCoarseTiles = len(self.coarseDict.keys())
        
        if isCoarseTPimgOut:
            CimgName = "CTilePwr_{}um.png".format(str(self.coarseR))
            self.coarseTileFC.plot(ptype=["TILE", self.coarseR], saveImg=CimgName)

        ### Coarse Tile cost function ###
        ### select the coarse tile ###
        maxId, maxCost = -1, -10000
        for i in self.coarseDict.keys():
            if self.coarseDict[i]["isFIXED"]:
                continue
            
            _cost = costFunction(self.coarseDict[i]["T"], self.coarseDict[i]["S"])
            if _cost > maxCost:
                maxId = i
                maxCost = _cost

        #print(self.coarseDict)
        #print(maxId, maxCost)
        #maxTid = "1_2"

        ### Out cells in this coarse mesh tile ###
        xid = maxId.split("_")[0]
        yid = maxId.split("_")[1]
        CoarseCellsListName = "Coarse_{}_{}.csv".format(str(steps), str(maxId))
        CoarseCellsPath, localArea = self.coarseTileFC.getTilePowerCells(resolution=self.coarseR, xid=xid, yid=yid, 
                                                                         macroList=self.MACROLIST, removeMacros=True,
                                                                         outputListName=CoarseCellsListName)
        #print(CoarseCellsPath, localArea)
        return localArea, CoarseCellsPath, maxId, maxCost
    

    def isFixRegion(self, region):
        llx, lly, urx, ury = region[:]
        isOverlap = False
        for macro in self.FIXMACROS.keys():
            _llx, _lly, _urx, _ury = self.FIXMACROS[macro][1:5]

            if (llx > _urx) or (urx < _llx):
                continue
            if (lly > _ury) or (ury < _lly):
                continue
            
            isOverlap = True
            break
        
        if isOverlap:
            return True
        
        return False
    
    def determine_subregion_position_and_distance(self, whole_region, sub_region):
        w_llx, w_lly, w_urx, w_ury = whole_region
        s_llx, s_lly, s_urx, s_ury = sub_region

        ### normalize ###
        w_llx = float("{:.4f}".format(w_llx))
        w_lly = float("{:.4f}".format(w_lly))
        w_urx = float("{:.4f}".format(w_urx))
        w_ury = float("{:.4f}".format(w_ury))
        s_llx = float("{:.4f}".format(s_llx))
        s_lly = float("{:.4f}".format(s_lly))
        s_urx = float("{:.4f}".format(s_urx))
        s_ury = float("{:.4f}".format(s_ury))

        ## Initialize to check position
        at_boundary = False
        at_corner = False
        position = []

        ## check if the sub-region is at the boundary
        if s_llx == w_llx:
            at_boundary = True
            position.append("left")
        if s_urx == w_urx:
            at_boundary = True
            position.append("right")
        if s_lly == w_lly:
            at_boundary = True
            position.append("bottom")
        if s_ury == w_ury:
            at_boundary = True
            position.append("top")
        
        ## check if the sub-region is at the corner
        if s_llx == w_llx and s_lly == w_lly:
            at_corner = True
            position = ["bottom-left"]
        if s_llx == w_llx and s_ury == w_ury:
            at_corner = True
            position = ["top-left"]
        if s_urx == w_urx and s_lly == w_lly:
            at_corner = True
            position = ["bottom-right"]
        if s_urx == w_urx and s_ury == w_ury:
            at_corner = True
            position = ["top-right"]
        
        ## calculate distances to boundaries
        dis_left = s_llx - w_llx
        dis_right = w_urx - s_urx
        dis_bottom = s_lly - w_lly
        dis_top = w_ury - s_ury

        ## distances to corner
        dis_bottom_left = ((s_llx-w_llx)**2 + (s_lly-w_lly)**2)**0.5
        dis_top_left = ((s_llx-w_llx)**2 + (s_ury-w_ury)**2)**0.5
        dis_bottom_right = ((s_urx-w_urx)**2 + (s_lly-w_lly)**2)**0.5
        dis_top_right = ((s_urx-w_urx)**2 + (s_ury-w_ury)**2)**0.5

        closest_boundary_dist = min(dis_left, dis_right, dis_bottom, dis_top)
        closest_corner_dist = min(dis_bottom_left, dis_top_left, dis_bottom_right, dis_top_right)

        if closest_boundary_dist < closest_corner_dist:
            if closest_boundary_dist == dis_left:
                closest_position = "left_boundary"
            elif closest_boundary_dist == dis_right:
                closest_position = "right_boundary"
            elif closest_boundary_dist == dis_bottom:
                closest_position = "bottom_boundary"
            else:
                closest_position = "top_boundary"
        else:
            if closest_corner_dist == dis_bottom_left:
                closest_position = "bottomLeft_corner"
            elif closest_corner_dist == dis_top_left:
                closest_position = "topLeft_corner"
            elif closest_corner_dist == dis_bottom_right:
                closest_position = "bottomRight_corner"
            else:
                closest_position = "topRight_corner"
        
        return position, closest_position
    

    def __initFineCostFun(self, designSpace, refFineDict, avgCoarseTilePD):
        self.MaxFineTiles = 0
        self.fineDict = {}
        self.BLOCKTILES = []
        ### calculate each tile cost ###
        tileArea = self.fineR*self.fineR
        for i, k in enumerate(refFineDict.keys()):
            #print(k)
            self.fineDict.setdefault(k, refFineDict[k])

            if self.isFixRegion(region=[refFineDict[k]["llx"], refFineDict[k]["lly"], refFineDict[k]["urx"], refFineDict[k]["ury"]]):
                self.fineDict[k]["isFIXED"] = True
                self.BLOCKTILES.append(k)
            else:
                self.fineDict[k]["isFIXED"] = False
                self.MaxFineTiles += 1
            
            pwr = self.fineDict[k]["PWR"]
            pd = self.__F2Sprecision((pwr/self.fineArea)*1000.0, prec=4)

            ### to do: need to refine the bgpd ###
            bgpd = self.__F2Sprecision(avgCoarseTilePD*0.8, prec=4)
            ######################################

            self.fineDict[k]["_bgpd"] = bgpd
            self.fineDict[k]["_pd"] = pd

            tprv = self.__UPTR_LUT(pd, bgpd, refType="PV")
            self.fineDict[k]["_tprv"] = [tprv]

            ### cal. how far from geometry boundary ###
            _xx = designSpace[0]+(self.fineR*int(k.split("_")[0]))
            _yy = designSpace[1]+(self.fineR*int(k.split("_")[1]))
            XL = _xx - self.designArea[0]
            YD = _yy - self.designArea[1]
            XR = self.designArea[2]-_xx
            YU = self.designArea[3]-_yy
            geo_boundary = abs(XR-XL) + abs(YU-YD)
            self.fineDict[k]["_geoBoundary"] = geo_boundary

            ### cal. area utilization ###
            if len(self.fineDict[k]["CELLS"]) == 0:
                self.fineDict[k]["_areaUtilization"] = 0.0
            else:
                totalCellsinTileArea = 0.0
                ## cell: [i, ratio, pwr, llx, lly, urx, ury, area, pd]
                for c in self.fineDict[k]["CELLS"]:
                    _ratio = c[1]
                    _area = c[7]
                    _inTileArea = float(self.__F2Sprecision(_area*_ratio, 8))
                    totalCellsinTileArea += _inTileArea
                
                areaUtilization = float(self.__F2Sprecision(totalCellsinTileArea/tileArea, 5))
                self.fineDict[k]["_areaUtilization"] = areaUtilization
            #print(self.fineDict[k])
        
        for i, k in enumerate(refFineDict.keys()):
            tileTSRV = self.__calTileTSRV(k, self.fineXX, self.fineYY, self.fineDict)
            self.fineDict[k]["_tsrv"] = tileTSRV
            #self.fineDict[k]["_temperature"] = sum(self.fineDict[k]["_tprv"]) + sum(self.fineDict[k]["_tsrv"])
            self.fineDict[k]["_temperature"] = sum(self.fineDict[k]["_tprv"])
        
        ### check ###
        #for i, k in enumerate(self.fineDict.keys()):
        #    print("{}\n{}".format(k, self.fineDict[k]))
        
        #exit(1)
            
    
    def FineAnalysis(self, localArea=None, coarseCellsPath=None, Fsteps=0, Csteps=0, \
                     isFineTPimgOut=True, isPlotWSCells=True):

        ### with initial localArea, coarseCellsPath & coarseTid cannot be None ###
        if localArea is None or coarseCellsPath is None: 
            print("<ERROR> localArea, coarseCellsPath need be provided in the first fine analysis")
            return {}, [], []
        
        designArea = [math.floor(localArea[0]), math.floor(localArea[1]), math.ceil(localArea[2]), math.ceil(localArea[3])]
            
        self.fineFixCount = 0
        self.MaxFineTiles = 0
        self.fineDict = {}
            
        FinePowerMap = FCpowermap.FCPowerView(coarseCellsPath, "CSV", outputFolder=self.outputFolder, DesignArea=designArea)
        FinePowerMap.translate2TilePwr(resolution=self.fineR)

        totalLocalPower = FinePowerMap.tileDictParams[self.fineR]["TotalPWR"]  ## in mW
        totalLocalPower = float(self.__F2Sprecision(totalLocalPower, prec=5))
        avgCoarseTilePD = float(self.__F2Sprecision((totalLocalPower/self.coarseArea)*1000.0, prec=4))
        #print("Total Local Power: {}, Power Density: {}".format(totalLocalPower, avgCoarseTilePD))
        
        fineData = FinePowerMap.tileDict[self.fineR]
        self.fineXX = FinePowerMap.getTileXStep(self.fineR)
        self.fineYY = FinePowerMap.getTileYStep(self.fineR)

        if len(fineData.keys()) == 0:
            return {}, [], designArea

        ### Initial self.fineDict ###
        self.__initFineCostFun(designSpace=designArea, refFineDict=fineData, avgCoarseTilePD=avgCoarseTilePD)

        ### output images ###
        if isFineTPimgOut:
            #print("==== {} ====".format(designArea))
            fineTileOutStr = ["Cell_Name,Cell_Type,lx,ly,ux,uy,power"]
            for i, k in enumerate(self.fineDict.keys()):
                tileInst = "F_{}".format(k)
                tile = "{},{},{},{},{},{},{}".format(tileInst,"FINE",self.fineDict[k]["llx"],self.fineDict[k]["lly"],\
                                                     self.fineDict[k]["urx"],self.fineDict[k]["ury"],self.fineDict[k]["PWR"])
                fineTileOutStr.append(tile)
            
            outFineTilePath = os.path.join(self.outputFolder, "_FineTile_{}-{}.csv".format(str(Csteps), str(Fsteps)))
            with open(outFineTilePath, "w") as fid:
                fid.write("\n".join(fineTileOutStr))
            
            print("==== Fine Tile CSV:{} ====".format(outFineTilePath))
            _FinePowerMap = FCpowermap.FCPowerView(outFineTilePath, "CSV", outputFolder=self.outputFolder, DesignArea=designArea)
            _FinePowerMap.translate2TilePwr(resolution=self.fineR)
            
            _FimgName = "_FTilePwr_{}-{}_{}um.png".format(str(Csteps), str(Fsteps), str(self.fineR))
            _FinePowerMap.plot(ptype=["TILE", self.fineR], blocked=self.BLOCKTILES, saveImg=_FimgName)
            #print("+++++++++", self.fineDict["44_12"])
        
        ### cost normalization ###
        areaWeight, geoWeight, tempWeight = 1, 1, 5
        
        GeoBoundary, AreaUtilization, Temperature = [], [], []
        for i, k in enumerate(self.fineDict.keys()):
            GeoBoundary.append(self.fineDict[k]["_geoBoundary"])
            AreaUtilization.append(self.fineDict[k]["_areaUtilization"])
            Temperature.append(self.fineDict[k]["_temperature"])
        
        minGB, maxGB = min(GeoBoundary), max(GeoBoundary)
        minAU, maxAU = min(AreaUtilization), max(AreaUtilization)
        minTT, maxTT = min(Temperature), max(Temperature)

        ### prepare all cells in this Fine Tile ###
        cellDict = {}
        costList = []
        _cellList = []
        cellArea = 0.0
        for i, k in enumerate(self.fineDict.keys()):
            try:
                _areaUtilization = (self.fineDict[k]["_areaUtilization"]-minAU)/(maxAU-minAU)
            except:
                _areaUtilization = 1
            
            try:
                _geoBoundary = (self.fineDict[k]["_geoBoundary"]-minGB)/(maxGB-minGB)
            except:
                _geoBoundary = 1
            
            try:
                _temperature = (self.fineDict[k]["_temperature"]-minTT)/(maxTT-minTT)
            except:
                _temperature = 1
            
            
            _cost = (areaWeight*_areaUtilization) + \
                    (geoWeight*_geoBoundary) + \
                    (tempWeight*_temperature)
            
            
            self.fineDict[k]["cost"] = _cost
            
            for _c in self.fineDict[k]["CELLS"]:
                if (_c[0] in cellDict) or (_c[0] in self.cellsProcessedDict):
                    ### cell has been processed ###
                    pass
                else:
                    _cellList.append([_c[0], _c[-1]])
                    cellDict.setdefault(_c[0], {"llx":_c[3], "lly":_c[4], "urx":_c[5], "ury":_c[6], \
                                                 "PWR":_c[2], "PD":_c[-1]})
                    cellArea += _c[7]
            
            if self.fineDict[k]["isFIXED"]:
                pass
            else:
                costList.append([_cost, k])

        costList = sorted(costList, key=lambda x:x[0], reverse=True)  ## from largest to smallest
        _cellList = sorted(_cellList, key=lambda x:x[-1], reverse=True)
        #print(_cellList)
        #maxCostFineKey = costList[0][1]
        #print(maxCostFineKey)
        
        cellArea = float("{:.6f}".format(cellArea))
        fineTotalArea = float("{:.6f}".format((designArea[2]-designArea[0])*(designArea[3]-designArea[1])))
        utilization = float("{:.3f}".format(cellArea/fineTotalArea))
        print("<INFO> Fine_Tile_Area:{}, #Fine_Tiles:{}, Cells_Area:{}, #Cells:{}, Utilization:{}".format(fineTotalArea, len(self.fineDict.keys()), \
                                                                cellArea, len(cellDict.keys()), utilization))

        cellsWithWS = []
        withWSArea = cellArea
        withWSUtilization = float("{:.3f}".format(withWSArea/fineTotalArea))
        for _c in _cellList:
            instName = _c[0]
            pd = _c[-1]

            ### LookUp Table White Space ###
            ### self.WS_UTILIZATION_RATIO = 0.85 ###
            if pd >= self.MINPD and withWSUtilization <= self.WS_UTILIZATION_RATIO:
                cell_bbox = [cellDict[instName]["llx"], cellDict[instName]["lly"], cellDict[instName]["urx"], cellDict[instName]["ury"]]
                WS, SITE_RULE, BBOX, overHeadArea = self.WSFUNC(self.WSRULES, pd, cell_bbox)   ## return [WS_spanX, WS_spanY]
                withWSArea += overHeadArea
                withWSUtilization = float("{:.3f}".format(withWSArea/fineTotalArea))
                cellsWithWS.append([instName, pd, WS, SITE_RULE, BBOX])

        print("<INFO> with WS consideration => updated utilization:{}".format(withWSUtilization))
        #print(cellsWithWS)

        if isPlotWSCells:
            WScells = []
            plotWSCells = []
            for c in cellsWithWS:
                instName = c[0]
                cllx = cellDict[instName]["llx"]
                clly = cellDict[instName]["lly"]
                curx = cellDict[instName]["urx"]
                cury = cellDict[instName]["ury"]
                WSbbox = c[-1]
                plotWSCells.append([[cllx, clly, curx, cury], WSbbox])
                WScells.append(WSbbox)
            
            WSplotName = "WSplot_{}_{}.png".format(str(Csteps), str(self.fineR))
            print("==== WS plot:{} ====".format(WSplotName))
            self.plotWSCells(cellList=plotWSCells, region=designArea, saveImg=WSplotName)
        
        return cellDict, cellsWithWS, designArea
    

    def skipCellPlacement(self, cellDict, cellsWithWS, Csteps):
        updatedCellDict = {}
        WScellDict = {}
        ## cellsWithWS items => c:[instName, pd, WS, SITE_RULE, BBOX]
        for c in cellsWithWS:
            bbox = c[-1]
            pd = c[1]
            WS = c[2]
            SITE_RULE = c[3]
            area = float("{:.4f}".format((bbox[2]-bbox[0])*(bbox[3]-bbox[1])))
            WScellDict.setdefault(c[0], {"llx":bbox[0], "lly":bbox[1], "urx":bbox[2], "ury":bbox[3], \
                                         "area":area, "pd":pd, "WS":WS, "SITE_RULE":SITE_RULE})

        for c in cellDict.keys():
            org_llx, org_lly, org_urx, org_ury = cellDict[c]["llx"], cellDict[c]["lly"], cellDict[c]["urx"], cellDict[c]["ury"]
            orgPwr = cellDict[c]["PWR"]
            orgPD = cellDict[c]["PD"]
            
            if c in WScellDict:
                WS = WScellDict[c]["WS"]
                SITE_RULE = WScellDict[c]["SITE_RULE"]
                ws_llx = org_llx - (WS[0]*SITE_RULE[0])
                ws_lly = org_lly - (WS[1]*SITE_RULE[1])
                ws_urx = org_urx + (WS[0]*SITE_RULE[0])
                ws_ury = org_ury + (WS[1]*SITE_RULE[1])
                ws_llx = float("{:.4f}".format(ws_llx))
                ws_lly = float("{:.4f}".format(ws_lly))
                ws_urx = float("{:.4f}".format(ws_urx))
                ws_ury = float("{:.4f}".format(ws_ury))
                    
                updatedCellDict.setdefault(c, {"org":[org_llx, org_lly, org_urx, org_ury, orgPwr, orgPD], \
                                               "update":[ws_llx, ws_lly, ws_urx, ws_ury, orgPwr, orgPD], \
                                               "withWS":[WS, SITE_RULE]})
            else:
                updatedCellDict.setdefault(c, {"org":[org_llx, org_lly, org_urx, org_ury, orgPwr, orgPD], \
                                               "update":[org_llx, org_lly, org_urx, org_ury, orgPwr, orgPD], \
                                               "withWS":None})
        
        ### Directly to self.cellsProcessedDict ###
        for c in updatedCellDict.keys():
            if c in self.cellsProcessedDict:
                pass
            else:
                self.cellsProcessedDict.setdefault(c, updatedCellDict[c])
        
        print("<INFO> SKIP UpdateALL>> #orgCells:{}, #UpdatedCells:{}".format(len(cellDict.keys()), len(updatedCellDict.keys())))

    
    def WScellsGrouping(self, cellDict, cellsWithWS, designArea, Csteps, isPlot=True):
        ### grouping cells with WS ###
        def is_overlapping(cell1, cell2):
            # Check if two cells overlap
            return not (cell1[2] <= cell2[0] or cell1[0] >= cell2[2] or cell1[3] <= cell2[1] or cell1[1] >= cell2[3])

        def group_cells(cells):
            groups = []
            groupsRect = []
    
            for cell in cells:
                added = False
                for group in groups:
                    if any(is_overlapping(cell, member) for member in group):
                        group.append(cell)
                        added = True
                        break
                if not added:
                    groups.append([cell])
            
            for group in groups:
                min_llx = min(rect[0] for rect in group)
                min_lly = min(rect[1] for rect in group)
                max_urx = max(rect[2] for rect in group)
                max_ury = max(rect[3] for rect in group)
                groupsRect.append([min_llx, min_lly, max_urx, max_ury])
    
            return groups, groupsRect
        
        def maxGrouping(cells):
            maxGroups = []
            grouped_cells, grouped_Rects = group_cells(cells)
            currLenGroups = len(grouped_Rects)
            nextLenGroups = None
            while True:
                _org, _next = group_cells(grouped_Rects)
                nextLenGroups = len(_next)
                
                if currLenGroups == nextLenGroups:
                    maxGroups = copy.deepcopy(_next)
                    break
                else:
                    currLenGroups = nextLenGroups
                    nextLenGroups = None
            
            return maxGroups

        WScells = []
        for c in cellsWithWS:
            instName = c[0]
            WSbbox = c[-1]
            WScells.append(WSbbox)

        maxGroupRect = maxGrouping(WScells)
        ### sorting with area ###
        groupedRects = []
        for group in maxGroupRect:
            llx, lly, urx, ury = group
            area = float("{:.4f}".format((urx-llx)*(ury-lly)))
            groupedRects.append([llx, lly, urx, ury, area])

        groupedRects = sorted(groupedRects, key=lambda x:x[-1], reverse=True)
        #print("<TEST> Grouping Rects:{}".format(groupedRects))
        
        if isPlot:
            cellGroupPlotName = "cellGroup_{}.png".format(str(Csteps))
            self.plotWScellsGrouped(WScells, maxGroupRect, region=designArea, saveImg=cellGroupPlotName)
        
        return groupedRects
    
    def defineCellsPlaceRules(self, position, closest_position, cells, WScells, \
                              cellDict, WScellDict, updatedCellDict):
        
        def insertCells(cellList, cellLookUpDict, cellType):
            ## cellType = 1: white space cells
            ## cellType = 2: original cells
            placedCells = []
            for cell in cellList:
                cellName = cell

                if cellName in updatedCellDict.keys():  ### cell had been placed
                    continue

                cellWidth = cellLookUpDict[cellName]["urx"]-cellLookUpDict[cellName]["llx"]
                cellHeight = cellLookUpDict[cellName]["ury"]-cellLookUpDict[cellName]["lly"]
                cellWidth = float("{:.4f}".format(cellWidth))
                cellHeight = float("{:.4f}".format(cellHeight))
                placedCells.append([cellName, cellWidth, cellHeight, cellType])
            
            return placedCells

        
        
        placeCellList = []
        ### at the boundary case
        if len(position) > 0:
            if position[0] == "bottom-left":
                cellCount = int(len(cells)*0.5)
                CL1 = insertCells(cells[0:cellCount], cellLookUpDict=cellDict, cellType=2)
                CL2 = insertCells(WScells, cellLookUpDict=WScellDict, cellType=1)
                CL3 = insertCells(cells[cellCount:], cellLookUpDict=cellDict, cellType=2)
                placeCellList = CL1+CL2+CL3

                #CL1 = insertCells(cells, cellLookUpDict=cellDict, cellType=2)
                #CL2 = insertCells(WScells, cellLookUpDict=WScellDict, cellType=1)
                #placeCellList = CL1+CL2

            elif position[0] == "top-left":
                cellCount = int(len(cells)*0.2)
                CL1 = insertCells(cells[0:cellCount], cellLookUpDict=cellDict, cellType=2)
                CL2 = insertCells(WScells, cellLookUpDict=WScellDict, cellType=1)
                CL3 = insertCells(cells[cellCount:], cellLookUpDict=cellDict, cellType=2)
                placeCellList = CL1+CL2+CL3

            elif position[0] == "bottom-right":
                cellCount = int(len(cells)*0.2)
                CL1 = insertCells(cells[0:cellCount], cellLookUpDict=cellDict, cellType=2)
                CL2 = insertCells(WScells, cellLookUpDict=WScellDict, cellType=1)
                CL3 = insertCells(cells[cellCount:], cellLookUpDict=cellDict, cellType=2)
                placeCellList = CL1+CL2+CL3

            elif position[0] == "top-right":
                CL1 = insertCells(WScells, cellLookUpDict=WScellDict, cellType=1)
                CL2 = insertCells(cells, cellLookUpDict=cellDict, cellType=2)
                placeCellList = CL1+CL2
            
            elif position[0] in ["left", "bottom"]:
                cellCount = int(len(cells)*0.2)
                CL1 = insertCells(cells[0:cellCount], cellLookUpDict=cellDict, cellType=2)
                CL2 = insertCells(WScells, cellLookUpDict=WScellDict, cellType=1)
                CL3 = insertCells(cells[cellCount:], cellLookUpDict=cellDict, cellType=2)
                placeCellList = CL1+CL2+CL3

            elif position[0] in ["right", "top"]:
                cellCount = int(len(cells)*0.2)
                CL1 = insertCells(cells[0:cellCount], cellLookUpDict=cellDict, cellType=2)
                CL2 = insertCells(WScells, cellLookUpDict=WScellDict, cellType=1)
                CL3 = insertCells(cells[cellCount:], cellLookUpDict=cellDict, cellType=2)
                placeCellList = CL1+CL2+CL3

            else:
                pass
            
            return placeCellList

        ###
        cellCount = int(len(cells)*0.4)
        CL1 = insertCells(cells[0:cellCount], cellLookUpDict=cellDict, cellType=2)
        CL2 = insertCells(WScells, cellLookUpDict=WScellDict, cellType=1)
        CL3 = insertCells(cells[cellCount:], cellLookUpDict=cellDict, cellType=2)
        placeCellList = CL1+CL2+CL3


        return placeCellList
        

    def cellRePlacement(self, cellDict, cellsWithWS, designArea, groupedRect, \
                        Fsteps, Csteps, \
                        isPlotCells=False, isPlotPlacement=False, isPlotResult=True, isPlotAnimate=False):
        
        def updateFineDictFIX(extendRegionIndx):
            ### update self.fineDict[k]["isFIXED"] to "True" ###
            for _kx in range(extendRegionIndx[0], extendRegionIndx[2]+1):
                for _ky in range(extendRegionIndx[1], extendRegionIndx[3]+1):
                    k = "{}_{}".format(_kx, _ky)
                    self.fineDict[k]["isFIXED"] = True
    
        
        #print(self.fineXX, self.fineYY)
        WScellDict = {}
        ## cellsWithWS items => c:[instName, pd, WS, SITE_RULE, BBOX]
        for c in cellsWithWS:
            bbox = c[-1]
            pd = c[1]
            WS = c[2]
            SITE_RULE = c[3]
            area = float("{:.4f}".format((bbox[2]-bbox[0])*(bbox[3]-bbox[1])))
            WScellDict.setdefault(c[0], {"llx":bbox[0], "lly":bbox[1], "urx":bbox[2], "ury":bbox[3], \
                                         "area":area, "pd":pd, "WS":WS, "SITE_RULE":SITE_RULE})

        
        updatedCellDict = {}
        unPlacedCells = []
        for i, gRect in enumerate(groupedRect):
            print("<INFO> ===== iter:{} =====".format(str(i)))
            cells, WScells, extendRegion, extendRegionIndx = self.findExtendRegion(gRect, cellDict, WScellDict, \
                                                            updatedCellDict, isPlot=isPlotCells, savePrefix="cells_{}".format(i))
            
            if len(WScells) <= 0:
                unPlaced = []
                for cellName in cells:
                    unPlaced.append(cellName)
                
                unPlacedCells += unPlaced
                updateFineDictFIX(extendRegionIndx)
                continue

            position, closest_position = self.determine_subregion_position_and_distance(whole_region=self.designArea, sub_region=extendRegion)
            #print("Design Area: {}, extend region: {}".format(self.designArea, extendRegion))
            #print("position: ", position, closest_position)

            #print(extendRegion, WScells)

            placeCellList = self.defineCellsPlaceRules(position, closest_position, cells, WScells, \
                                                       cellDict, WScellDict, updatedCellDict)

            """
            placeCellList = []
            ### white space cells ###
            for wscell in WScells:
                cellName = wscell

                if cellName in updatedCellDict.keys():  ### cell had been placed
                    continue

                cellWidth = WScellDict[cellName]["urx"]-WScellDict[cellName]["llx"]
                cellHeight = WScellDict[cellName]["ury"]-WScellDict[cellName]["lly"]
                cellWidth = float("{:.4f}".format(cellWidth))
                cellHeight = float("{:.4f}".format(cellHeight))
                placeCellList.append([cellName, cellWidth, cellHeight, 1])
            
            ### original cells ###
            for cell in cells:
                cellName = cell

                if cellName in updatedCellDict.keys():  ### cell had been placed
                    continue

                cellWidth = cellDict[cellName]["urx"]-cellDict[cellName]["llx"]
                cellHeight = cellDict[cellName]["ury"]-cellDict[cellName]["lly"]
                cellWidth = float("{:.4f}".format(cellWidth))
                cellHeight = float("{:.4f}".format(cellHeight))
                placeCellList.append([cellName, cellWidth, cellHeight, 2])
            """
            
            ### placer ###
            PL = placeCell(cell_list=placeCellList, region=extendRegion, outputFolder=self.outputFolder)
            PL.place_cells()
            placed = PL.getPlacedCells()     # return: [[name, llx, lly, urx, ury], ...]
            unPlaced = PL.getUnPlacedCells() # return: [name, ...]

            if isPlotAnimate:
                saveAniName = "placeAnimation_{}-{}.gif".format(Csteps, i)
                PL.animate_placement(saveAniName=saveAniName)
            
            if isPlotPlacement:
                saveFile="place_{}-{}.png".format(Csteps, i)
                PL.plotPlacement(saveFile=saveFile)

            ### update cells ###
            for cell in placed:
                cellName = cell[0]
                new_llx, new_lly, new_urx, new_ury = cell[1:]
                
                org_llx, org_lly, org_urx, org_ury = cellDict[cellName]["llx"], cellDict[cellName]["lly"], cellDict[cellName]["urx"], cellDict[cellName]["ury"]
                orgPwr = cellDict[cellName]["PWR"]
                orgPD = cellDict[cellName]["PD"]

                newPD = float("{:.8f}".format(orgPwr/((new_urx-new_llx)*(new_ury-new_lly))))

                if cellName in WScellDict:
                    WS = WScellDict[cellName]["WS"]
                    SITE_RULE = WScellDict[cellName]["SITE_RULE"]
                    updatedCellDict.setdefault(cellName, {"org":[org_llx, org_lly, org_urx, org_ury, orgPwr, orgPD], \
                                                          "update":[new_llx, new_lly, new_urx, new_ury, orgPwr, newPD],\
                                                          "withWS":[WS, SITE_RULE]})
                else:
                    updatedCellDict.setdefault(cellName, {"org":[org_llx, org_lly, org_urx, org_ury, orgPwr, orgPD], \
                                                          "update":[new_llx, new_lly, new_urx, new_ury, orgPwr, newPD],\
                                                          "withWS": None})
            
            ### for un-placed cells: assign to white space corner => to do ###
            unPlacedCells += unPlaced
            
            updateFineDictFIX(extendRegionIndx)
            """
            ### update self.fineDict[k]["isFIXED"] to "True" ###
            for _kx in range(extendRegionIndx[0], extendRegionIndx[2]+1):
                for _ky in range(extendRegionIndx[1], extendRegionIndx[3]+1):
                    k = "{}_{}".format(_kx, _ky)
                    self.fineDict[k]["isFIXED"] = True
            """

        
        print("<INFO> #orgCells:{}, #UpdatedCells:{}".format(len(cellDict.keys()), len(updatedCellDict.keys())))
        for c in cellDict.keys():
            ### cell not in updatedCellDict >> unPlaced
            if not (c in updatedCellDict):
                org_llx, org_lly, org_urx, org_ury = cellDict[c]["llx"], cellDict[c]["lly"], cellDict[c]["urx"], cellDict[c]["ury"]
                orgPwr = cellDict[c]["PWR"]
                orgPD = cellDict[c]["PD"]
                
                if c in WScellDict:
                    WS = WScellDict[c]["WS"]
                    SITE_RULE = WScellDict[c]["SITE_RULE"]
                    ws_llx = org_llx - (WS[0]*SITE_RULE[0])
                    ws_lly = org_lly - (WS[1]*SITE_RULE[1])
                    ws_urx = org_urx + (WS[0]*SITE_RULE[0])
                    ws_ury = org_ury + (WS[1]*SITE_RULE[1])
                    ws_llx = float("{:.4f}".format(ws_llx))
                    ws_lly = float("{:.4f}".format(ws_lly))
                    ws_urx = float("{:.4f}".format(ws_urx))
                    ws_ury = float("{:.4f}".format(ws_ury))
                    
                    updatedCellDict.setdefault(c, {"org":[org_llx, org_lly, org_urx, org_ury, orgPwr, orgPD], \
                                          "update":[ws_llx, ws_lly, ws_urx, ws_ury, orgPwr, orgPD], \
                                          "withWS":[WS, SITE_RULE]})
                else:
                    updatedCellDict.setdefault(c, {"org":[org_llx, org_lly, org_urx, org_ury, orgPwr, orgPD], \
                                          "update":[org_llx, org_lly, org_urx, org_ury, orgPwr, orgPD], \
                                          "withWS":None})
        
        print("<INFO> UpdateALL>> #orgCells:{}, #UpdatedCells:{}".format(len(cellDict.keys()), len(updatedCellDict.keys())))

        ### upload updatedCellDict to self.cellsProcessedDict ###
        for c in updatedCellDict.keys():
            if c in self.cellsProcessedDict:
                pass
            else:
                self.cellsProcessedDict.setdefault(c, updatedCellDict[c])


        if isPlotResult:
            region = designArea
            cellList, WScellList = [], []
            for c in cellDict:
                llx, lly, urx, ury = cellDict[c]["llx"], cellDict[c]["lly"], cellDict[c]["urx"], cellDict[c]["ury"]
                if c in WScellDict:
                    WScellList.append([[llx, lly, urx, ury], [llx, lly, urx, ury]])
                else:
                    cellList.append([llx, lly, urx, ury])
            
            cellPlacementName = "cellPlaceBefore_{}.png".format(str(Csteps))
            self.plotCells(cellList=cellList, WScellList=WScellList, region=region, saveImg=cellPlacementName)

            cellList, WScellList = [], []
            for c in updatedCellDict:
                llx, lly, urx, ury = updatedCellDict[c]["update"][0:4]
                
                if updatedCellDict[c]["withWS"] is None:
                    cellList.append([llx, lly, urx, ury])
                else:
                    WS = updatedCellDict[c]["withWS"][0]
                    SITE_RULE = updatedCellDict[c]["withWS"][1]
                    _llx = llx + (WS[0]*SITE_RULE[0])
                    _lly = lly + (WS[1]*SITE_RULE[1])
                    _urx = urx - (WS[0]*SITE_RULE[0])
                    _ury = ury - (WS[1]*SITE_RULE[1])
                    _llx = float("{:.4f}".format(_llx))
                    _lly = float("{:.4f}".format(_lly))
                    _urx = float("{:.4f}".format(_urx))
                    _ury = float("{:.4f}".format(_ury))

                    ## [[rect1], [rect2]] > rect1: cell, rect2: white space
                    WScellList.append([[_llx, _lly, _urx, _ury], [llx, lly, urx, ury]])
            
            cellPlacementName = "cellPlaceAfter_{}.png".format(str(Csteps))
            self.plotCells(cellList=cellList, WScellList=WScellList, region=region, saveImg=cellPlacementName)



    def findExtendRegion(self, rect, cellDict, WScellDict, updatedCellDict, blockNum=50, \
                         isPlot=True, savePrefix="cells"):
        
        def is_overlapping(cell1, cell2):
            # Check if two cells overlap
            return not (cell1[2] <= cell2[0] or cell1[0] >= cell2[2] or cell1[3] <= cell2[1] or cell1[1] >= cell2[3])

        def insertCells(kid, WScellDict):
            _WScells, _cells = [], []
            for c in self.fineDict[kid]["CELLS"]:
                instName = c[0]
                if not ((instName in WScellDict) or (instName in updatedCellDict) or (instName in self.cellsProcessedDict)):
                    _cells.append(instName)
            
            ### check white space ###
            tileRegion = [self.fineDict[kid]["llx"], self.fineDict[kid]["lly"], self.fineDict[kid]["urx"], self.fineDict[kid]["ury"]]
            for ws in WScellDict.keys():
                if ws in updatedCellDict:
                    pass
                else:
                    wsRegion = [WScellDict[ws]["llx"], WScellDict[ws]["lly"], WScellDict[ws]["urx"], WScellDict[ws]["ury"]]
                    if is_overlapping(tileRegion, wsRegion):
                        _WScells.append(ws)
            
            return _cells, _WScells
        
        def calCellsArea(cellList, cellDict, WScellDict, cType="CELL"):
            cellsArea = 0.0
            cellsRect = []
            for c in cellList:
                if cType == "CELL":
                    _area = float("{:.4f}".format((cellDict[c]["urx"]-cellDict[c]["llx"])*(cellDict[c]["ury"]-cellDict[c]["lly"])))
                    cellsRect.append([cellDict[c]["llx"], cellDict[c]["lly"], cellDict[c]["urx"], cellDict[c]["ury"]])
                elif cType == "WS":
                    _area = float("{:.4f}".format((WScellDict[c]["urx"]-WScellDict[c]["llx"])*(WScellDict[c]["ury"]-WScellDict[c]["lly"])))
                    cellsRect.append([[cellDict[c]["llx"], cellDict[c]["lly"], cellDict[c]["urx"], cellDict[c]["ury"]], \
                                      [WScellDict[c]["llx"], WScellDict[c]["lly"], WScellDict[c]["urx"], WScellDict[c]["ury"]]])
                
                cellsArea += _area
            
            return cellsArea, cellsRect
        

        MIN_X_ID, MAX_X_ID = 0, len(self.fineXX)-1
        MIN_Y_ID, MAX_Y_ID = 0, len(self.fineYY)-1
        LLX, LLY = self.fineXX[0], self.fineYY[0]

        llx_id = math.floor((rect[0]-LLX)/self.fineR)
        lly_id = math.floor((rect[1]-LLY)/self.fineR)
        urx_id = math.ceil((rect[2]-LLX)/self.fineR)
        ury_id = math.ceil((rect[3]-LLY)/self.fineR)

        if urx_id > MAX_X_ID:
            urx_id = MAX_X_ID
        if ury_id > MAX_Y_ID:
            ury_id = MAX_Y_ID
        if llx_id < MIN_X_ID:
            llx_id = MIN_X_ID
        if lly_id < MIN_Y_ID:
            lly_id = MIN_Y_ID
        
        ### check boundary ###
        passTiles = []
        for _x in range(llx_id, urx_id+1):
            for _y in range(lly_id, ury_id+1):
                fine = "{}_{}".format(_x, _y)
                if not self.fineDict[fine]["isFIXED"]:
                    passTiles.append(fine)
        
        XX, YY = [], []
        for tt in passTiles:
            _x, _y = tt.split("_")
            XX.append(int(_x))
            YY.append(int(_y))
        
        if len(XX) > 0 and len(YY) > 0:
            llx_id = min(XX)
            lly_id = min(YY)
            urx_id = max(XX)
            ury_id = max(YY)
        ###########################
        
        ll_key = "{}_{}".format(llx_id, lly_id)
        ur_key = "{}_{}".format(urx_id, ury_id)

        run_llx = self.fineDict[ll_key]["llx"]
        run_lly = self.fineDict[ll_key]["lly"]
        run_urx = self.fineDict[ur_key]["urx"]
        run_ury = self.fineDict[ur_key]["ury"]

        extendRegion = [run_llx, run_lly, run_urx, run_ury]
        extendRegionIndx = [llx_id, lly_id, urx_id, ury_id]

        if len(passTiles) == 0:
            return [], [], extendRegion, extendRegionIndx

        cells, WScells = [], []   ### cells in this region
        groupArea = 0.0
        for xx in range(llx_id, urx_id+1):
            for yy in range(lly_id, ury_id+1):
                groupArea += (self.fineR)*(self.fineR)
                kk = "{}_{}".format(xx, yy)
                _Cs, _WSs = insertCells(kk, WScellDict)
                cells += _Cs
                WScells += _WSs
            
        WScells = list(set(WScells))
        cells = list(set(cells))

        cellsArea = 0.0
        A1, _cells = calCellsArea(cells, cellDict, WScellDict, cType="CELL")
        A2, _WScells = calCellsArea(WScells, cellDict, WScellDict, cType="WS")
            
        cellsArea = A1 + A2
        cellsArea = float("{:.4f}".format(cellsArea))

        if isPlot:  ## extendRegion = [run_llx, run_lly, run_urx, run_ury]
            self.plotCells(_cells, _WScells, region=extendRegion, saveImg="{}.png".format(savePrefix))
        
        print("<INFO> >> Group area:{}, cells area:{}".format(groupArea, cellsArea))

        ### extend area ###
        ex_llx_id = llx_id
        ex_lly_id = lly_id
        ex_urx_id = urx_id
        ex_ury_id = ury_id
        exCount = 0
        while True:
            ### 4 edges ###
            cost_left, cost_right, cost_under, cost_up = [], [], [], []
            avg_left, avg_right, avg_under, avg_up = 100, 100, 100, 100
            ## > left_cost
            if ex_llx_id - 1 < MIN_X_ID:
                pass
            else:
                totalCount = 0
                isFixCount = 0
                for _y in range(ex_lly_id, ex_ury_id+1):
                    _k = "{}_{}".format(ex_llx_id-1, _y)
                    cost_left.append(self.fineDict[_k]["cost"])
                    
                    if self.fineDict[_k]["isFIXED"]:
                        isFixCount += 1
                    
                    totalCount += 1
                
                if isFixCount/totalCount > 0.7:
                    ### the selected regions are fixed, clear the cost list ###
                    cost_left = []

                
            ## > right_cost
            if ex_urx_id + 1 > MAX_X_ID:
                pass
            else:
                totalCount = 0
                isFixCount = 0
                for _y in range(ex_lly_id, ex_ury_id+1):
                    _k = "{}_{}".format(ex_urx_id+1, _y)
                    cost_right.append(self.fineDict[_k]["cost"])

                    if self.fineDict[_k]["isFIXED"]:
                        isFixCount += 1

                    totalCount += 1
                
                if isFixCount/totalCount > 0.7:
                    ### the selected regions are fixed, clear the cost list ###
                    cost_right = []

                
            ## > under_cost
            if ex_lly_id - 1 < MIN_Y_ID:
                pass
            else:
                totalCount = 0
                isFixCount = 0
                for _x in range(ex_llx_id, ex_urx_id+1):
                    _k = "{}_{}".format(_x, ex_lly_id-1)
                    cost_under.append(self.fineDict[_k]["cost"])

                    if self.fineDict[_k]["isFIXED"]:
                        isFixCount += 1

                    totalCount += 1
                
                if isFixCount/totalCount > 0.7:
                    ### the selected regions are fixed, clear the cost list ###
                    cost_under = []

                
            ## > up_cost
            if ex_ury_id + 1 > MAX_Y_ID:
                pass
            else:
                totalCount = 0
                isFixCount = 0
                for _x in range(ex_llx_id, ex_urx_id+1):
                    _k = "{}_{}".format(_x, ex_ury_id+1)
                    cost_up.append(self.fineDict[_k]["cost"])

                    if self.fineDict[_k]["isFIXED"]:
                        isFixCount += 1

                    totalCount += 1
                
                if isFixCount/totalCount > 0.7:
                    ### the selected regions are fixed, clear the cost list ###
                    cost_up = []
            
            if len(cost_left) == 0 and len(cost_right) == 0 and len(cost_under) == 0 and len(cost_up) == 0:
                ### no available region can be extended ###
                break
                
            #print(cost_left, cost_right, cost_under, cost_up)

            if len(cost_left) > 0:
                avg_left = float("{:.3f}".format(sum(cost_left)/len(cost_left)))
            else:
                pass
                
            if len(cost_right) > 0:
                avg_right = float("{:.3f}".format(sum(cost_right)/len(cost_right)))
            else:
                pass
                
            if len(cost_under) > 0:
                avg_under = float("{:.3f}".format(sum(cost_under)/len(cost_under)))
            else:
                pass
                
            if len(cost_up) > 0:
                avg_up = float("{:.3f}".format(sum(cost_up)/len(cost_up)))
            else:
                pass
            
            #print("left:{}, right:{}, under:{}, up:{}".format(avg_left, avg_right, avg_under, avg_up))

            ### select the smallest one ###
            ext_dir = sorted([[avg_left, 0], [avg_right, 1], [avg_under, 2], [avg_up, 3]], key=lambda x:x[0])[0]
            
            #print("extend dir:{}, ex_llx_id:{}, ex_lly_id:{}, ex_urx_id:{}, ex_ury_id:{}".format(ext_dir, \
            #                                   ex_llx_id, ex_lly_id, ex_urx_id, ex_ury_id))

            addCells, addWSCells = [], []
            if ext_dir[1] == 0:  ## left
                for _y in range(ex_lly_id, ex_ury_id+1):
                    _k = "{}_{}".format(ex_llx_id-1, _y)
                    _Cs, _WSs = insertCells(_k, WScellDict)
                    addCells += _Cs
                    addWSCells += _WSs
                    groupArea += (self.fineR)*(self.fineR)
                    
                ex_llx_id = ex_llx_id-1
                
            if ext_dir[1] == 1:  ## right
                for _y in range(ex_lly_id, ex_ury_id+1):
                    _k = "{}_{}".format(ex_urx_id+1, _y)
                    _Cs, _WSs = insertCells(_k, WScellDict)
                    addCells += _Cs
                    addWSCells += _WSs
                    groupArea += (self.fineR)*(self.fineR)
                    
                ex_urx_id = ex_urx_id+1
                
            if ext_dir[1] == 2:  ## under
                for _x in range(ex_llx_id, ex_urx_id+1):
                    _k = "{}_{}".format(_x, ex_lly_id-1)
                    _Cs, _WSs = insertCells(_k, WScellDict)
                    addCells += _Cs
                    addWSCells += _WSs
                    groupArea += (self.fineR)*(self.fineR)
                    
                ex_lly_id = ex_lly_id-1
                
            if ext_dir[1] == 3:  ## up
                for _x in range(ex_llx_id, ex_urx_id+1):
                    _k = "{}_{}".format(_x, ex_ury_id+1)
                    _Cs, _WSs = insertCells(_k, WScellDict)
                    addCells += _Cs
                    addWSCells += _WSs
                    groupArea += (self.fineR)*(self.fineR)
                    
                ex_ury_id = ex_ury_id+1
                
            #print(addCells, addWSCells)

            WScells += addWSCells
            cells += addCells
            WScells = list(set(WScells))
            cells = list(set(cells))

            cellsArea = 0.0
            A1, _cells = calCellsArea(cells, cellDict, WScellDict, cType="CELL")
            A2, _WScells = calCellsArea(WScells, cellDict, WScellDict, cType="WS")
            
            cellsArea = A1 + A2
            cellsArea = float("{:.4f}".format(cellsArea))

            ll_key = "{}_{}".format(ex_llx_id, ex_lly_id)
            ur_key = "{}_{}".format(ex_urx_id, ex_ury_id)

            ext_llx = self.fineDict[ll_key]["llx"]
            ext_lly = self.fineDict[ll_key]["lly"]
            ext_urx = self.fineDict[ur_key]["urx"]
            ext_ury = self.fineDict[ur_key]["ury"]
            
            extendRegion = [ext_llx, ext_lly, ext_urx, ext_ury]
            extendRegionIndx = [ex_llx_id, ex_lly_id, ex_urx_id, ex_ury_id]

            exCount += 1

            if isPlot:
                self.plotCells(_cells, _WScells, region=extendRegion, saveImg="{}_{}.png".format(savePrefix, exCount))
            
            print("  <INFO> *{}/{} Group area:{}, cells area:{}".format(exCount, blockNum, groupArea, cellsArea))

            if exCount > blockNum:
                break
                
            if groupArea > cellsArea*self.AREAMARGIN:
                break
        
        print("<INFO >To be placed > #cells:{}, #WScells:{}".format(len(cells), len(WScells)))
        return cells, WScells, extendRegion, extendRegionIndx

    
    def checkAllCells(self):
        print("<INFO> CHECK ALL #Input_Cells:{}, #Processed_Cells:{}".format(len(self.orgCellNetList.keys()), len(self.cellsProcessedDict.keys())))
        for c in self.orgCellNetList.keys():
            if not (c in self.cellsProcessedDict):
                lls = (self.orgCellNetList[c]).split(",")
                llx, lly, urx, ury = lls[2:6]
                llx = float(llx)
                lly = float(lly)
                urx = float(urx)
                ury = float(ury)
                pwr = float(lls[6])
                pd = pwr/((urx-llx)*(ury-lly))
                pd = float("{:.6f}".format(pd))

                self.cellsProcessedDict.setdefault(c, {"org":[llx, lly, urx, ury, pwr, pd], \
                                          "update":[llx, lly, urx, ury, pwr, pd], \
                                          "withWS":None})
        
        print("<INFO> FINAL UPDATE >> #Input_Cells:{}, #Processed_Cells:{}".format(len(self.orgCellNetList.keys()), len(self.cellsProcessedDict.keys())))
    
    
    def toNextCoarseMesh(self, coarseID):
        self.coarseDict[coarseID]["isFIXED"] = True

    
    def netlistWriteOut(self, Csteps, isFinal=False):
        if isFinal:
            subCase = "_netlistStep_{}".format(str(Csteps))
        else:
            subCase = "netlistStep_{}".format(str(Csteps))

        caseFolder = os.path.join(self.outputFolder, subCase)
        if not os.path.isdir(caseFolder):
            os.makedirs(caseFolder, 0o777)
        else:
            ### remove the existed case ###
            contents = [os.path.join(caseFolder, i)  for i in os.listdir(caseFolder)]
            [shutil.rmtree(i) if os.path.isdir(i) and not os.path.islink(i) else os.remove(i) for i in contents]

        ## update CELL_PADDING & generate padding script ##
        ## set_inst_padding -inst z_intf[0].hbi_intf_0/prects_FE_OFC10109_n_779 -right_side 7 -left_side 7 -bottom_side 7 -top_side 7
        processedCells = 0
        processedPwr = 0.0
        orgCellsArea, updateCellsArea = 0.0, 0.0
        HEADER = "Cell_Name,Cell_Type,lx,ly,ux,uy,power"
        netlistOutStr = [HEADER]
        padOutStr = []
        ## "org":[llx, lly, urx, ury, Pwr, PD], \
        ## "update":[llx, lly, urx, ury, Pwr, PD], \
        ## "withWS":[WS, SITE_RULE]}
        for c in self.cellsProcessedDict.keys():
            cellName = c
            cellType = (self.orgCellNetList[c]).split(",")[1]
            org_llx, org_lly, org_urx, org_ury = self.cellsProcessedDict[c]["org"][0:4]
            
            llx, lly, urx, ury = self.cellsProcessedDict[c]["update"][0:4]
            pwr = self.cellsProcessedDict[c]["update"][4]

            orgCellsArea += (org_urx-org_llx)*(org_ury-org_lly)
            updateCellsArea += (urx-llx)*(ury-lly)
            processedPwr += pwr
            
            llx = self.__F2Sprecision(llx, prec=4)
            lly = self.__F2Sprecision(lly, prec=4)
            urx = self.__F2Sprecision(urx, prec=4)
            ury = self.__F2Sprecision(ury, prec=4)
            pwr = self.__F2Sprecision(pwr, prec=8)

            newList = [cellName, cellType, llx, lly, urx, ury, pwr]
            netlistOutStr.append(",".join(newList))

            if not(self.cellsProcessedDict[c]["withWS"] is None):
                WS_X, WS_Y = self.cellsProcessedDict[c]["withWS"][0]
                _str = "set_inst_padding -inst {} -right_side {} -left_side {} -bottom_side {} -top_side {}".format(c, WS_X, WS_X, WS_Y, WS_Y)
                padOutStr.append(_str)
            
            processedCells += 1
        
        
        orgCellsArea = float(self.__F2Sprecision(orgCellsArea, prec=4))
        updateCellsArea = float(self.__F2Sprecision(updateCellsArea, prec=4))
        processedPwr = float(self.__F2Sprecision(processedPwr, prec=4))

        
        outPath = os.path.join(caseFolder, "paddingList.tcl")
        with open(outPath, "w") as fid:
            fid.write("\n".join(padOutStr))
        
        outPath = os.path.join(caseFolder, "cellsNetlist.csv")
        with open(outPath, "w") as fid:
            fid.write("\n".join(netlistOutStr))
        
        dieArea = (self.designArea[2]-self.designArea[0])*(self.designArea[3]-self.designArea[1])
        dieArea = float(self.__F2Sprecision(dieArea, prec=4))

        self.areaOverHead = self.__F2Sprecision((updateCellsArea-orgCellsArea)/orgCellsArea, prec=3)

        summaryStr = [">>>>> Summary <<<<<"]
        summaryStr.append("Design_Area: {}".format(str(dieArea)))
        summaryStr.append("Total_Cells: {}".format(self.totalCells))
        summaryStr.append("Processed_Cells: {}".format(str(processedCells)))
        summaryStr.append("Original_Cells_Area: {}".format(str(orgCellsArea)))
        summaryStr.append("Updated_Cells_Area: {}".format(str(updateCellsArea)))
        summaryStr.append("Overhead: {}".format(self.areaOverHead))
        summaryStr.append("Original_Input_Power_mW: {}".format(str(self.totalInputPwr)))
        summaryStr.append("Processed_Power_mW: {}".format(str(processedPwr)))

        outPath = os.path.join(caseFolder, "summary.txt")
        with open(outPath, "w") as fid:
            fid.write("\n".join(summaryStr))
        
        print("<INFO> #Cells processed: {}, Area overhead: {}".format(processedCells, self.areaOverHead))

        if isFinal:
            ### also export original netlist ###
            netlistOrgStr = [HEADER]
            for c in self.orgCellSeq:
                netlistOrgStr.append(self.orgCellNetList[c])
            
            outPath = os.path.join(caseFolder, "orgNetlist.csv")
            with open(outPath, "w") as fid:
                fid.write("\n".join(netlistOrgStr))

        #sys.exit(1)


    def plotCells(self, cellList, WScellList, region, saveImg="cells.png"):
        import matplotlib
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle

        fig, ax = plt.subplots()

        # Set the limits of the plot to the given region
        ax.set_xlim(region[0], region[2])
        ax.set_ylim(region[1], region[3])

        # Add each rectangle to the plot
        for rects in cellList:
            ### for cell 
            llx, lly, urx, ury = rects
            width = urx - llx
            height = ury - lly
            ax.add_patch(Rectangle((llx, lly), width, height, edgecolor="blue", facecolor="skyblue"))
        
        for rects in WScellList:
            llx, lly, urx, ury = rects[0]
            width = urx - llx
            height = ury - lly
            ax.add_patch(Rectangle((llx, lly), width, height, edgecolor="goldenrod", facecolor="goldenrod"))

            ### with WS
            llx, lly, urx, ury = rects[1]
            width = urx - llx
            height = ury - lly
            ax.add_patch(Rectangle((llx, lly), width, height, edgecolor="maroon", facecolor="none", linestyle="--"))

        # Save the plot to an image file
        imgPath = os.path.join(self.outputFolder, saveImg)
        plt.savefig(imgPath, bbox_inches="tight")
        plt.close(fig)


    def plotWSCells(self, cellList, region, saveImg="WSCells.png"):
        import matplotlib
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle

        fig, ax = plt.subplots()

        # Set the limits of the plot to the given region
        ax.set_xlim(region[0], region[2])
        ax.set_ylim(region[1], region[3])

        # Add each rectangle to the plot
        for rects in cellList:
            ### for cell 
            llx, lly, urx, ury = rects[0]
            width = urx - llx
            height = ury - lly
            ax.add_patch(Rectangle((llx, lly), width, height, edgecolor="blue", facecolor="blue"))

            ### with WS
            llx, lly, urx, ury = rects[1]
            width = urx - llx
            height = ury - lly
            ax.add_patch(Rectangle((llx, lly), width, height, edgecolor="maroon", facecolor="none"))

        # Save the plot to an image file
        imgPath = os.path.join(self.outputFolder, saveImg)
        plt.savefig(imgPath, bbox_inches="tight")
        plt.close(fig)
    
    
    def plotWScellsGrouped(self, WScellList, groupedList, region, saveImg="cellsGrouping.png"):
        import matplotlib
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle

        fig, ax = plt.subplots()

        # Set the limits of the plot to the given region
        ax.set_xlim(region[0], region[2])
        ax.set_ylim(region[1], region[3])

        for cell in WScellList:
            llx, lly, urx, ury = cell
            width = urx - llx
            height = ury - lly
            ax.add_patch(Rectangle((llx, lly), width, height, edgecolor="blue", facecolor="blue"))
        
        for group in groupedList:
            llx, lly, urx, ury = group
            width = urx - llx
            height = ury - lly
            ax.add_patch(Rectangle((llx, lly), width, height, edgecolor="red", facecolor="none", linestyle="--"))
        
        # Save the plot to an image file
        imgPath = os.path.join(self.outputFolder, saveImg)
        plt.savefig(imgPath, bbox_inches="tight")
        plt.close(fig)

    
    
    def plotGroupedCells(self, grouped_cells, region, saveImg="GroupCells.png"):
        import matplotlib
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle

        fig, ax = plt.subplots()

        # Set the limits of the plot to the given region
        ax.set_xlim(region[0], region[2])
        ax.set_ylim(region[1], region[3])

        # Add each group of rectangles to the plot with red bounded box
        for group in grouped_cells:
            min_llx = min(rect[0] for rect in group)
            min_lly = min(rect[1] for rect in group)
            max_urx = max(rect[2] for rect in group)
            max_ury = max(rect[3] for rect in group)
        
            for rect in group:
                llx, lly, urx, ury = rect
                width = urx - llx
                height = ury - lly
                ax.add_patch(Rectangle((llx, lly), width, height, edgecolor="blue", facecolor="none"))
        
            # Add the bounding box for the group
            group_width = max_urx - min_llx
            group_height = max_ury - min_lly
            ax.add_patch(Rectangle((min_llx, min_lly), group_width, group_height, edgecolor="red", facecolor="none", linestyle="--"))

        # Save the plot to an image file
        imgPath = os.path.join(self.outputFolder, saveImg)
        plt.savefig(imgPath, bbox_inches="tight")
        plt.close(fig)



if __name__ == "__main__":
    pass
    
    
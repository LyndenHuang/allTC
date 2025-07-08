import os
import sys
import json
import re
import math
import numpy as np
import argparse
import copy

def arg():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--thermalProfile", type=str, required=False, default="", help="Detail thermal profile from RHSC-ET")
    parser.add_argument(
        "--outputFolder", type=str, required=False, default="./", help="output folder")
    parser.add_argument(
        "--outputName", type=str, required=False, default="pwd.mhs", help="output name")   

    return parser


class RHSCETView:
    def __init__(self, profilePath, outputFolder="./"):
        self.profilePath = profilePath
        self.outputFolder = outputFolder

        self.llx, self.lly, self.urx, self.ury = None, None, None, None
        self.tileX, self.tileY = None, None
        self.layers = None
        self.scale_factor = None

        self.layerList = []
        self.tileKeys = []

        self.dbDict = {}
        ### The highest T in this DIE profile ###
        self.DIEMaxT = -100000
        self.DIEMinT = 100000

        self.stepX = []
        self.stepY = []

        self.parsing()
    
    def __F2Sprecision(self, fval, prec=4):
        precStr= "{:."+str(prec)+"f}"
        return precStr.format(fval)
    

    def parsing(self):
        """
        Parses the thermal profile file to extract die area, tile information, layers, and temperature data.
    
        This function reads the thermal profile file line by line and extracts:
        - Die area coordinates (llx, lly, urx, ury).
        - Tile dimensions (tileX, tileY).
        - Layer information (number of layers and their names).
        - Scaling factor for the thermal profile.
        - Temperature values for each tile and layer.
    
        Populates the following attributes:
        - `self.llx`, `self.lly`, `self.urx`, `self.ury`: Die area coordinates.
        - `self.tileX`, `self.tileY`: Number of tiles in X and Y directions.
        - `self.layers`: Number of layers.
        - `self.layerList`: List of layer names.
        - `self.dbDict`: Dictionary storing temperature data for each layer and tile.
        - `self.DIEMaxT`, `self.DIEMinT`: Maximum and minimum temperatures across the die.
        - `self.stepX`, `self.stepY`: Sorted lists of unique X and Y tile boundaries.
    
        Raises:
            FileNotFoundError: If the thermal profile file does not exist.
            ValueError: If the number of layers does not match the parsed layer names.
        """
        if not os.path.isfile(self.profilePath):
            raise FileNotFoundError(f"[ERROR] {self.profilePath} path not found")
    
        _stepX, _stepY = {}, {}
        with open(self.profilePath, "r") as fid:
            for i, line in enumerate(fid):
                line = line.strip()
                diearea = re.match(r"^# DIE.* ([-+]?\d*\.?\d+) ([-+]?\d*\.?\d+) ([-+]?\d*\.?\d+) ([-+]?\d*\.?\d+).*", line)
                tile = re.match(r"^# TILE.* (\d+) (\d+).*", line)
                layers = re.match(r"^# LAYER (\d+) (.*)", line)
                scale = re.match(r"^# SCALE_FACTOR (\d*\.?\d+).*", line)
                entries = re.match(r"^[0-9].*", line)
    
                # Parse die area
                if diearea:
                    self.llx, self.lly = float(diearea.group(1)), float(diearea.group(2))
                    self.urx, self.ury = float(diearea.group(3)), float(diearea.group(4))
    
                # Parse tile dimensions
                if tile:
                    self.tileX, self.tileY = int(tile.group(1)), int(tile.group(2))
    
                # Parse layers
                if layers:
                    self.layers = int(layers.group(1))
                    for ly in layers.group(2).split():
                        self.layerList.append(ly)
                        self.dbDict.setdefault(ly, {
                            "TILES": {},
                            "FEATURES": {
                                "MAXT": {"VAL": -100000, "KEY": None},
                                "MINT": {"VAL": 100000, "KEY": None}
                            }
                        })
                    # Validate the number of layers
                    if len(self.layerList) != self.layers:
                        raise ValueError("<ERROR> Layer numbers do not match")
    
                # Parse scaling factor
                if scale:
                    self.scale_factor = float(scale.group(1))
    
                # Parse tile entries
                if entries:
                    lls = line.split()
                    tid = lls[0]
                    llx, lly, urx, ury = lls[1:5]  ## string type

                    kllx = self.__F2Sprecision(float(llx), prec=4)
                    klly = self.__F2Sprecision(float(lly), prec=4)
                    kurx = self.__F2Sprecision(float(urx), prec=4)
                    kury = self.__F2Sprecision(float(ury), prec=4)

                    key = "_".join([kllx, klly, kurx, kury])
                    self.tileKeys.append(key)
    
                    _stepX.setdefault(llx, float(llx))
                    _stepX.setdefault(urx, float(urx))
                    _stepY.setdefault(lly, float(lly))
                    _stepY.setdefault(ury, float(ury))
    
                    if not self.layerList:
                        raise ValueError("<ERROR> Layers not set before parsing entries")
    
                    # Parse temperature values for each layer
                    for i, ly in enumerate(self.layerList):
                        tVal = float(lls[5 + i])
                        self.dbDict[ly]["TILES"].setdefault(key, tVal)
                        if self.dbDict[ly]["FEATURES"]["MAXT"]["VAL"] < tVal:
                            self.dbDict[ly]["FEATURES"]["MAXT"]["VAL"] = tVal
                            self.dbDict[ly]["FEATURES"]["MAXT"]["KEY"] = key
    
                        if self.dbDict[ly]["FEATURES"]["MINT"]["VAL"] > tVal:
                            self.dbDict[ly]["FEATURES"]["MINT"]["VAL"] = tVal
                            self.dbDict[ly]["FEATURES"]["MINT"]["KEY"] = key
    
                        if self.DIEMaxT < tVal:
                            self.DIEMaxT = tVal
    
                        if self.DIEMinT > tVal:
                            self.DIEMinT = tVal
    
        # Sort step coordinates
        self.stepX = sorted([[i, _stepX[i]] for i in _stepX.keys()], key=lambda x: x[1])
        self.stepY = sorted([[i, _stepY[i]] for i in _stepY.keys()], key=lambda x: x[1])

   
    def getTopNHotSpots(self, selectedLayer="MEOL", topN=10):

        dbDict = self.dbDict[selectedLayer]["TILES"]
        _cellsT = [(i, float(self.__F2Sprecision(dbDict[i], 4))) for i in dbDict.keys()]
        sortedCells = sorted(_cellsT, key=lambda x:x[1], reverse=True)

        topNTiles = []
        for i in range(topN):
            tileID = sortedCells[i][0]
            topNTiles.append(tileID)
        
        return topNTiles
    
    
    def getLayerRegionalT(self, selectedLayer="M0", region=[]):
        """
        Calculate the maximum, average, and minimum temperatures for a specific region in a selected layer.
        The input region is in design coordinates and is translated into tile coordinates.

        Parameters:
            selectedLayer (str): The layer to analyze.
            region (list): The region in design coordinates [llx, lly, urx, ury].

        Returns:
            tuple: Max temperature, average temperature, min temperature, and all temperature values in the region.
        """
        # Translate the input region into the thermal profile's coordinate system
        offsetX, offsetY = self.llx, self.lly
        dieWidth, dieHeight = self.urx - self.llx, self.ury - self.lly

        # Convert design region to thermal profile coordinates
        _llx = region[0] + offsetX
        _lly = region[1] + offsetY
        _urx = region[2] + offsetX
        _ury = region[3] + offsetY

        # Get sorted step coordinates for X and Y
        _stepX = [step[1] for step in self.stepX]
        _stepY = [step[1] for step in self.stepY]

        # Find the corresponding tile boundaries for the region
        rstepX = self._getTileSteps(_stepX, _llx, _urx)
        rstepY = self._getTileSteps(_stepY, _lly, _ury)
        
        #print("region: ", region)
        #print(offsetX, offsetY)
        #print(_stepX, _stepY)
        #print(_llx, _lly, _urx, _ury, rstepX, rstepY)

        # Retrieve temperature values for the tiles in the region
        dbDict = self.dbDict[selectedLayer]["TILES"]
        allT = []
        MaxT, MinT, avgT = -100000, 100000, 0.0
        #print(dbDict)

        for _x in range(len(rstepX) - 1):
            for _y in range(len(rstepY) - 1):
                kllx = self.__F2Sprecision(float(rstepX[_x]), prec=4)
                klly = self.__F2Sprecision(float(rstepY[_y]), prec=4)
                kurx = self.__F2Sprecision(float(rstepX[_x + 1]), prec=4)
                kury = self.__F2Sprecision(float(rstepY[_y + 1]), prec=4)
                tileKey = "_".join([kllx, klly, kurx, kury])
                
                if tileKey in dbDict:
                    temp = dbDict[tileKey]
                    allT.append(self.__F2Sprecision(temp, prec=3))
                    avgT += temp
                    MaxT = max(MaxT, temp)
                    MinT = min(MinT, temp)

        # Calculate average temperature
        avgT = avgT / len(allT) if allT else 0.0

        # Format temperatures to the desired precision
        MaxT = self.__F2Sprecision(MaxT, prec=3)
        MinT = self.__F2Sprecision(MinT, prec=3)
        avgT = self.__F2Sprecision(avgT, prec=3)
        #print(allT, MaxT, MinT, avgT)

        return MaxT, avgT, MinT, allT
    
    def _getTileSteps(self, stepList, start, end):
        """
        Helper function to find the corresponding tile steps for a given range.
    
        Parameters:
            stepList (list): Sorted list of step coordinates.
            start (float): Start coordinate.
            end (float): End coordinate.
    
        Returns:
            list: List of tile step keys, ensuring the first value is <= start and the last value is >= end.
        """
        tileSteps = []
    
        # Ensure the first value is less than or equal to the start
        lower_bound_index = None
        for i in range(len(stepList)):
            if stepList[i] <= start:
                lower_bound_index = i
            else:
                break
    
        # If no valid lower bound is found, return an empty list
        if lower_bound_index is None:
            return tileSteps
    
        # Add steps starting from the lower bound
        for i in range(lower_bound_index, len(stepList)):
            tileSteps.append(stepList[i])
            if stepList[i] >= end:
                break
    
        # Ensure the last value is greater than or equal to the end
        if tileSteps and tileSteps[-1] < end:
            for i in range(len(stepList)):
                if stepList[i] >= end:
                    tileSteps.append(stepList[i])
                    break
    
        return tileSteps

    
    def getLayerTMax(self, selectedLayer="M0"):
        dbDict = self.dbDict[selectedLayer]["TILES"]
        _cellsT = [(i, dbDict[i]) for i in dbDict.keys()]
        sortedCells = sorted(_cellsT, key=lambda x:x[1], reverse=True)

        return self.__F2Sprecision(sortedCells[0][1], 4)
    
    def getLayerTMin(self, selectedLayer="M0"):
        dbDict = self.dbDict[selectedLayer]["TILES"]
        _cellsT = [(i, dbDict[i]) for i in dbDict.keys()]
        sortedCells = sorted(_cellsT, key=lambda x:x[1], reverse=True)

        return self.__F2Sprecision(sortedCells[-1][1], 4)
    
    def getLayerTvals(self, selectedLayer="M0"):
        tileHeader, tileTval = [], []
        dbDict = self.dbDict[selectedLayer]["TILES"]
        for tt in self.tileKeys:
            tileHeader.append(tt)
            tileTval.append(self.__F2Sprecision(dbDict[tt], 4))
        
        return tileHeader, tileTval
    
    def plot(self, dieName="DIE", selectedLayer="MEOL",
             min_val=None, max_val=None,
             highlighted=[], withColorBar=False,
             saveImg="Tprofile.png", isShow=False):
        """
        Plots the thermal profile for a selected layer.
    
        Parameters:
            dieName (str): Name of the die to display in the plot title.
            selectedLayer (str): The layer to visualize.
            min_val (float, optional): Minimum temperature value for the color scale. Defaults to the layer's minimum temperature.
            max_val (float, optional): Maximum temperature value for the color scale. Defaults to the layer's maximum temperature.
            highlighted (list, optional): List of tile keys to highlight in the plot. Defaults to an empty list.
            withColorBar (bool, optional): Whether to include a color bar in the plot. Defaults to False.
            saveImg (str, optional): File name to save the plot image. Defaults to "Tprofile.png".
            isShow (bool, optional): Whether to display the plot interactively. Defaults to False.
    
        Returns:
            str: Path to the saved image file if `isShow` is False. Otherwise, returns None.
        """
        import matplotlib
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle
        import numpy as np
        import matplotlib.cm as cm
        import matplotlib.ticker as mticker
    
        # Initialize the plot
        fig, ax = plt.subplots(1, 1, figsize=[8, 8])
    
        # Determine min and max temperature values for the color scale
        if min_val is None:
            min_val = float(self.__F2Sprecision(self.dbDict[selectedLayer]["FEATURES"]["MINT"]["VAL"]))
        else:
            min_val = float("{:.3f}".format(float(min_val)))
    
        if max_val is None:
            max_val = float(self.__F2Sprecision(self.dbDict[selectedLayer]["FEATURES"]["MAXT"]["VAL"]))
        else:
            max_val = float("{:.3f}".format(float(max_val)))
    
        mid_val = float("{:.3f}".format((max_val + min_val) * 0.5))
    
        # Set up the color map and normalization
        my_cmap = matplotlib.colormaps.get_cmap("coolwarm")
        norm = matplotlib.colors.Normalize(min_val, max_val)
    
        # Calculate die area and steps
        offsetX, offsetY = self.llx, self.lly
        LLX = float("{:.3f}".format(self.llx - offsetX))
        LLY = float("{:.3f}".format(self.lly - offsetY))
        URX = float("{:.3f}".format(self.urx - offsetX))
        URY = float("{:.3f}".format(self.ury - offsetY))
        Xsteps = np.linspace(LLX, URX, 10)
        Ysteps = np.linspace(LLY, URY, 10)
    
        # Plot each tile
        for tileKey, temp in self.dbDict[selectedLayer]["TILES"].items():
            coords = tileKey.split("_")
            llx = float(coords[0]) - offsetX
            lly = float(coords[1]) - offsetY
            urx = float(coords[2]) - offsetX
            ury = float(coords[3]) - offsetY
            width = urx - llx
            height = ury - lly
    
            # Determine the color for the tile
            color = my_cmap(norm(temp))
    
            # Highlight specific tiles if needed
            if tileKey in highlighted:
                rect = Rectangle((llx, lly), width, height, facecolor=color, edgecolor="yellow", linewidth=1)
            else:
                rect = Rectangle((llx, lly), width, height, facecolor=color)
    
            ax.add_patch(rect)
    
        # Add plot title and axis labels
        layer_maxT = float(self.__F2Sprecision(self.dbDict[selectedLayer]["FEATURES"]["MAXT"]["VAL"]))
        layer_Tgap = float(self.__F2Sprecision(self.dbDict[selectedLayer]["FEATURES"]["MAXT"]["VAL"] - self.dbDict[selectedLayer]["FEATURES"]["MINT"]["VAL"]))
        ax.set_title(f"Name: {dieName}\nLayer: {selectedLayer}, Max T: {layer_maxT}, Max deltaT: {layer_Tgap}")
        ax.set_xlabel("X Coordinate")
        ax.set_ylabel("Y Coordinate")
        ax.invert_yaxis()
        ax.set_xticks(Xsteps)
        ax.set_yticks(Ysteps)
    
        # Add color bar if requested
        if withColorBar:
            cax = fig.add_axes([ax.get_position().x1 + 0.02, ax.get_position().y0, 0.02, ax.get_position().height])
            cbar = fig.colorbar(matplotlib.cm.ScalarMappable(norm=norm, cmap=my_cmap), cax=cax,
                                ticks=[min_val, mid_val, max_val], extend="both")
            cbar.ax.set_yticklabels([f"<{min_val}", f"{mid_val}", f">{max_val}"], verticalalignment="center")
    
        # Show or save the plot
        if isShow:
            plt.show()
            return None
        else:
            imgPath = os.path.join(self.outputFolder, saveImg)
            plt.savefig(imgPath, bbox_inches="tight")
            plt.close(fig)
            return imgPath              


class TPCaseProcessing:
    def __init__(self, caseRoot):
        self.caseRoot = caseRoot
        self.caseFolders = []

        self.setupDict = {}   # save the data from input JSON conf.
    
    def __F2Sprecision(self, fval, prec=4):
        precStr= "{:."+str(prec)+"f}"
        return precStr.format(fval)
    
    def load_case_JSONFile(self, jsonConf_path):
        if not os.path.isfile(jsonConf_path):
            raise FileNotFoundError(f"[ERROR] JSON conf file {jsonConf_path} not found")
        
        # Load the JSON data
        with open(jsonConf_path, "r") as json_file:
            self.setupDict = json.load(json_file)
        
        folderCases = ["core"]

        sweepCases = self.setupDict["SWEEP"]
        caseCount = 1
        ### IID & UNION select one ###
        if "IID" in sweepCases.keys():
            ### IID, up to 2 list ###
            if len(sweepCases["IID"].keys()) == 1:
                for pi, p in enumerate(sweepCases["IID"].keys()):
                    ps = p.split(":")
                    for parai, param in enumerate(sweepCases["IID"][p]):
                        caseName = "_".join(["S"+str(caseCount), "P"+str(pi)+"_"+str(parai)])
                        folderCases.append(caseName)
                        caseCount += 1
            
            elif len(sweepCases["IID"].keys()) == 2:
                pass
            else:
                print("<ERROR> No support for IID list > 2")
        
        elif "UNION" in sweepCases.keys():
            ### length of sweeping point ###
            params = len(sweepCases["UNION"][list(sweepCases["UNION"].keys())[0]])
            for _id in range(params):
                _casename = []
                for pi, p in enumerate(sweepCases["UNION"].keys()):
                    _casename.append("P{}_{}".format(str(pi), str(_id)))
                
                caseName = "_".join(["S"+str(caseCount)]+["_".join(_casename)])
                folderCases.append(caseName)
                caseCount += 1
        
        for case in folderCases:
            runCaseFolder = os.path.join(os.path.join(self.caseRoot, case), "MAIN_et")
            self.caseFolders.append(runCaseFolder)
        
        print("<INFO> #CaseFolders: {}".format(len(self.caseFolders)))
    
    def Centroid_UC_deltaT_Space_eval(self, output_csv="saveDict.csv"):
        TPpath = os.path.join(self.caseFolders[0], "ThermalProfile_DIE.txt")
        
        ### Input parameters ###
        TotemTF = self.setupDict["CORE"]["TOTEMTF"]
        thermalTF = self.setupDict["CORE"]["THERMALTF"]["PATH"]
        TTFName = self.setupDict["CORE"]["THERMALTF"]["NAME"]
        resolution = self.setupDict["CORE"]["RESOLUTION"]
        designArea = self.setupDict["CORE"]["DESIGN_AREA"]["SIZE"]
        ambT = self.setupDict["CORE"]["AMBIENT_T"]
        HTCs = self.setupDict["CORE"]["HTC"]
        centerCellOffset = self.setupDict["CORE"]["POWER_CELL0"]["OFFSET"]
        cellSize = self.setupDict["CORE"]["POWER_CELL0"]["SIZE"]
        cellPower = self.setupDict["CORE"]["POWER_CELL0"]["POWER_VAL"]
        #########################

        ### R in K/W ###
        UCdisk = self.__F2Sprecision(float(cellSize[0])*0.5, prec=1)
        saveDict = {"Input":{"TotemTF":TotemTF, "ThermalTF":{"PATH":thermalTF, "Name":TTFName},
                             "Resolution":resolution, "DesignArea(um^2)":designArea, "BCs(W/m^2K)":{"RefT":ambT, "HTCs":HTCs}},\
                    "Output":{"TOPminT":0.0, "UC_power(mW)":cellPower, "UCTemp":0.0, "UCdisk(um)":UCdisk, "deltaT_top":0.0,\
                              "cellsTemp":[], "stepsDeltaT":["NaN"], "stepDeltaT":["NaN"], "Rdisk(um)":["NaN"],\
                              "ln(Rdisk/a)":["NaN"], "Rcond":["NaN"] },
                    "Calculated":{"BoundaryT":0.0, "R_BC":0.0, "deltaT_top":0.0}
                    }

        thermalView = RHSCETView(TPpath)
        selectedLayer = "Xtor"
        topLayer = "FSIC"
        cell_llx = centerCellOffset[0]
        cell_lly = centerCellOffset[1]
        cell_urx = cell_llx+cellSize[0]
        cell_ury = cell_lly+cellSize[1]
        counter = 0
        UCTemp = 0.0
        Rdisk = 0.0

        TOPminT = thermalView.getLayerTMin(selectedLayer=topLayer)
        saveDict["Output"]["TOPminT"] = TOPminT

        ### trun area into m^2 ###
        R_BC = 1/((float(HTCs[0])+float(HTCs[1]))*(float(designArea[0])*0.000001*float(designArea[1])*0.000001))
        R_BC = self.__F2Sprecision(R_BC, prec=4)
        ### T = R*Q + ambT ###
        boundaryT = (float(R_BC)*(float(cellPower)*0.001))+float(ambT)
        boundaryT = self.__F2Sprecision(boundaryT, prec=4)

        deltaT_top = float(TOPminT) - float(boundaryT)
        deltaT_top = self.__F2Sprecision(deltaT_top, prec=4)

        saveDict["Calculated"]["BoundaryT"] = boundaryT
        saveDict["Calculated"]["R_BC"] = R_BC
        saveDict["Calculated"]["deltaT_top"] = deltaT_top
        while True:
            MaxT, avgT, MinT, allT = thermalView.getLayerRegionalT(selectedLayer=selectedLayer, \
                                                    region=[cell_llx,cell_lly,cell_urx,cell_ury])
            #print(MaxT, avgT, MinT, allT)
            if counter == 0:
                UCTemp = self.__F2Sprecision(float(avgT))
                saveDict["Output"]["UCTemp"] = UCTemp
                saveDict["Output"]["cellsTemp"].append(UCTemp)
            else:
                stepDeltaT = float(saveDict["Output"]["cellsTemp"][-1])-float(avgT)
                deltaT = self.__F2Sprecision(float(UCTemp)-float(avgT))
                Rdisk += resolution
                ln = self.__F2Sprecision(np.log(float(Rdisk)/float(UCdisk)), prec=5)
                Rcond = self.__F2Sprecision(float(deltaT)/(float(ln)*(float(cellPower)*0.001)), prec=4)
                
                saveDict["Output"]["cellsTemp"].append(self.__F2Sprecision(float(avgT)))
                saveDict["Output"]["stepDeltaT"].append(self.__F2Sprecision(stepDeltaT))
                saveDict["Output"]["stepsDeltaT"].append(deltaT)
                saveDict["Output"]["Rdisk(um)"].append(Rdisk)
                saveDict["Output"]["ln(Rdisk/a)"].append(ln)
                saveDict["Output"]["Rcond"].append(Rcond)
            
            cell_llx = cell_llx - resolution
            cell_lly = cell_lly
            cell_urx = cell_llx + cellSize[0]
            cell_ury = cell_lly + cellSize[1]

            if cell_llx < 0:
                break
            
            counter += 1
        
        deltaT_top = float(saveDict["Output"]["cellsTemp"][-1]) - float(TOPminT)
        saveDict["Output"]["deltaT_top"] = self.__F2Sprecision(deltaT_top, prec=4)
        
        #print(saveDict)

        ### output saveDict to csv ###
        import pandas as pd

        # Find the length of the lists in Output (assume all lists are the same length)
        output_lists = {k: v for k, v in saveDict["Output"].items() if isinstance(v, list)}
        if not output_lists:
            raise ValueError("No list fields found in Output section.")

        n_rows = max(len(v) for v in output_lists.values())
        # Prepare rows
        rows = []
        for i in range(n_rows):
            row = {}
            # Add scalar values from Input and Calculated
            for section in ["Input", "Calculated"]:
                for k, v in saveDict[section].items():
                    row[f"{section}_{k}"] = v
            # Add list values from Output (use ith element), and scalar values
            for k, v in saveDict["Output"].items():
                if isinstance(v, list):
                    row[f"Output_{k}"] = v[i] if i < len(v) else None
                else:
                    row[f"Output_{k}"] = v
            rows.append(row)
        
        df = pd.DataFrame(rows)
        df.to_csv(output_csv, index=False)
        return df
    
    def Shift_UC_deltaT_eval(self, output_csv="saveDict.csv"):
        sweepCases = self.setupDict["SWEEP"]["UNION"]["POWER_CELL0:OFFSET"]

        copyDict = copy.deepcopy(self.setupDict)
        sweepDict = {}
        for i, cc in enumerate(sweepCases):
            caseName = self.caseFolders[i+1]
            sweepDict.setdefault(caseName, {})
            TPpath = os.path.join(caseName, "ThermalProfile_DIE.txt")
        
            ## sweeping parameter ###
            centerCellOffset = cc
        
            ### Input parameters ###
            TotemTF = copyDict["CORE"]["TOTEMTF"]
            thermalTF = copyDict["CORE"]["THERMALTF"]["PATH"]
            TTFName = copyDict["CORE"]["THERMALTF"]["NAME"]
            resolution = copyDict["CORE"]["RESOLUTION"]
            designArea = copyDict["CORE"]["DESIGN_AREA"]["SIZE"]
            ambT = copyDict["CORE"]["AMBIENT_T"]
            HTCs = copyDict["CORE"]["HTC"]
            cellSize = copyDict["CORE"]["POWER_CELL0"]["SIZE"]
            cellPower = copyDict["CORE"]["POWER_CELL0"]["POWER_VAL"]
            #########################

            ### R in K/W ###
            UCdisk = self.__F2Sprecision(float(cellSize[0])*0.5, prec=1)
            saveDict = {"Input":{"TotemTF":TotemTF, "ThermalTF":{"PATH":thermalTF, "Name":TTFName},\
                                 "Resolution":resolution, "DesignArea(um^2)":designArea,\
                                 "BCs(W/m^2K)":{"RefT":ambT, "HTCs":HTCs}},\
                        "Output":{"TOPminT":0.0, "UC_power(mW)":cellPower, "UCTemp":0.0,\
                                  "UCdisk(um)":UCdisk,\
                                  "L_cellsTemp":[], "L_stepsDeltaT":["NaN"], "L_stepDeltaT":["NaN"], "L_Rdisk(um)":["NaN"],\
                                  "L_ln(Rdisk/a)":["NaN"], "L_Rcond":["NaN"],\
                                  "R_cellsTemp":[], "R_stepsDeltaT":["NaN"], "R_stepDeltaT":["NaN"], "R_Rdisk(um)":["NaN"],\
                                  "R_ln(Rdisk/a)":["NaN"], "R_Rcond":["NaN"] },\
                        "Calculated":{"BoundaryT":0.0, "R_BC":0.0, "deltaT_top":0.0}
            }

            thermalView = RHSCETView(TPpath)
            selectedLayer = "Xtor"
            topLayer = "FSIC"
            
            cell_llx = centerCellOffset[0]
            cell_lly = centerCellOffset[1]
            cell_urx = cell_llx+cellSize[0]
            cell_ury = cell_lly+cellSize[1]
            counter = 0
            UCTemp = 0.0
            Rdisk = 0.0

            TOPminT = thermalView.getLayerTMin(selectedLayer=topLayer)
            saveDict["Output"]["TOPminT"] = TOPminT

            ### trun area into m^2 ###
            R_BC = 1/((float(HTCs[0])+float(HTCs[1]))*(float(designArea[0])*0.000001*float(designArea[1])*0.000001))
            R_BC = self.__F2Sprecision(R_BC, prec=4)
            ### T = R*Q + ambT ###
            boundaryT = (float(R_BC)*(float(cellPower)*0.001))+float(ambT)
            boundaryT = self.__F2Sprecision(boundaryT, prec=4)

            deltaT_top = float(TOPminT) - float(boundaryT)
            deltaT_top = self.__F2Sprecision(deltaT_top, prec=4)

            saveDict["Calculated"]["BoundaryT"] = boundaryT
            saveDict["Calculated"]["R_BC"] = R_BC
            saveDict["Calculated"]["deltaT_top"] = deltaT_top
            
            ### Left-side ###
            while True:
                MaxT, avgT, MinT, allT = thermalView.getLayerRegionalT(selectedLayer=selectedLayer, \
                                                    region=[cell_llx,cell_lly,cell_urx,cell_ury])
                #print(MaxT, avgT, MinT, allT)
                if counter == 0:
                    UCTemp = self.__F2Sprecision(float(avgT))
                    saveDict["Output"]["UCTemp"] = UCTemp
                    saveDict["Output"]["L_cellsTemp"].append(UCTemp)
                else:
                    stepDeltaT = float(saveDict["Output"]["L_cellsTemp"][-1])-float(avgT)
                    deltaT = self.__F2Sprecision(float(UCTemp)-float(avgT))
                    Rdisk += resolution
                    ln = self.__F2Sprecision(np.log(float(Rdisk)/float(UCdisk)), prec=5)
                    Rcond = self.__F2Sprecision(float(deltaT)/(float(ln)*(float(cellPower)*0.001)), prec=4)
                
                    saveDict["Output"]["L_cellsTemp"].append(self.__F2Sprecision(float(avgT)))
                    saveDict["Output"]["L_stepDeltaT"].append(self.__F2Sprecision(stepDeltaT))
                    saveDict["Output"]["L_stepsDeltaT"].append(deltaT)
                    saveDict["Output"]["L_Rdisk(um)"].append(Rdisk)
                    saveDict["Output"]["L_ln(Rdisk/a)"].append(ln)
                    saveDict["Output"]["L_Rcond"].append(Rcond)
            
                cell_llx = cell_llx - resolution
                cell_lly = cell_lly
                cell_urx = cell_llx + cellSize[0]
                cell_ury = cell_lly + cellSize[1]

                if cell_llx < 0:
                    break
            
                counter += 1
            
            ### reset ###
            cell_llx = centerCellOffset[0]
            cell_lly = centerCellOffset[1]
            cell_urx = cell_llx+cellSize[0]
            cell_ury = cell_lly+cellSize[1]
            counter = 0
            UCTemp = 0.0
            Rdisk = 0.0
            ### Right-side ###
            while True:
                MaxT, avgT, MinT, allT = thermalView.getLayerRegionalT(selectedLayer=selectedLayer, \
                                                    region=[cell_llx,cell_lly,cell_urx,cell_ury])
                #print(MaxT, avgT, MinT, allT)
                if counter == 0:
                    UCTemp = self.__F2Sprecision(float(avgT))
                    saveDict["Output"]["UCTemp"] = UCTemp
                    saveDict["Output"]["R_cellsTemp"].append(UCTemp)
                else:
                    stepDeltaT = float(saveDict["Output"]["R_cellsTemp"][-1])-float(avgT)
                    deltaT = self.__F2Sprecision(float(UCTemp)-float(avgT))
                    Rdisk += resolution
                    ln = self.__F2Sprecision(np.log(float(Rdisk)/float(UCdisk)), prec=5)
                    Rcond = self.__F2Sprecision(float(deltaT)/(float(ln)*(float(cellPower)*0.001)), prec=4)
                
                    saveDict["Output"]["R_cellsTemp"].append(self.__F2Sprecision(float(avgT)))
                    saveDict["Output"]["R_stepDeltaT"].append(self.__F2Sprecision(stepDeltaT))
                    saveDict["Output"]["R_stepsDeltaT"].append(deltaT)
                    saveDict["Output"]["R_Rdisk(um)"].append(Rdisk)
                    saveDict["Output"]["R_ln(Rdisk/a)"].append(ln)
                    saveDict["Output"]["R_Rcond"].append(Rcond)
            
                cell_llx = cell_llx + resolution
                cell_lly = cell_lly
                cell_urx = cell_llx + cellSize[0]
                cell_ury = cell_lly + cellSize[1]

                if cell_llx > int(designArea[0])-int(resolution):
                    break
            
                counter += 1
            
            sweepDict[caseName] = copy.deepcopy(saveDict)
        #print(saveDict)

        ### output saveDict to csv ###
        import pandas as pd

        # --- Flatten sweepDict into a DataFrame ---
        all_rows = []
        for caseName, saveDict in sweepDict.items():
            # Find the length of the lists in Output (assume all lists are the same length)
            output_lists = {k: v for k, v in saveDict["Output"].items() if isinstance(v, list)}
            n_rows = max(len(v) for v in output_lists.values()) if output_lists else 1

            for i in range(n_rows):
                row = {"CaseName": caseName}
                # Input group (flatten dicts)
                for k, v in saveDict["Input"].items():
                    if isinstance(v, dict):
                        for subk, subv in v.items():
                            row[("Input", f"{k}_{subk}")] = subv
                    else:
                        row[("Input", k)] = v
                # Output group (expand lists, repeat scalars)
                for k, v in saveDict["Output"].items():
                    if isinstance(v, list):
                        row[("Output", k)] = v[i] if i < len(v) else None
                    else:
                        row[("Output", k)] = v
                # Calculated group
                for k, v in saveDict["Calculated"].items():
                    row[("Calculated", k)] = v
                all_rows.append(row)

        # Create DataFrame with MultiIndex columns
        df = pd.DataFrame(all_rows)
        # Move 'CaseName' to the front and flatten columns for CSV
        cols = ['CaseName'] + [col for col in df.columns if col != 'CaseName']
        df = df[cols]
        df.columns = [col if isinstance(col, str) else "_".join(col) for col in df.columns]
        df.to_csv(output_csv, index=False)
        print(f"[INFO] Sweep results written to {output_csv}")
        return df



class TPPostProcessor:
    def __init__(self, thermal_profile_path):
        self.thermal_view = RHSCETView(thermal_profile_path)
        self.cellsList = []
        self.results = {}

        #print(self.thermal_view.dbDict["NPTAB"])
        #sys.exit(1)
    
    def __F2Sprecision(self, fval, prec=4):
        precStr= "{:."+str(prec)+"f}"
        return precStr.format(fval)
    
    def load_cell_file(self, cell_file_path):
        if not os.path.isfile(cell_file_path):
            raise FileNotFoundError(f"[ERROR] Cell file {cell_file_path} not found")
        
        with open(cell_file_path, "r") as cell_file:
            for i, line in enumerate(cell_file):
                # Skip the header
                if i == 0:
                    continue

                # Parse the cell line
                parts = line.strip().split(",")
                if len(parts) < 6:
                    print(f"[WARNING] Skipping malformed line {i + 1}: {line.strip()}")
                    continue
                
                inst_name, *_ = parts
                self.cellsList.append(inst_name)
        
        print("#HighPDCells: ", len(self.cellsList))


    def process_cellCSV_file(self, cellCSV_path, output_file_path, selected_layer="M0"):
        if not os.path.isfile(cellCSV_path):
            raise FileNotFoundError(f"[ERROR] Cell file {cellCSV_path} not found")

        with open(cellCSV_path, "r") as cell_file:
            for i, line in enumerate(cell_file):
                # Skip the header
                if i == 0:
                    continue

                # Parse the cell line
                parts = line.strip().split(",")
                if len(parts) < 6:
                    print(f"[WARNING] Skipping malformed line {i + 1}: {line.strip()}")
                    continue

                inst_name, cellType, llx, lly, urx, ury, pwr = parts

                if not(inst_name in self.cellsList):
                    continue

                region = [float(llx), float(lly), float(urx), float(ury)]

                # Get regional temperatures and tile locations from the thermal profile
                try:
                    max_t, avg_t, min_t, all_t = self.thermal_view.getLayerRegionalT(
                        selectedLayer=selected_layer, region=region
                    )
                    tile_locations = self._get_tile_locations(region)
                    
                    ## Area, Aspect_ratio -> H/W
                    area = (float(urx)-float(llx))*(float(ury)-float(lly))
                    area = self.__F2Sprecision(area, prec=4)

                    aspect_ratio = (float(urx)-float(llx))/(float(ury)-float(lly))
                    aspect_ratio = self.__F2Sprecision(aspect_ratio, prec=4)
                    
                    ## pd unit: mW/um^2 -> W/mm^2
                    pd = (float(pwr)/((float(urx)-float(llx))*(float(ury)-float(lly))))*1000
                    pd = self.__F2Sprecision(pd, prec=4)
                    
                    #print(max_t, avg_t, min_t, all_t)
                    #print(tile_locations)

                    self.results[inst_name] = {
                        "AREA": area,
                        "ASPECT_RATIO": aspect_ratio,
                        "PD": pd,
                        "MaxT": max_t,
                        "MinT": min_t,
                        "AvgT": avg_t,
                        "TileLocations": tile_locations,
                        "Temperatures": all_t,
                    }
                    self.cellsList.append(inst_name)
                
                except Exception as e:
                    print(f"[ERROR] Failed to process region {region} for {inst_name}: {e}")

        # Write results to the output file
        with open(output_file_path, "w") as output_file:
            json.dump(self.results, output_file, indent=4)

        print(f"[INFO] Results written to {output_file_path}")
        return self.results, output_file_path

    
    def _get_tile_locations(self, region):
        """
        Helper function to retrieve tile locations for a given region.
        """
        offsetX, offsetY = self.thermal_view.llx, self.thermal_view.lly
        _llx = region[0] + offsetX
        _lly = region[1] + offsetY
        _urx = region[2] + offsetX
        _ury = region[3] + offsetY

        _stepX = [step[1] for step in self.thermal_view.stepX]
        _stepY = [step[1] for step in self.thermal_view.stepY]

        rstepX = self.thermal_view._getTileSteps(_stepX, _llx, _urx)
        rstepY = self.thermal_view._getTileSteps(_stepY, _lly, _ury)

        tile_locations = []
        for _x in range(len(rstepX) - 1):
            for _y in range(len(rstepY) - 1):
                kllx = self.__F2Sprecision(float(rstepX[_x]), prec=4)
                klly = self.__F2Sprecision(float(rstepY[_y]), prec=4)
                kurx = self.__F2Sprecision(float(rstepX[_x + 1]), prec=4)
                kury = self.__F2Sprecision(float(rstepY[_y + 1]), prec=4)
                tile_locations.append(f"{kllx}_{klly}_{kurx}_{kury}")

        return tile_locations
    
    def plot_from_json(self, json_file_path, save_path=None, show_plot=False):
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle

        """
        Plots the tile locations and temperature data from the result JSON file.

        Parameters:
            json_file_path (str): Path to the JSON file containing the results.
            save_path (str, optional): Path to save the plot image. Defaults to None.
            show_plot (bool, optional): Whether to display the plot interactively. Defaults to True.
        """
        if not os.path.isfile(json_file_path):
            raise FileNotFoundError(f"[ERROR] JSON file {json_file_path} not found")

        # Load the JSON data
        with open(json_file_path, "r") as json_file:
            data = json.load(json_file)
        
        # Calculate the thermal profile size
        profile_width = self.thermal_view.urx - self.thermal_view.llx
        profile_height = self.thermal_view.ury - self.thermal_view.lly

        # Initialize the plot
        fig, ax = plt.subplots(figsize=(10, 10))
        ax.set_title("Tile Locations and Temperatures")
        ax.set_xlabel("X Coordinate")
        ax.set_ylabel("Y Coordinate")
        ax.invert_yaxis()

        # Initialize plot limits
        x_min, y_min, x_max, y_max = float("inf"), float("inf"), float("-inf"), float("-inf")
        Tmax, Tmin = float("-inf"), float("inf")

        # Plot each tile from the JSON data
        for inst_name, details in data.items():
            tile_locations = details["TileLocations"]
            temperatures = details["Temperatures"]

            for tile_key, temp in zip(tile_locations, temperatures):
                coords = tile_key.split("_")
                llx = float(coords[0])
                lly = float(coords[1])
                urx = float(coords[2])
                ury = float(coords[3])
                width = urx - llx
                height = ury - lly

                # Debugging: Print rectangle details
                #print(f"Tile: {tile_key}, llx: {llx}, lly: {lly}, urx: {urx}, ury: {ury}, width: {width}, height: {height}")
                
                # Update T
                Tmax = max(Tmax, float(temp))
                Tmin = min(Tmin, float(temp))

                # Skip invalid rectangles
                if width <= 0 or height <= 0:
                    print(f"[WARNING] Skipping invalid rectangle: {tile_key}")
                    continue
                
                # Determine the color based on temperature
                color = plt.cm.coolwarm(float(temp) / 100)  # Normalize temperature for colormap

                # Plot the tile
                rect = Rectangle((llx, lly), width, height, facecolor=color, edgecolor="black", linewidth=0.5)
                ax.add_patch(rect)

        # Set plot limits
        ax.set_xlim(self.thermal_view.llx, self.thermal_view.urx)
        ax.set_ylim(self.thermal_view.lly, self.thermal_view.ury)
        
        # Add color bar
        sm = plt.cm.ScalarMappable(cmap="coolwarm", norm=plt.Normalize(vmin=Tmin, vmax=Tmax))
        cbar = plt.colorbar(sm, ax=ax)
        cbar.set_label("Temperature (°C)")

        # Save or show the plot
        if save_path:
            plt.savefig(save_path, bbox_inches="tight")
            print(f"[INFO] Plot saved to {save_path}")
        
        if show_plot:
            plt.show()
        
        plt.close(fig)


def TPComparsion(tar1Json, tar2Json, output_csv="comparison_results.csv"):
    import csv
    """
    Compares two JSON results files from TPPostProcessor and calculates the temperature deltas.

    Parameters:
        tar1Json (str): Path to the first JSON results file.
        tar2Json (str): Path to the second JSON results file.
        output_csv (str): Path to save the comparison results in CSV format.

    Output:
        A CSV file with the following format:
        cell name, power density, target1_MaxT, target2_MaxT, delta_MaxT, target1_AvgT, target2_AvgT, delta_AvgT
    """
    if not os.path.isfile(tar1Json):
        raise FileNotFoundError(f"[ERROR] JSON file {tar1Json} not found")
    if not os.path.isfile(tar2Json):
        raise FileNotFoundError(f"[ERROR] JSON file {tar2Json} not found")

    # Load JSON data
    with open(tar1Json, "r") as file1, open(tar2Json, "r") as file2:
        data1 = json.load(file1)
        data2 = json.load(file2)

    # Open CSV file for writing
    with open(output_csv, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        # Write header
        writer.writerow(["Cell Name", "Area", "Aspect_Ratio", "PD", "Target1_MaxT", "Target2_MaxT", "Delta_MaxT",
                         "Target1_AvgT", "Target2_AvgT", "Delta_AvgT"])

        # Compare data
        for cell_name in data1.keys():
            if cell_name in data2:
                area = data1[cell_name]["AREA"]
                aspect_ratio = data1[cell_name]["ASPECT_RATIO"]
                PD = data1[cell_name]["PD"]
                # Extract MaxT and AvgT for both targets
                target1_MaxT = float(data1[cell_name]["MaxT"])
                target2_MaxT = float(data2[cell_name]["MaxT"])
                delta_MaxT = target2_MaxT - target1_MaxT

                target1_AvgT = float(data1[cell_name]["AvgT"])
                target2_AvgT = float(data2[cell_name]["AvgT"])
                delta_AvgT = target2_AvgT - target1_AvgT

                # Write to CSV
                writer.writerow([cell_name, area, aspect_ratio, PD, target1_MaxT, target2_MaxT, delta_MaxT,
                                 target1_AvgT, target2_AvgT, delta_AvgT])

    print(f"[INFO] Comparison results written to {output_csv}")




if __name__ == "__main__":
    ## python FCpowermap.py --fc_powermap=./thermal_case.csv

    #args = arg().parse_args()
    #FCpowermap2RHSCETmhs(args.fc_powermap, args.outputFolder, args.outputName)

    #designArea = [0, 0, 48, 48]
    #FCipf2RHSCETmhs(args.fc_powermap, args.outputFolder, args.outputName, designArea)

    #ipfPath = "./pwd.mhs"
    #plotIPF(ipfPath)

    ## Example 1 usage
    #profile = "./ThermalProfile_DIE_exp.txt"
    #ETThermalView = RHSCETView(profile)
    #MaxT, avgT, MinT, allT = ETThermalView.getLayerRegionalT(region=[0,0,10,10])
    #print(MaxT, avgT, allT, MinT)
    #ETThermalView.plot(isShow=True)

    """
    ## Example 2 usage
    # "./TProfile_DIE_0410.txt", "./TProfile_DIE_7b7.txt"
    thermal_profile_path = "./TProfile_DIE_0410.txt"  # Replace with your thermal profile file path
    cell_file_path = "./highPDCells.txt"  # Replace with your cell file path
    output_file_path = "./output_results.json"  # Replace with your desired output file path

    processor = TPPostProcessor(thermal_profile_path)
    postResults, output_file_path = processor.process_cell_file(cell_file_path, output_file_path, selected_layer="NPTAB")

    processor.plot_from_json(json_file_path=output_file_path, save_path="tile_plot.png")
    """

    """
    ## Example 3
    thermal_profile_path_org = "./org/ThermalProfile_DIE.txt"
    cell_file_path = "./highPDCells.csv"
    cellCSV_path = "./cell_0410_org.csv"
    output_file_path = "./output_results_org.json"  # Replace with your desired output file path

    processor_org = TPPostProcessor(thermal_profile_path_org)
    processor_org.load_cell_file(cell_file_path)
    postResults, output_file_path = processor_org.process_cellCSV_file(cellCSV_path, output_file_path, selected_layer="NPTAB")
    print(len(postResults.keys()))


    thermal_profile_path_PGA = "./PGA/ThermalProfile_DIE.txt"
    cell_file_path = "./highPDCells.csv"
    cellCSV_path = "./cell_0410_PGA.csv"
    output_file_path = "./output_results_PGA.json"  # Replace with your desired output file path

    processor_PGA = TPPostProcessor(thermal_profile_path_org)
    processor_PGA.load_cell_file(cell_file_path)
    postResults, output_file_path = processor_PGA.process_cellCSV_file(cellCSV_path, output_file_path, selected_layer="NPTAB")
    print(len(postResults.keys()))

    TPComparsion(
    tar1Json="./output_results_org.json",
    tar2Json="./output_results_PGA.json",
    output_csv="comparison_results.csv")
    """

    ## Example 4 
    caseRoot = "./UPTR_p1278_m14_13b13_r1"
    JSONconf = "./UPTR_p1278_m14_13b13_r1.json"

    TPCase = TPCaseProcessing(caseRoot)
    TPCase.load_case_JSONFile(JSONconf)
    
    print(TPCase.caseFolders)
    #TPCase.Centroid_UC_deltaT_Space_eval()
    TPCase.Shift_UC_deltaT_eval()

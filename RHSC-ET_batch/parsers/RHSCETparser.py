import os
import sys
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
        if not os.path.isfile(self.profilePath):
            print("[ERROR] {} path not found".format(self.profilePath))
            return
    
        _stepX, _stepY = {}, {}
        with open(self.profilePath, "r") as fid:
            for i, ll in enumerate(fid):
                ll = ll.split("\n")[0]
                diearea = re.match(r"^# DIE.* ([-+]?\d*\.?\d+) ([-+]?\d*\.?\d+) ([-+]?\d*\.?\d+) ([-+]?\d*\.?\d+).*", ll)
                tile = re.match(r"^# TILE.* (\d+) (\d+).*", ll)
                layers = re.match(r"^# LAYER (\d+) (.*)", ll)
                scale = re.match(r"^# SCALE_FACTOR (\d*\.?\d+).*", ll)
                entries = re.match(r"^[0-9].*", ll)

                if diearea:
                    self.llx, self.lly = float(diearea.group(1)), float(diearea.group(2))
                    self.urx, self.ury = float(diearea.group(3)), float(diearea.group(4))
                
                if tile:
                    self.tileX, self.tileY = int(tile.group(1)), int(tile.group(2))
                
                if layers:
                    self.layers = int(layers.group(1))
                    for ly in layers.group(2).split():
                        self.layerList.append(ly)
                        self.dbDict.setdefault(ly, {"TILES":{}, "FEATURES":{"MAXT":{"VAL":-100000, "KEY":None},\
                                                                            "MINT":{"VAL":100000, "KEY":None} }})
                    ### check ###
                    if len(self.layerList) == self.layers:
                        pass
                    else:
                        print("<ERROR> layer numbers not match")
                
                if scale:
                    self.scale_factor = float(scale.group(1))
                
                if entries:
                    lls = ll.split()
                    tid = lls[0]
                    llx, lly, urx, ury = lls[1:5]
                    key = "_".join([llx, lly, urx, ury])
                    self.tileKeys.append(key)

                    _stepX.setdefault(llx, float(llx))
                    _stepX.setdefault(urx, float(urx))
                    _stepY.setdefault(lly, float(lly))
                    _stepY.setdefault(ury, float(ury))
                    #print(llx, lly, urx, ury)
                    if self.layerList is None:
                        print("<ERROR> layer not set")
                        return 

                    for i, ly in enumerate(self.layerList):
                        tVal = float(lls[5+i])
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
                    
                    #sys.exit(1)
        
        self.stepX = sorted([[i, _stepX[i]] for i in _stepX.keys()], key=lambda x:x[1])
        self.stepY = sorted([[i, _stepY[i]] for i in _stepY.keys()], key=lambda x:x[1])
        #self.stepX = sorted(list(set(self.stepX)))
        #self.stepY = sorted(list(set(self.stepY)))
        
        #print(self.llx, self.lly, self.urx, self.ury, self.tileX, self.tileY)
        #print(self.layers, self.layerList)
    
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
        ### The region is design region, not the ET coordination ###
        offsetX = self.llx
        offsetY = self.lly
        dieWidth = self.urx - self.llx
        dieHeight = self.ury - self.lly
        resolution = dieWidth/self.tileX

        _llx = region[0]+offsetX
        _lly = region[1]+offsetY
        _urx = region[2]+offsetX
        _ury = region[3]+offsetY

        #print(self.stepX)
        #print(self.stepY)
        #print(_llx, _lly, _urx, _ury, resolution)

        _stepX = [_i[1] for _i in self.stepX]
        _stepY = [_i[1] for _i in self.stepY]
        
        rstepX, rstepY = [], []
        star = _llx
        while star < _urx:
            _id = np.argmin(np.absolute(np.array(_stepX)-star))
            rstepX.append(self.stepX[_id][0])
            star += resolution
        _id = np.argmin(np.absolute(np.array(_stepX)-star))
        rstepX.append(self.stepX[_id][0])
        
        dbDict = self.dbDict[selectedLayer]["TILES"]
        star = _lly
        while star < _ury:
            _id = np.argmin(np.absolute(np.array(_stepY)-star))
            rstepY.append(self.stepY[_id][0])
            star += resolution
        _id = np.argmin(np.absolute(np.array(_stepY)-star))
        rstepY.append(self.stepY[_id][0])
        
        #print(rstepX, rstepY)
        allT = []
        MaxT = -100000
        MinT = 100000
        avgT = 0.0
        for _x in range(len(rstepX)-1):
            for _y in range(len(rstepY)-1):
                _key = "_".join([rstepX[_x], rstepY[_y], rstepX[_x+1], rstepY[_y+1]])
                #print(_key)
                tt = dbDict[_key]
                allT.append(self.__F2Sprecision(tt, prec=3))
                avgT += tt
                if tt > MaxT:
                    MaxT = tt
                
                if tt < MinT:
                    MinT = tt
                #print(tt, dbDict[_key])
        
        ### to string ###
        MaxT = self.__F2Sprecision(MaxT, prec=3)
        MinT = self.__F2Sprecision(MinT, prec=3)
        avgT = self.__F2Sprecision(avgT/len(allT), prec=3)
        
        return MaxT, avgT, MinT, allT

    
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

        if min_val is not None:
            min_val = float("{:.3f}".format(float(min_val)))
        else:
            min_val = float(self.__F2Sprecision(self.dbDict[selectedLayer]["FEATURES"]["MINT"]["VAL"]))
        
        if max_val is not None:
            max_val = float("{:.3f}".format(float(max_val)))
        else:
            max_val = float(self.__F2Sprecision(self.dbDict[selectedLayer]["FEATURES"]["MAXT"]["VAL"]))
        
        mid_val = float("{:.3f}".format((max_val+min_val)*0.5))
        my_cmap = matplotlib.colormaps.get_cmap("coolwarm")
        norm = matplotlib.colors.Normalize(min_val, max_val)

        offsetX = self.llx
        offsetY = self.lly
        LLX = float("{:.3f}".format(self.llx-offsetX))
        LLY = float("{:.3f}".format(self.lly-offsetY))
        URX = float("{:.3f}".format(self.urx-offsetX))
        URY = float("{:.3f}".format(self.ury-offsetY))
        AreaX = math.ceil(self.urx-self.llx)
        AreaY = math.ceil(self.ury-self.lly)
        Xsteps = np.linspace(LLX, URX, 10)
        Ysteps = np.linspace(LLY, URY, 10)

        #pixels = np.zeros((AreaX+1, AreaY+1))
        pixels = np.zeros((1, 1))
        
        for i in self.dbDict[selectedLayer]["TILES"].keys():
            coords = i.split("_")
            val = float(self.dbDict[selectedLayer]["TILES"][i])
            color_i = my_cmap(norm(val))
            llx = float(coords[0])-offsetX
            lly = float(coords[1])-offsetY
            urx = float(coords[2])-offsetX
            ury = float(coords[3])-offsetY
            width = float(self.__F2Sprecision(urx-llx))
            length = float(self.__F2Sprecision(ury-lly))

            if i in highlighted:
                rect = Rectangle((llx, lly), width, length, facecolor=color_i, edgecolor="yellow", linewidth=1)
            else:
                rect = Rectangle((llx, lly), width, length, color=color_i)

            ax.add_patch(rect)

        #xi = 20
        #color_i = my_cmap(norm(xi))
        #print(color_i)
        #rect = Rectangle((1, 1), 2, 2, color=color_i)
        #ax.add_patch(rect)

        #cax = ax.imshow(pixels, vmin=min_val, vmax=max_val, cmap="coolwarm")
        im = ax.imshow(pixels, vmin=min_val, vmax=max_val, cmap="coolwarm")
        layer_maxT = float(self.__F2Sprecision(self.dbDict[selectedLayer]["FEATURES"]["MAXT"]["VAL"]))
        layer_Tgap = float(self.__F2Sprecision(self.dbDict[selectedLayer]["FEATURES"]["MAXT"]["VAL"]-self.dbDict[selectedLayer]["FEATURES"]["MINT"]["VAL"]))
        ax.set_title("Name: {}\nLayer: {}, Max T: {}, Max deltaT: {}".format(dieName, selectedLayer, layer_maxT, layer_Tgap))
        ax.invert_yaxis()
        ax.set_xticks(Xsteps)
        ax.set_yticks(Ysteps)
        
        ## Add colorbar, make sure to specify tick locations to match desired ticklabels ##
        if withColorBar:
            cax = fig.add_axes([ax.get_position().x1+0.02, ax.get_position().y0, 0.02, ax.get_position().height])
            cbar = fig.colorbar(im, cax=cax, ticks=[min_val, mid_val, max_val],
                                format=mticker.FixedFormatter(["<{}".format(min_val), "{}".format(mid_val), ">{}".format(max_val)]), extend="both")
            labels = cbar.ax.get_yticklabels()
            labels[0].set_verticalalignment("top")
            labels[-1].set_verticalalignment("bottom")


        """
        if withColorBar:
            cbar = fig.colorbar(cax, ticks=[min_val, mid_val, max_val],
                                format=mticker.FixedFormatter(["<{}".format(min_val), "{}".format(mid_val), ">{}".format(max_val)]))
                                #extend="both")
            labels = cbar.ax.get_yticklabels()
            labels[0].set_verticalalignment("top")
            labels[-1].set_verticalalignment("bottom")
        """

        if isShow:
            plt.show()
            return None
        else:
            imgPath = os.path.join(self.outputFolder, saveImg)
            plt.savefig(imgPath, bbox_inches="tight")
            plt.close(fig)
            return imgPath
                    


if __name__ == "__main__":
    ## python FCpowermap.py --fc_powermap=./thermal_case.csv

    #args = arg().parse_args()
    #FCpowermap2RHSCETmhs(args.fc_powermap, args.outputFolder, args.outputName)

    #designArea = [0, 0, 48, 48]
    #FCipf2RHSCETmhs(args.fc_powermap, args.outputFolder, args.outputName, designArea)

    #ipfPath = "./pwd.mhs"
    #plotIPF(ipfPath)

    profile = "./ThermalProfile_DIE.txt"

    ETThermalView = RHSCETView(profile)
    MaxT, avgT, MinT, allT = ETThermalView.getLayerRegionalT(region=[0,0,10,10])
    print(MaxT, avgT, allT, MinT)

    #ETThermalView.plot(isShow=True)
    
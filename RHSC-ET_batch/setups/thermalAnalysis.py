import os
import sys
import shutil
import numpy as np
import re
import math
import argparse
import copy

class powerThermalAnalysis:
    def __init__(self, powerView, ETresultView, resolution, outputFolder="./"):
        self.powerView = powerView
        self.ETresultView = ETresultView
        self.resolution = resolution
        self.outputFolder = outputFolder

        self.llx = self.ETresultView.llx
        self.lly = self.ETresultView.lly
        self.urx = self.ETresultView.urx
        self.ury = self.ETresultView.ury

        ### stepX/Y = [["key",float(key)], ...]
        self.stepX = self.ETresultView.stepX
        self.stepY = self.ETresultView.stepY
        ### stepXYDict = {"key":stepXY_index}
        self.stepXDict, self.stepYDict = {}, {}

        self.minGradient = 100000
        self.maxGradient = -100000

        self.corrDict = {}
        for _k in self.ETresultView.dbDict[list(self.ETresultView.dbDict.keys())[0]]["TILES"].keys():
            self.corrDict.setdefault(_k, {})

        self.__assignPowerTiles()
    
    def __F2Sprecision(self, fval, prec=4):
        precStr= "{:."+str(prec)+"f}"
        return precStr.format(fval)
    
    def __assignPowerTiles(self):
        pwrView = self.powerView.tileDict[self.resolution]
        _stepX = [_i[1] for _i in self.stepX]
        _stepY = [_i[1] for _i in self.stepY]
        for i, k in enumerate(self.stepX):
            self.stepXDict.setdefault(k[0], i)
        for i, k in enumerate(self.stepY):
            self.stepYDict.setdefault(k[0], i)

        for i in pwrView.keys():
            _llxID = np.argmin(np.absolute(np.array(_stepX)-pwrView[i]["llx"]))
            _llyID = np.argmin(np.absolute(np.array(_stepY)-pwrView[i]["lly"]))
            _urxID = np.argmin(np.absolute(np.array(_stepX)-pwrView[i]["urx"]))
            _uryID = np.argmin(np.absolute(np.array(_stepY)-pwrView[i]["ury"]))
            _key = "_".join([self.stepX[_llxID][0], self.stepY[_llyID][0], self.stepX[_urxID][0], self.stepY[_uryID][0]])
            #print(_key)
            self.corrDict[_key]["power"] = pwrView[i]["PWR"]
            #print(pwrView[i], _key, self.corrDict[_key]["power"])
            #sys.exit(1)
        
        #print(len(pwrView.keys()))
        #_count = 0
        #for i in self.corrDict.keys():
        #    if "power" in self.corrDict[i].keys():
        #        _count += 1
        #print(_count)
    
    def outputCorrDict(self, layer, outputName="corr.data"):
        Tlayer = "T@{}".format(layer)
        Glayer = "grad@{}".format(layer)
        #print(self.stepX, self.stepY, self.corrDict)
        temperature, pwr, gradient = [], [], []
        for yi in reversed(range(len(self.stepY)-1)):
            _tt, _pp, _gg = [], [], []
            for xi in range(len(self.stepX)-1):
                llx = self.stepX[xi][0]
                lly = self.stepY[yi][0]
                urx = self.stepX[xi+1][0]
                ury = self.stepY[yi+1][0]
                _Txy = "_".join([llx, lly, urx, ury])
                #print(_Txy)
                #Txy = self.corrDict[_Txy][Tlayer]
                _p = self.__F2Sprecision(self.corrDict[_Txy]["power"], 6)
                _t = self.__F2Sprecision(self.corrDict[_Txy][Tlayer], 3)
                _g = self.__F2Sprecision(self.corrDict[_Txy][Glayer], 3)
                _pp.append(_p)
                _tt.append(_t)
                _gg.append(_g)
            
            temperature.append(",".join(_tt))
            pwr.append(",".join(_pp))
            gradient.append(",".join(_gg))
        
        #print(temperature, pwr, gradient)
        outStr = ["Layer: {}".format(layer),\
                  "Resolution: {}".format(str(self.resolution)),\
                  "Area: {},{},{},{}".format(str(self.llx), str(self.lly), str(self.urx), str(self.ury)),\
                  "StepX: {}".format(",".join([x[0] for x in self.stepX])),\
                  "StepY: {}".format(",".join([y[0] for y in self.stepY]))]
        
        outStr.append("Power:")
        outStr.append("\n".join(pwr))
        outStr.append("Temperature:")
        outStr.append("\n".join(temperature))
        outStr.append("Gradient:")
        outStr.append("\n".join(gradient))

        save2 = os.path.join(self.outputFolder, outputName)
        with open(save2, "w") as fid:
            fid.write("\n".join(outStr))


    def calNegLaplacianOperator(self, layer):
        Tlayer = "T@{}".format(layer)
        Glayer = "grad@{}".format(layer)
        unit = 1
        kernal = np.array([[0, -1, 0],[-1, 4, -1],[0, -1, 0]])
        #kernal = np.array([[-1, -1, -1],[-1, 8, -1],[-1, -1, -1]])

        ETView = self.ETresultView.dbDict[layer]["TILES"]
        sumConv = 0.0
        for i in ETView.keys():
            self.corrDict[i][Tlayer] = ETView[i]
        
        _pwrs, _grad = [], []
        for tile in self.corrDict.keys():
            pwr = self.corrDict[tile]["power"]
            coords = tile.split("_")
            llx, lly, urx, ury = coords[0:]
            llxid = self.stepXDict[llx]
            llyid = self.stepYDict[lly]
            urxid = self.stepXDict[urx]
            uryid = self.stepYDict[ury]
            rangMinX = llxid-unit
            rangMaxX = urxid+unit
            rangMinY = llyid-unit
            rangMaxY = uryid+unit

            ### === with boundary === ###
            local = []
            _Txy = "_".join([self.stepX[llxid][0], self.stepY[llyid][0], self.stepX[urxid][0], self.stepY[uryid][0]])
            Txy = self.corrDict[_Txy][Tlayer]
            for _y in range(rangMinY, rangMaxY):
                if _y < 0:
                    local.append([Txy, Txy, Txy])
                    continue
                if _y > len(self.stepYDict.keys())-2:
                    local.append([Txy, Txy, Txy])
                    continue
                
                _local = []
                for _x in range(rangMinX, rangMaxX):
                    if _x < 0:
                        _local.append(Txy)
                        continue
                    if _x > len(self.stepXDict.keys())-2:
                        _local.append(Txy)
                        continue
                    
                    #print(_x, _y)
                    _tile = "_".join([self.stepX[_x][0], self.stepY[_y][0], self.stepX[_x+1][0], self.stepY[_y+1][0]])
                    #print(_tile)
                    _local.append(self.corrDict[_tile][Tlayer])
                
                local.append(_local)
            
            local = np.array(local)
            conv = (kernal*local).sum()
            #print(local, conv)
            conv = float(self.__F2Sprecision(conv, prec=4))
            ### === with boundary === ###

            ### === w/o boundary === ###
            """
            if rangMinX < 0:
                rangMinX = 0
            if rangMinY < 0:
                rangMinY = 0
            if rangMaxX > len(self.stepXDict.keys())-1:
                rangMaxX = len(self.stepXDict.keys())-1
            if rangMaxY > len(self.stepYDict.keys())-1:
                rangMaxY = len(self.stepYDict.keys())-1

            local = []
            count = 0
            for _y in range(rangMinY, rangMaxY):
                _local = []
                for _x in range(rangMinX, rangMaxX):
                    _tile = "_".join([self.stepX[_x][0], self.stepY[_y][0], self.stepX[_x+1][0], self.stepY[_y+1][0]])
                    _local.append(self.corrDict[_tile][Tlayer])
                    count += 1
                
                local.append(_local)
            
            ### ignore boundary cells ###
            if count < 9:
                conv = 0
            else:
                local = np.array(local)
                conv = (kernal*local).sum()
                conv = float(self.__F2Sprecision(conv, prec=4))
            """
            ### === w/o boundary === ###
            
            self.corrDict[tile][Glayer] = conv
            sumConv += conv

            #if llxid > 0 and llxid < len(self.stepXDict.keys())-1:
            #    if llyid > 0 and llyid < len(self.stepYDict.keys())-1:
            _pwrs.append(pwr)
            _grad.append(conv)
            
            if self.minGradient > conv:
                self.minGradient = conv
            if self.maxGradient < conv:
                self.maxGradient = conv
            
            #print(tile, local)
            #sys.exit(1)
        
        sumConv = float(self.__F2Sprecision(sumConv, prec=4))
        R = np.corrcoef(np.array([_pwrs, _grad]))
        corr = float(self.__F2Sprecision(R[0][1], 2))
        print("Min Grad: {}, Max Grad: {}, Sum: {}, R: {}".format(self.minGradient, self.maxGradient, sumConv, corr))
        
        """
        ### filter output ###
        selected = []
        midGradient = (self.minGradient+self.maxGradient)*0.3
        sumPartialGrad = 0.0
        for i in self.corrDict.keys():
            if self.corrDict[i]["gradient"] > midGradient:
                print(i, self.corrDict[i]["gradient"])
                selected.append(i)
                sumPartialGrad += self.corrDict[i]["gradient"]
        
        totalPwr = 25.5
        unitPwr = float(self.__F2Sprecision(totalPwr/sumPartialGrad, 3))
        print(unitPwr)
        for i in selected:
            newPwr = float(self.__F2Sprecision(self.corrDict[i]["gradient"]*unitPwr, 3))
            print(i, newPwr)
        """

    def calProfileCorr(self, layer, unit=3):
        Tlayer = "layer@{}".format(layer)
        corrUnit = "corr@{}".format(unit)
        ETView = self.ETresultView.dbDict[layer]["TILES"]
        for i in ETView.keys():
            self.corrDict[i][Tlayer] = ETView[i]
        
        for tile in self.corrDict.keys():
            _pwrs, _thermals = [], []
            coords = tile.split("_")
            llx, lly, urx, ury = coords[0:]
            llxid = self.stepXDict[llx]
            llyid = self.stepYDict[lly]
            urxid = self.stepXDict[urx]
            uryid = self.stepYDict[ury]
            rangMinX = llxid-unit
            rangMaxX = urxid+unit
            rangMinY = llyid-unit
            rangMaxY = uryid+unit
            if rangMinX < 0:
                rangMinX = 0
            if rangMinY < 0:
                rangMinY = 0
            if rangMaxX > len(self.stepXDict.keys())-1:
                rangMaxX = len(self.stepXDict.keys())-1
            if rangMaxY > len(self.stepYDict.keys())-1:
                rangMaxY = len(self.stepYDict.keys())-1
            
            #print(self.stepXDict.keys())
            #print(coords, llx, lly, urx, ury)
            #print(llxid, llyid, urxid, uryid)
            #print(rangMinX, rangMaxX, rangMinY, rangMaxY)
            #sys.exit(1)

            for _x in range(rangMinX, rangMaxX):
                for _y in range(rangMinY, rangMaxY):
                    _tile = "_".join([self.stepX[_x][0], self.stepY[_y][0], self.stepX[_x+1][0], self.stepY[_y+1][0]])
                    _pwrs.append(self.corrDict[_tile]["power"])
                    _thermals.append(self.corrDict[_tile][Tlayer])
            
            r1 = np.corrcoef(np.array([_pwrs, _thermals]))
            #print(r1, np.array([_pwrs, _thermals]))
            #print(_pwrs, _thermals)
            #sys.exit(1)
            self.corrDict[tile][corrUnit] = r1[0][1]

    def gradPlot(self, layer, \
                 highlighted=[], saveImg="gradient.png", isShow=False):
        import matplotlib
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle

        import numpy as np
        import matplotlib.cm as cm
        import matplotlib.ticker as mticker
        
        Glayer = "grad@{}".format(layer)
        fig, ax = plt.subplots(1, 1, figsize=[8, 8])

        #rng = np.random.default_rng(seed=1900000)
        #data = rng.standard_normal((10, 5))
        #print(data)

        min_val = self.minGradient
        max_val = self.maxGradient
        mid_val = float("{:.3f}".format((max_val+min_val)*0.5))
        my_cmap = matplotlib.colormaps.get_cmap("seismic")
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
        
        for i in self.corrDict.keys():
            coords = i.split("_")
            val = float(self.corrDict[i][Glayer])

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

        im = ax.imshow(pixels, vmin=min_val, vmax=max_val, cmap="seismic")
        
        #layer_maxT = float(self.__F2Sprecision(self.dbDict[selectedLayer]["FEATURES"]["MAXT"]["VAL"]))
        #layer_Tgap = float(self.__F2Sprecision(self.dbDict[selectedLayer]["FEATURES"]["MAXT"]["VAL"]-self.dbDict[selectedLayer]["FEATURES"]["MINT"]["VAL"]))
        #ax.set_title("Name: {}\nLayer: {}, Max T: {}, Max deltaT: {}".format(dieName, selectedLayer, layer_maxT, layer_Tgap))
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
    



if __name__ == "__main__":
    pass
    
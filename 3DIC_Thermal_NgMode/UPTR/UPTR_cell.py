import os
import sys
import math
import copy
import json
import numpy as np

from collections import namedtuple

#from parsers import RHSCETparser


UPTR_PRESETUP = {
    "CELL": {
        "ReCore": {
            "XRANGE": [0.05, 0.2],
            "OUTFACTOR": 1.0,
            "TYPE": "LOG",
            "COEFFICIENT": [82888, 988988]
        },
        "ReMiddle": {
            "XRANGE": [0.2, 0.4],
            "TYPE": "LINEAR",
            "COEFFICIENT": [45955, 843534],
        },
        "ReOuter": {
            "XRANGE": [0.4, 2.0],
            "OUTFACTOR": 1.0,
            "TYPE": "LINEAR",
            "COEFFICIENT": [4893, 860048],
        }
    }
}


def ReBC(dArea, topHTC, botHTC, sideHTC=0, prec=4):
    dArea = dArea*0.000001*0.000001
    precStr= "{:."+str(prec)+"f}"
    re = 1/((float(topHTC)+float(botHTC)+float(sideHTC))*dArea)
    re = float(precStr.format(re))

    return re

def ReXtor2FSIC(dArea, thickness, Kvalue, prec=4):
    ## thickness (um), dArea (um^2) ==> 1/um
    ## K (W/(Km))
    precStr= "{:."+str(prec)+"f}"
    re = (float(thickness)*1000000)/(float(Kvalue)*float(dArea))
    re = float(precStr.format(re))

    return re


class UPTRCell:
    def __init__(self, resolution, extendArea=[40, 20]):
        ### 18A: resolution = [0.05, 0.16] //[site_column, site_row]
        self.extendArea = extendArea   ## in resolution unit
        self.resolution = resolution

        self.INDX = 40
        self.INDY = 20

        self.UPTReval = {
            "CORE": {
                "Rdisk": [],
                "Re": []
            }
        }

        # Create a grid array based on designArea and resolution
        self.gridX = np.arange(0, self.extendArea[0], 1)
        self.gridY = np.arange(0, self.extendArea[1], 1)

        ### self.grid as index ###
        self.grid = np.array(np.meshgrid(self.gridX, self.gridY)).T.reshape(-1, 2)
        
        # Initialize gridDeltaT with grid rectangles and zero deltaT
        self.gridDeltaT = [
            [g[0], g[1], g[0]+1, g[1]+1, 0.0]
            for g in self.grid
        ]

        # grid temperature ###
        self.gridTemp = [
            [g[0], g[1], g[0]+1, g[1]+1, 0.0]
            for g in self.grid
        ]
        #print(self.gridX, self.gridY, self.grid, self.grid.shape)
        
        self.totalPower = 0.0   ### in mW
    
    def __F2Sprecision(self, fval, prec=4):
        precStr= "{:."+str(prec)+"f}"
        return precStr.format(fval)

    def UPTRCore(self):
        def linear_fit(x1, y1, x2, y2):
            a = (y2-y1)/(x2-x1)
            b = y1 - (a*x1)
            return lambda x:(a*x)+b
        
        def log_fit(x1, y1, x2, y2):
            a = (y2-y1)/(np.log(x2)-np.log(x1))
            b = y1 - (a*np.log(x1))
            return lambda x:(a*np.log(x))+b

        UPTReval = {
            "CORE": {
                "Rdisk": [],
                "Re": []
            },
            "MIDDLE": {
                "Rdisk": [],
                "Re": []
            },
            "OUTER": {
                "Rdisk": [],
                "Re": []
            }
        }

        siteCol = self.resolution[0]
        siteRow = self.resolution[1]

        setupDict = UPTR_PRESETUP["CELL"]

        
        rdisk_list = list(range(1, self.INDX, 1))
        for xid in rdisk_list:
            xx = xid*siteCol
            xx = float(self.__F2Sprecision(xx, prec=2))

            if xx >= setupDict["ReCore"]["XRANGE"][0] and xx <= setupDict["ReCore"]["XRANGE"][1]:
                if setupDict["ReCore"]["TYPE"] == "LOG":
                    ReCore = np.log(xx)*setupDict["ReCore"]["COEFFICIENT"][0]+setupDict["ReCore"]["COEFFICIENT"][1]
                    ReCore = float(self.__F2Sprecision(ReCore, prec=4))
                
                UPTReval["CORE"]["Rdisk"].append(xx)
                UPTReval["CORE"]["Re"].append(ReCore)
            
            elif xx > setupDict["ReMiddle"]["XRANGE"][0] and xx <= setupDict["ReMiddle"]["XRANGE"][1]:
                if setupDict["ReMiddle"]["TYPE"] == "LINEAR":
                    ReCore = xx*setupDict["ReMiddle"]["COEFFICIENT"][0]+setupDict["ReMiddle"]["COEFFICIENT"][1]
                    ReCore = float(self.__F2Sprecision(ReCore, prec=4))
                
                UPTReval["MIDDLE"]["Rdisk"].append(xx)
                UPTReval["MIDDLE"]["Re"].append(ReCore)
            
            else:
                if setupDict["ReOuter"]["TYPE"] == "LINEAR":
                    ReCore = xx*setupDict["ReOuter"]["COEFFICIENT"][0]+setupDict["ReOuter"]["COEFFICIENT"][1]
                    ReCore = float(self.__F2Sprecision(ReCore, prec=4))
                
                UPTReval["OUTER"]["Rdisk"].append(xx)
                UPTReval["OUTER"]["Re"].append(ReCore)
        
        # Concatenate Rdisk and Re from CORE, MIDDLE, OUTER
        Rdisk = (
            UPTReval["CORE"]["Rdisk"] +
            UPTReval["MIDDLE"]["Rdisk"] +
            UPTReval["OUTER"]["Rdisk"]
        )
        Re = (
            UPTReval["CORE"]["Re"] +
            UPTReval["MIDDLE"]["Re"] +
            UPTReval["OUTER"]["Re"]
        )
        print("[INFO]\nRdisk: {}\nRe: {}".format(Rdisk, Re))

        self.UPTReval["CORE"]["Rdisk"] = Rdisk
        self.UPTReval["CORE"]["Re"] = Re
        
        return Rdisk, Re
    
    
    def deltaTMatrix(self, UCpower, UCloc):
        ## UCpower in mW, UCloc in [x_um, y_um]
        def interpolateRe(UCloc, grid, Rdisk, Re):
            # Calculate the distance from grid to the UCloc
            distX = (grid[0]-UCloc[0])*self.resolution[0]
            distY = (grid[1]-UCloc[1])*self.resolution[1]
            UCdisk = math.sqrt((distX) ** 2 + (distY) ** 2)
            UCdisk = float(self.__F2Sprecision(UCdisk, prec=4))

            # Interpolate Re value for the given UCdisk
            if Rdisk and Re:
                if UCdisk <= Rdisk[0]:
                    interp_Re = Re[0]
                elif UCdisk >= Rdisk[-1]:
                    interp_Re = Re[-1]
                else:
                    interp_Re = np.interp(UCdisk, Rdisk, Re)
                    interp_Re = float(self.__F2Sprecision(interp_Re, prec=4))
                #print(f"[INFO] Interpolated Re at UCloc {UCloc} (UCdisk={UCdisk:.2f}): {interp_Re}")
            else:
                interp_Re = None
                #print(f"[WARN] No Rdisk/Re data available for UCloc {UCloc}")
            
            return UCdisk, interp_Re


        #print("<INFO> UC located at [{}, {}]".format(UCloc[0], UCloc[1]))
        Rdisk = self.UPTReval["CORE"]["Rdisk"]
        Re = self.UPTReval["CORE"]["Re"]

        ReBound = Re[-1]
        for i, g in enumerate(self.grid):
            rdisk, re = interpolateRe(UCloc, g, Rdisk, Re)

            gridDeltaT = (ReBound-re)*UCpower*0.001
            gridDeltaT = float(self.__F2Sprecision(gridDeltaT, prec=4))
            if rdisk < 0.0001:
                gridDeltaT = ReBound*UCpower*0.001
                
            self.gridDeltaT[i][4] += gridDeltaT
        
        self.totalPower += UCpower
    
    def estimatedCellDeltaT(self, cellSize, cellPower):
        # Calculate the center position for the cell
        center_x = self.extendArea[0] // 2
        center_y = self.extendArea[1] // 2

        # Calculate the lower-left corner to center the cell
        llx = center_x - cellSize[0] // 2
        lly = center_y - cellSize[1] // 2

        # Generate all grid locations covered by the cell
        UClocs = []
        for dx in range(cellSize[0]):
            for dy in range(cellSize[1]):
                UClocs.append([llx + dx, lly + dy])

        # Calculate the uniform power per grid cell
        ucpower = cellPower / (cellSize[0] * cellSize[1])
        UCpowers = [ucpower] * len(UClocs)

        # Optionally, run deltaTMatrix for each cell
        for i, ucl in enumerate(UClocs):
            self.deltaTMatrix(UCpowers[i], ucl)

        self.plotGridTempMatrix(type="DeltaT", show_plot=True)
    

    def gridTemperature(self):
        dArea = self.designArea[0]*self.designArea[1]
        topHTC = self.HTCs[0]
        botHTC = self.HTCs[1]
        sideHTC = self.HTCs[2]
         
        reBC = ReBC(dArea, topHTC, botHTC, sideHTC)
        reXtor2FSIC = ReXtor2FSIC(dArea, self.Xtor2FSIC, self.KzXtor2FSIC)

        TreBC = self.totalPower*0.001*reBC
        TreXtor2FSIC = self.totalPower*0.001*reXtor2FSIC
        for i, g in enumerate(self.grid):
            gridDeltaT = self.gridDeltaT[i][4]
            
            gridTemp = gridDeltaT + TreBC + TreXtor2FSIC + self.ambT
            gridTemp = float(self.__F2Sprecision(gridTemp, prec=2))

            self.gridTemp[i][4] = gridTemp


    def plotRe(self,
               Res, Rdisks,
               groups=[["CELL", "o", "blue"]], 
               save_path=None, show_plot=False):
        ### Res: [[Re_1], [Re_2], ...], Rdisks: [[Rdisk_1], [Rdisk_2], ...] ###
        ### groups: [("CORE", "o", "blue"), ...]
        
        import matplotlib.pyplot as plt

        # Concatenate Rdisk and Re from CENTER, MEDIUM, PERIPHERY
        fig = plt.figure(figsize=(8, 5))
        for idx, (group, marker, color) in enumerate(groups):
            Rdisk = Rdisks[idx]
            Re = Res[idx]
            
            if Rdisk and Re:
                plt.plot(Rdisk, Re, marker=marker, color=color, linestyle='-', label=group)
                # Label the group at the last point
                plt.text(Rdisk[-1], Re[-1], f" {group}", color=color, fontsize=10, verticalalignment='bottom')

        plt.xlabel("Rdisk(um)")
        plt.ylabel("Re(K/W)")
        plt.title("Rdisk vs. Re")
        plt.grid(True)
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, bbox_inches="tight")
            print(f"[INFO] Plot saved to {save_path}")
        
        if show_plot:
            plt.show()

        plt.close(fig)
    
    def plotGridTempMatrix(self, type="DeltaT", save_path=None, show_plot=False, 
                           label="deltaT (K)"):
        import matplotlib.pyplot as plt
        import numpy as np
    
        if not self.gridDeltaT:
            print("[WARN] gridDeltaT is empty. Run deltaTMatrix first.")
            return
    
        # Convert to numpy array for easier handling
        if type == "DeltaT":
            arr = np.array(self.gridDeltaT)  # shape: (N, 5)
        elif type == "Temp":
            arr = np.array(self.gridTemp)
        else:
            arr = np.array(self.gridDeltaT)  # shape: (N, 5)
        
        # Get unique sorted x and y coordinates
        x_vals = np.unique(arr[:, 0])
        y_vals = np.unique(arr[:, 1])
        #print(x_vals, y_vals)
    
        # Build a 2D array for deltaT
        deltaT_matrix = np.full((len(y_vals), len(x_vals)), np.nan)
        for row in arr:
            llx, lly, urx, ury, deltaT = row
            ix = np.where(x_vals == llx)[0][0]
            iy = np.where(y_vals == lly)[0][0]
            deltaT_matrix[iy, ix] = deltaT
    
        fig, ax = plt.subplots(figsize=(8, 6))
        # Convert grid indices to physical coordinates using resolution
        x_vals_phys = x_vals * self.resolution[0]
        y_vals_phys = y_vals * self.resolution[1]
        im = ax.imshow(
            deltaT_matrix,
            origin='lower',
            extent=(x_vals_phys[0], x_vals_phys[-1]+self.resolution[0], 
                    y_vals_phys[0], y_vals_phys[-1]+self.resolution[1]),
            aspect='equal',
            cmap='jet'
        )
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label(label)
        ax.set_xlabel("X (um)")
        ax.set_ylabel("Y (um)")
        ax.set_title("Grid {} Matrix (imshow)".format(label))
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, bbox_inches="tight")
            print(f"[INFO] Grid {label} matrix plot saved to {save_path}")
        if show_plot:
            plt.show()
        plt.close(fig)



class UPTRTable:
    def __init__(self, designArea, HTCs, ambT, resolution):
        self.designArea = designArea
        self.radiusX = self.designArea[0]*0.5
        self.radiusY = self.designArea[1]*0.5

        self.rangeFactor = 0.33

        if self.radiusX > self.radiusY:
            self.aspectRatio = self.radiusY/self.radiusX
        else:
            self.aspectRatio = self.radiusX/self.radiusY
        
        self.HTCs = HTCs
        self.ambT = ambT
        self.resolution = resolution

        self.UPTReval = {
            "CORE": {
                "Rdisk": [],
                "Re": []
            }
        }

        # Create a grid array based on designArea and resolution
        self.gridX = np.arange(0, self.designArea[0], self.resolution)
        self.gridY = np.arange(0, self.designArea[1], self.resolution)
        ### self.grid as index ###
        self.grid = np.array(np.meshgrid(self.gridX, self.gridY)).T.reshape(-1, 2)
        
        # Initialize gridDeltaT with grid rectangles and zero deltaT
        self.gridDeltaT = [
            [g[0], g[1], g[0] + self.resolution, g[1] + self.resolution, 0.0]
            for g in self.grid
        ]

        # grid temperature ###
        self.gridTemp = [
            [g[0], g[1], g[0] + self.resolution, g[1] + self.resolution, 0.0]
            for g in self.grid
        ]
        #print(self.gridX, self.gridY, self.grid, self.grid.shape)
        
        self.totalPower = 0.0   ### in mW

        ### process values (in um): ToDo -> read thermal TF ###
        self.Xtor2FSIC = 2.24
        self.KzXtor2FSIC = 1.7
        
        #sys.exit(1)
    
    def __F2Sprecision(self, fval, prec=4):
        precStr= "{:."+str(prec)+"f}"
        return precStr.format(fval)
    
    def initUPTR(self):
        ### aspect ratio close to 1 ###
        if self.aspectRatio >= 0.8:
            if self.radiusX > self.radiusY:
                Rdisk = self.radiusX
            else:
                Rdisk = self.radiusY
            
            Rdisk, Re = self.UPTRCore(Rdisk)
        
        elif self.aspectRation > 0.4 and self.aspectRatio < 0.8:
            pass
        else:
            pass
        
        self.UPTReval["CORE"]["Rdisk"] = Rdisk
        self.UPTReval["CORE"]["Re"] = Re

    

    def UPTRCore(self, Rdisk):
        def linear_fit(x1, y1, x2, y2):
            a = (y2-y1)/(x2-x1)
            b = y1 - (a*x1)
            return lambda x:(a*x)+b
        
        def log_fit(x1, y1, x2, y2):
            a = (y2-y1)/(np.log(x2)-np.log(x1))
            b = y1 - (a*np.log(x1))
            return lambda x:(a*np.log(x))+b

        UPTReval = {
            "CENTER": {
                "Rdisk": [],
                "Re": []
            },
            "MEDIUM": {
                "Rdisk": [],
                "Re": []
            },
            "PERIPHERY": {
                "Rdisk": [],
                "Re": []
            }
        }

        Rdisk_1 = Rdisk*self.rangeFactor
        Rdisk_2 = Rdisk*(1-self.rangeFactor)

        rdisk_1_list = list(range(1, int(Rdisk_1) + 1))
        rdisk_mid_list = list(range(int(Rdisk_1), int(Rdisk_2) + 1))
        rdisk_2_list = list(range(int(Rdisk_2), int(Rdisk) + 1))

        ### TODO: NEED to consider resolution ###
        setupDict = UPTR_PRESETUP["CELL"]["CENTER"]
        #########################################

        if setupDict["ReBound"]["TYPE"] == "LINEAR":
            ReBound = Rdisk*setupDict["ReBound"]["COEFFICIENT"][0]+setupDict["ReBound"]["COEFFICIENT"][1]
            
        ### determine ReG1 point value ###
        ReG2 = ReBound*(1-setupDict["ReG2"]["FACTOR"])
        ### fitting the values from ReG2 to ReBound ###
        if setupDict["ReG2"]["FITTING"] == "LINEAR":
            fitted_func = linear_fit(rdisk_2_list[0], ReG2, rdisk_2_list[-1], ReBound)
            
        for i, x in enumerate(rdisk_2_list):
            if i == 0:
                continue

            fitval = fitted_func(x)
            fitval = float(self.__F2Sprecision(fitval, prec=4))
            UPTReval["PERIPHERY"]["Rdisk"].append(x)
            UPTReval["PERIPHERY"]["Re"].append(fitval)
            
        ### fitting the values in CENTER ###
        for x in rdisk_1_list:
            if setupDict["ReCore"]["TYPE"] == "LOG":
                ReCore = np.log(x)*setupDict["ReCore"]["COEFFICIENT"][0]+setupDict["ReCore"]["COEFFICIENT"][1]
                ReCore = float(self.__F2Sprecision(ReCore, prec=4))

            UPTReval["CENTER"]["Rdisk"].append(x)
            UPTReval["CENTER"]["Re"].append(ReCore)

        ### determine ReG1 point value ###
        #ReG1 = ReG2*(1-setupDict["ReG1"]["FACTOR"])
        ReG1 = UPTReval["CENTER"]["Re"][-1]
            
        ### fitting the values from ReG1 to ReG2 ###
        if setupDict["ReG1"]["FITTING"] == "LOG":
            fitted_func = log_fit(rdisk_mid_list[0], ReG1, rdisk_mid_list[-1], ReG2)
            
        for i, x in enumerate(rdisk_mid_list):
            if i == 0:
                continue

            fitval = fitted_func(x)
            fitval = float(self.__F2Sprecision(fitval, prec=4))
            UPTReval["MEDIUM"]["Rdisk"].append(x)
            UPTReval["MEDIUM"]["Re"].append(fitval)
        
        # Concatenate Rdisk and Re from CENTER, MEDIUM, PERIPHERY
        Rdisk = (
            UPTReval["CENTER"]["Rdisk"] +
            UPTReval["MEDIUM"]["Rdisk"] +
            UPTReval["PERIPHERY"]["Rdisk"]
        )
        Re = (
            UPTReval["CENTER"]["Re"] +
            UPTReval["MEDIUM"]["Re"] +
            UPTReval["PERIPHERY"]["Re"]
        )
        print("[INFO]\nRdisk: {}\nRe: {}".format(Rdisk, Re))
        
        return Rdisk, Re


    def UPTRoffCenter(self, UCloc):
        # Calculate the maximum and minimum distance from UCloc to any corner of the design area
        corners = [
            (0, 0),
            (self.designArea[0], 0),
            (0, self.designArea[1]),
            (self.designArea[0], self.designArea[1])
        ]
        distances = [math.hypot(UCloc[0] - x, UCloc[1] - y) for x, y in corners]
        min_dist = math.floor(min(distances))
        max_dist = math.ceil(max(distances))

        #if min_dist < 3:
        #    pass

        Rdisk, Re = self.UPTRCore(max_dist)
        
        ReBound = Re[-1]

        return Rdisk, Re, ReBound
    
    
    def deltaTMatrix(self, UCpower, UCloc):
        ## UCpower in mW, UCloc in [x_um, y_um]
        # Classify UCdiskX and UCdiskY into stages for X and Y directions
        def classify_stage(disk, radius):
            stage1 = radius * self.rangeFactor
            stage2 = radius * self.rangeFactor * 2
            if disk <= stage1:
                return 1
            elif disk <= stage2:
                return 2
            else:
                return 3
        
        def interpolateRe(UCloc, grid, Rdisk, Re):
            # Calculate the distance from grid to the UCloc
            UCdisk = math.sqrt((grid[0] - UCloc[0]) ** 2 + (grid[1] - UCloc[1]) ** 2)
            UCdisk = float(self.__F2Sprecision(UCdisk, prec=4))

            # Interpolate Re value for the given UCdisk
            if Rdisk and Re:
                if UCdisk <= Rdisk[0]:
                    interp_Re = Re[0]
                elif UCdisk >= Rdisk[-1]:
                    interp_Re = Re[-1]
                else:
                    interp_Re = np.interp(UCdisk, Rdisk, Re)
                    interp_Re = float(self.__F2Sprecision(interp_Re, prec=4))
                #print(f"[INFO] Interpolated Re at UCloc {UCloc} (UCdisk={UCdisk:.2f}): {interp_Re}")
            else:
                interp_Re = None
                #print(f"[WARN] No Rdisk/Re data available for UCloc {UCloc}")
            
            return UCdisk, interp_Re

        
        UCdiskX = abs(UCloc[0]-self.radiusX)
        UCdiskY = abs(UCloc[1]-self.radiusY)

        stageX = classify_stage(UCdiskX, self.radiusX)
        stageY = classify_stage(UCdiskY, self.radiusY)
        #print(f"[INFO] UCdiskX stage: {stageX}, UCdiskY stage: {stageY}")

        ### CENTER ###
        if stageX == 1 and stageY == 1:
            print("[INFO] UC located at CENTER")
            Rdisk = self.UPTReval["CORE"]["Rdisk"]
            Re = self.UPTReval["CORE"]["Re"]

            ReBound = Re[-1]
            for i, g in enumerate(self.grid):
                rdisk, re = interpolateRe(UCloc, g, Rdisk, Re)
                #print(g, rdisk, re, UCloc)

                gridDeltaT = (ReBound-re)*UCpower*0.001
                gridDeltaT = float(self.__F2Sprecision(gridDeltaT, prec=2))
                if rdisk < 0.0001:
                    gridDeltaT = ReBound*UCpower*0.001
                
                self.gridDeltaT[i][4] += gridDeltaT
                #self.gridDeltaT.append([g[0], g[1], g[0]+self.resolution, g[1]+self.resolution, gridDeltaT])
        
        ### MEDIUM ###
        if stageX == 2 or stageY == 2:
            Rdisk, Re, ReBound = self.UPTRoffCenter(UCloc)
            for i, g in enumerate(self.grid):
                rdisk, re = interpolateRe(UCloc, g, Rdisk, Re)

                gridDeltaT = (ReBound-re)*UCpower*0.001
                gridDeltaT = float(self.__F2Sprecision(gridDeltaT, prec=2))

                if rdisk < 0.0001:
                    gridDeltaT = ReBound*UCpower*0.001
                
                self.gridDeltaT[i][4] += gridDeltaT
        
        ### PERIPHERY ###
        if stageX == 3 or stageY == 3:
            Rdisk, Re, ReBound = self.UPTRoffCenter(UCloc)
            for i, g in enumerate(self.grid):
                rdisk, re = interpolateRe(UCloc, g, Rdisk, Re)

                gridDeltaT = (ReBound-re)*UCpower*0.001
                gridDeltaT = float(self.__F2Sprecision(gridDeltaT, prec=2))

                if rdisk < 0.0001:
                    gridDeltaT = ReBound*UCpower*0.001
                
                self.gridDeltaT[i][4] += gridDeltaT
        
        self.totalPower += UCpower


    def gridTemperature(self):
        dArea = self.designArea[0]*self.designArea[1]
        topHTC = self.HTCs[0]
        botHTC = self.HTCs[1]
        sideHTC = self.HTCs[2]
         
        reBC = ReBC(dArea, topHTC, botHTC, sideHTC)
        reXtor2FSIC = ReXtor2FSIC(dArea, self.Xtor2FSIC, self.KzXtor2FSIC)

        TreBC = self.totalPower*0.001*reBC
        TreXtor2FSIC = self.totalPower*0.001*reXtor2FSIC
        for i, g in enumerate(self.grid):
            gridDeltaT = self.gridDeltaT[i][4]
            
            gridTemp = gridDeltaT + TreBC + TreXtor2FSIC + self.ambT
            gridTemp = float(self.__F2Sprecision(gridTemp, prec=2))

            self.gridTemp[i][4] = gridTemp

    
    def plotRe(self,
               Res, Rdisks,
               groups, 
               save_path=None, show_plot=False):
        ### Res: [[Re_1], [Re_2], ...], Rdisks: [[Rdisk_1], [Rdisk_2], ...] ###
        ### groups: [("CORE", "o", "blue"), ...]
        
        import matplotlib.pyplot as plt

        # Concatenate Rdisk and Re from CENTER, MEDIUM, PERIPHERY
        fig = plt.figure(figsize=(8, 5))
        for idx, (group, marker, color) in enumerate(groups):
            Rdisk = Rdisks[idx]
            Re = Res[idx]
            
            if Rdisk and Re:
                plt.plot(Rdisk, Re, marker=marker, color=color, linestyle='-', label=group)
                # Label the group at the last point
                plt.text(Rdisk[-1], Re[-1], f" {group}", color=color, fontsize=10, verticalalignment='bottom')

        plt.xlabel("Rdisk(um)")
        plt.ylabel("Re(K/W)")
        plt.title("Rdisk vs. Re")
        plt.grid(True)
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, bbox_inches="tight")
            print(f"[INFO] Plot saved to {save_path}")
        
        if show_plot:
            plt.show()

        plt.close(fig)
    
    
    def plotGridTempMatrix(self, type="DeltaT", save_path=None, show_plot=False, 
                           label="deltaT (K)"):
        import matplotlib.pyplot as plt
        import numpy as np
    
        if not self.gridDeltaT:
            print("[WARN] gridDeltaT is empty. Run deltaTMatrix first.")
            return
    
        # Convert to numpy array for easier handling
        if type == "DeltaT":
            arr = np.array(self.gridDeltaT)  # shape: (N, 5)
        elif type == "Temp":
            arr = np.array(self.gridTemp)
        else:
            arr = np.array(self.gridDeltaT)  # shape: (N, 5)
        
        # Get unique sorted x and y coordinates
        x_vals = np.unique(arr[:, 0])
        y_vals = np.unique(arr[:, 1])
        #print(x_vals, y_vals)
    
        # Build a 2D array for deltaT
        deltaT_matrix = np.full((len(y_vals), len(x_vals)), np.nan)
        for row in arr:
            llx, lly, urx, ury, deltaT = row
            ix = np.where(x_vals == llx)[0][0]
            iy = np.where(y_vals == lly)[0][0]
            deltaT_matrix[iy, ix] = deltaT
    
        fig, ax = plt.subplots(figsize=(8, 6))
        im = ax.imshow(
            deltaT_matrix,
            origin='lower',
            extent=(x_vals[0], x_vals[-1]+self.resolution, y_vals[0], y_vals[-1]+self.resolution),
            aspect='equal',
            cmap='jet'
        )
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label(label)
        ax.set_xlabel("X (um)")
        ax.set_ylabel("Y (um)")
        ax.set_title("Grid {} Matrix (imshow)".format(label))
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, bbox_inches="tight")
            print(f"[INFO] Grid {label} matrix plot saved to {save_path}")
        if show_plot:
            plt.show()
        plt.close(fig)


    """ plot using rect patches 
    def plotGridDeltaTMatrix(self, save_path=None, show_plot=False):
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches

        if not self.gridDeltaT:
            print("[WARN] gridDeltaT is empty. Run deltaTMatrix first.")
            return
        
        # Extract all deltaT values for color normalization
        deltaT_vals = [item[4] for item in self.gridDeltaT]
        vmin = min(deltaT_vals)
        vmax = max(deltaT_vals)

        fig, ax = plt.subplots(figsize=(8, 6))
        cmap = plt.get_cmap('jet')
        norm = plt.Normalize(vmin=vmin, vmax=vmax)

        for item in self.gridDeltaT:
            llx, lly, urx, ury, deltaT = item
            width = urx - llx
            height = ury - lly
            color = cmap(norm(deltaT))
            rect = patches.Rectangle((llx, lly), width, height, linewidth=0, edgecolor=None, facecolor=color)
            ax.add_patch(rect)

        ax.set_xlim(min([item[0] for item in self.gridDeltaT]), max([item[2] for item in self.gridDeltaT]))
        ax.set_ylim(min([item[1] for item in self.gridDeltaT]), max([item[3] for item in self.gridDeltaT]))
        ax.set_xlabel("X (um)")
        ax.set_ylabel("Y (um)")
        ax.set_title("Grid deltaT Matrix")
        ax.set_aspect('equal')

        # Add colorbar
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax)
        cbar.set_label("deltaT (K)")

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, bbox_inches="tight")
            print(f"[INFO] Grid deltaT matrix plot saved to {save_path}")
        
        if show_plot:
            plt.show()

        plt.close(fig)
    """


def GentestCase(outputFolder, # (str) Path to the folder where generated test case JSON files will be saved
                genCases,     # (int) Number of test cases to generate
                numPowerSource, # (int) Number of power sources (cells) per test case
                powerRange,     # (tuple/list of 2 floats) Min and max power value for each power source (e.g., [0.1, 2.0])
                powerLocRange,  # (tuple/list of 2 lists) Ranges for x and y coordinates of power sources (e.g., [[0, 18], [0, 18]])
                totalPowerLimit=10,
                outputRuncsh="runCases.csh",
                totemTF="/nfs/site/disks/x5e2d_gwa_chienchi_001/TechFiles/Totem-EM/fake1278_m14_woBULK.tech",
                thermalTF="/nfs/site/disks/x5e2d_gwa_chienchi_001/TechFiles/thermalTF/TF_thermal/Intel/p1278_m14_woBULK.xml",
                thermalTFName="p1278_m14_woBULK", 
                resolution=1, designArea=[19,19], BCs=[10000,100,0], ambT=25):
    
    """
    Generate randomized thermal simulation test cases and save them as JSON files.
    This function creates a specified number of test cases for thermal analysis, each with a given number of power sources
    randomly placed within a defined area. Power values and locations are randomized within provided ranges, and the total
    power is scaled if it exceeds a specified limit. Each test case is saved as a JSON file in the output folder, and a
    summary dictionary for all cases is returned.
    Args:
        outputFolder (str): Directory to save generated JSON test case files.
        genCases (int): Number of test cases to generate.
        numPowerSource (int): Number of power sources (cells) per test case.
        powerRange (list or tuple): [min, max] power value for each source (in mW).
        powerLocRange (list or tuple): [[min_x, max_x], [min_y, max_y]] location range for sources.
        totalPowerLimit (float, optional): Maximum total power allowed per test case. Default is 10.
    Returns:
        dict: A dictionary where each key is a test case name (e.g., "testcase_1") and each value is a summary dictionary
              containing design area, HTC values, resolution, power values, and locations for each power source.
    Side Effects:
        - Creates the output folder if it does not exist.
        - Writes one JSON file per test case in the output folder.
        - Prints info messages for each generated file.
    """
 
    import random

    templateJSON = {
        "//COMMENT1": "Power: mW, distance: um, HTC: W/(K-m^2), Power_density: W/m^2",
        "CORE": {
            "TOTEMTF": totemTF,
            "LAYERMAP": None,
            "THERMALTF": {
                "PATH": thermalTF,
                "NAME": thermalTFName
            },
            "RESOLUTION": resolution,
            "DESIGN_AREA": {
                "SIZE": designArea
            },
            "METAL_DENSITY_MODEL": "TYPICAL",
            "AMBIENT_T": ambT,
            "HTC": BCs
        },
        "METAL_DENSITY_LIBRARY": {
            "TYPICAL": {
                "METAL": {
                    "0": {
                    "LAYERS": "GLOBAL",
                    "DENSITY": 100.0 }
                },
                "VIA": {
                    "0": {
                    "LAYERS": "GLOBAL",
                    "DENSITY": 100.0 }
                } 
            } 
        } 
    }

    os.makedirs(outputFolder, exist_ok=True)

    testCases = {}
    runScript = ["#!/bin/csh -h","source /nfs/site/disks/x5e2d_gwa_chienchi_001/Tools/myPy3.12/bin/activate.csh"]
    runETs = []
    for case_idx in range(genCases):
        caseJSON = json.loads(json.dumps(templateJSON))  # deep copy
        core_dict = caseJSON["CORE"]

        # Generate power sources
        ### limit the size to [1, 1] ###
        used_offsets = set()
        for i in range(numPowerSource):
            # Ensure unique [llx, lly] for each power cell
            while True:
                llx = int(round(random.uniform(powerLocRange[0][0], powerLocRange[0][1])))
                lly = int(round(random.uniform(powerLocRange[1][0], powerLocRange[1][1])))
                offset = (llx, lly)
                if offset not in used_offsets:
                    used_offsets.add(offset)
                    break
            
            pw = round(random.uniform(powerRange[0], powerRange[1]), 4)
            power_cell = {
                "SIZE": [1, 1],
                "POWER_VAL": pw,
                "OFFSET": [llx, lly]
            }
            core_dict[f"POWER_CELL_{i}"] = power_cell
        
        # Optionally, add a default POWER_CELL as well (if needed)
        # core_dict["POWER_CELL"] = {"SIZE": [1, 1], "POWER_VAL": 0.1, "OFFSET": [6, 6]}

        # Ensure total power does not exceed totalPowerLimit
        power_keys = [k for k in core_dict if k.startswith("POWER_CELL_")]
        total_power = sum(core_dict[k]["POWER_VAL"] for k in power_keys)
        if total_power > totalPowerLimit and total_power > 0:
            scale = totalPowerLimit / total_power
            for k in power_keys:
                core_dict[k]["POWER_VAL"] = round(core_dict[k]["POWER_VAL"] * scale, 4)
        
        # Generate caseDict for deltaTMatrix
        caseDict = {
            "ET": "",
            "designArea": core_dict["DESIGN_AREA"]["SIZE"],
            "HTCs": core_dict["HTC"],
            "resolution": core_dict["RESOLUTION"],
            "ambT": core_dict["AMBIENT_T"],
            "UCpowers": [],
            "UClocs": []
        }
        for k in core_dict:
            if k.startswith("POWER_CELL_"):
                cell = core_dict[k]
                # Center location of the power cell
                x = cell["OFFSET"][0]
                y = cell["OFFSET"][1]
                caseDict["UCpowers"].append(cell["POWER_VAL"])
                caseDict["UClocs"].append([x, y])
        
        testCases[f"TC_{case_idx+1}"] = caseDict

        # Write JSON file
        json_path = os.path.join(outputFolder, f"TC_{case_idx+1}.json")
        with open(json_path, "w") as f:
            json.dump(caseJSON, f, indent=2)
        print(f"[INFO] Generated {json_path}")

        runET = os.path.join(outputFolder, f"ET_{case_idx+1}")
        runcsh = "python NgBatchMode.py --JSON={} --caseFolder={}".format(json_path, runET)

        runScript.append(runcsh)
        runETs.append(runET)

        testCases[f"TC_{case_idx+1}"]["ET"] = runET
    

    # Write caseDict to caseSetup.json in the outputFolder
    caseSetup_path = os.path.join(outputFolder, "caseSetup.json")
    with open(caseSetup_path, "w") as f:
        json.dump(testCases, f, indent=2)
    print(f"[INFO] Generated {caseSetup_path}")
    
    # Write runScript to outputRuncsh in the outputFolder
    outputRuncsh_path = os.path.join(outputFolder, outputRuncsh)
    with open(outputRuncsh_path, "w") as f:
        f.write("\n".join(runScript) + "\n")
    print(f"[INFO] Run script saved to {outputRuncsh_path}")

    # Write ET folders to cases_path in the outputFolder
    cases_path = os.path.join(outputFolder, "ETcases.txt")
    with open(cases_path, "w") as f:
        f.write("\n".join(runETs) + "\n")
    print(f"[INFO] Run script saved to {cases_path}")
    
    return caseSetup_path, outputRuncsh_path, cases_path


def ETvsUPTRTable_1DIE(outputFolder, caseSetup_path, selectedLayer="Xtor",
                       compareResult_path="result.json"):
    def F2Sprecision(fval, prec=4):
        precStr= "{:."+str(prec)+"f}"
        return precStr.format(fval)
    
    os.makedirs(outputFolder, exist_ok=True)

    with open(caseSetup_path, "r") as f:
        case_dict = json.load(f)

    uptr_tables = {}
    for case_name, case in case_dict.items():
        designArea = case["designArea"]
        HTCs = case["HTCs"]
        resolution = case["resolution"]
        ambT = case["ambT"]
        
        uptr = UPTRTable(designArea, HTCs, ambT, resolution)
        uptr.initUPTR()
        uptr_tables[case_name] = {"UPTR": uptr, "MISMATCH": None, "ET": None, \
                                  "UPTR_PLOT_PATH": None, "MISMATCH_PLOT_PATH": None, "ET_PLOT_PATH": None}

        UCpowers = case["UCpowers"]
        UClocs = case["UClocs"]
        for i, ucp in enumerate(UCpowers):
            ucl = UClocs[i]
            uptr.deltaTMatrix(ucp, ucl)
        
        deltaTplot_path = os.path.join(outputFolder, "deltaT_{}.png".format(case_name))
        uptr.plotGridTempMatrix(type="DeltaT", save_path=deltaTplot_path)
        
        uptr.gridTemperature()

        uptrPlot_path = os.path.join(outputFolder, "gridT_{}.png".format(case_name))
        uptr.plotGridTempMatrix(type="Temp", save_path=uptrPlot_path, label="Temp (K)")

        ### load ET thermal profile ###
        ETProfile_path = os.path.join(os.path.join(os.path.join(case["ET"], "core"), "MAIN_et"), "ThermalProfile_DIE.txt")
        ETView = RHSCETparser.RHSCETView(ETProfile_path)
        
        gridMismatch = []
        gridET = []
        for grid in uptr.gridTemp:
            region = [grid[0], grid[1], grid[2], grid[3]]
            gridT = grid[4]
            MaxT, avgT, MinT, allT = ETView.getLayerRegionalT(selectedLayer=selectedLayer, region=region)
            avgT = float(avgT)
            mismatch = ((avgT - gridT)/gridT)*100.0
            mismatch = float(F2Sprecision(mismatch, prec=2))

            gridMismatch.append([grid[0], grid[1], grid[2], grid[3], mismatch])
            gridET.append([grid[0], grid[1], grid[2], grid[3], avgT])
        
        uptr_tables[case_name]["MISMATCH"] = gridMismatch
        uptr_tables[case_name]["ET"] = gridET

        mismatchPlot_path = os.path.join(outputFolder, "{}_mismatch.png".format(case_name))
        ETplot_path = os.path.join(outputFolder, "{}_ET.png".format(case_name))

        plotGridValues(resolution, gridMismatch, save_path=mismatchPlot_path, label="Error (%)")
        plotGridValues(resolution, gridET, save_path=ETplot_path, label="Temp (K)")

        uptr_tables[case_name]["MISMATCH"] = gridMismatch
        uptr_tables[case_name]["ET"] = gridET
        uptr_tables[case_name]["UPTR_PLOT_PATH"] = uptrPlot_path
        uptr_tables[case_name]["MISMATCH_PLOT_PATH"] = mismatchPlot_path
        uptr_tables[case_name]["ET_PLOT_PATH"] = ETplot_path
    
    ### make plots into one image ###
    plotCombine(uptr_tables, outputFolder)
    
    # Save uptr_tables as JSON
    compareResult_fullpath = os.path.join(outputFolder, compareResult_path)
    # Convert any non-serializable objects (like UPTRTable) to string or skip
    def serialize(obj):
        if isinstance(obj, UPTRTable):
            return f"UPTRTable(designArea={obj.designArea}, HTCs={obj.HTCs}, resolution={obj.resolution})"
        return str(obj)
    
    with open(compareResult_fullpath, "w") as f:
        json.dump(uptr_tables, f, indent=2, default=serialize)
    print(f"[INFO] Comparison results saved to {compareResult_fullpath}")



def plotCombine(uptr_tables, outputFolder):
    import matplotlib.pyplot as plt
    import matplotlib.image as mpimg

    for case_name, paths in uptr_tables.items():
        uptr_img = paths["UPTR_PLOT_PATH"].format(case_name)
        mismatch_img = paths["MISMATCH_PLOT_PATH"]
        et_img = paths["ET_PLOT_PATH"]

        fig, axs = plt.subplots(1, 3, figsize=(18, 6))
        for ax, img_path, title in zip(
            axs,
            [uptr_img, mismatch_img, et_img],
            ["UPTR Temp", "Mismatch (%)", "ET Temp"]
        ):
            try:
                img = mpimg.imread(img_path)
                ax.imshow(img)
                ax.axis('off')
                ax.set_title(title)
            except Exception as e:
                ax.text(0.5, 0.5, f"Image not found:\n{img_path}", ha='center', va='center')
                ax.axis('off')
                ax.set_title(title)
        plt.tight_layout()
        combined_path = os.path.join(outputFolder, f"{case_name}_combined.png")
        plt.savefig(combined_path, bbox_inches="tight")
        plt.close(fig)
        print(f"[INFO] Combined plot saved to {combined_path}")

    

def plotGridValues(resolution, gridValues, save_path=None, show_plot=False,
                   label="deltaT (K)"):
    import matplotlib.pyplot as plt
    import numpy as np
    
    if not gridValues:
        print("[WARN] gridValues is empty.")
        return
    
    # Convert to numpy array for easier handling
    arr = np.array(gridValues)  # shape: (N, 5)
        
    # Get unique sorted x and y coordinates
    x_vals = np.unique(arr[:, 0])
    y_vals = np.unique(arr[:, 1])
    #print(x_vals, y_vals)
    
    # Build a 2D array for deltaT
    deltaT_matrix = np.full((len(y_vals), len(x_vals)), np.nan)
    for row in arr:
        llx, lly, urx, ury, deltaT = row
        ix = np.where(x_vals == llx)[0][0]
        iy = np.where(y_vals == lly)[0][0]
        deltaT_matrix[iy, ix] = deltaT
    
    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(
        deltaT_matrix,
        origin='lower',
        extent=(x_vals[0], x_vals[-1]+resolution, y_vals[0], y_vals[-1]+resolution),
        aspect='equal',
        cmap='jet'
    )
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label(label)
    ax.set_xlabel("X (um)")
    ax.set_ylabel("Y (um)")
    ax.set_title("Grid {} (imshow)".format(label))
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, bbox_inches="tight")
        print(f"[INFO] Grid deltaT matrix plot saved to {save_path}")
    
    if show_plot:
        plt.show()
    plt.close(fig)    



if __name__ == "__main__":
    
    extendArea = [80, 13]
    resolution = [0.05, 0.16]
    
    p1278 = UPTRCell(resolution=resolution, extendArea=extendArea)
    rdisk, re = p1278.UPTRCore()
    p1278.plotRe(Res=[re], Rdisks=[rdisk], show_plot=True)


    UCpowers = [0.001, 0.001, 0.001, 0.001, 0.001]
    UClocs = [[18, 6], [19, 6], [20, 6], [21, 6], [22, 6]]

    for i, ucp in enumerate(UCpowers):
        ucl = UClocs[i]
        p1278.deltaTMatrix(ucp, ucl)
    
    p1278.plotGridTempMatrix(type="DeltaT", show_plot=True)


    cellSize = [27, 2]
    cellPower = 0.5
    p1278.estimatedCellDeltaT(cellSize, cellPower)
    
    
    """
    designArea = [51, 54]
    HTCs = [1000, 100, 0]
    ambT = 25
    
    p1278 = UPTRTable(designArea, HTCs, ambT, resolution)
    p1278.initUPTR()

    UCpowers = [1, 2, 5, 4, 3]
    UClocs = [[20, 23], [24,24], [20,19], [0, 20], [4, 10]]

    rdisk1, re1, rebound = p1278.UPTRoffCenter(UCloc=[0, 20])
    rdisk2, re2, rebound = p1278.UPTRoffCenter(UCloc=[4, 10])
    Res = [p1278.UPTReval["CORE"]["Re"], re1, re2]
    Rdisks = [p1278.UPTReval["CORE"]["Rdisk"], rdisk1, rdisk2]
    groups = [("CORE", "o", "blue"), ("EDGE", "s", "green"), ("NEAR_EDGE", "^", "red")]
    p1278.plotRe(Res=Res, Rdisks=Rdisks, groups=groups, show_plot=True)

    for i, ucp in enumerate(UCpowers):
        ucl = UClocs[i]
        p1278.deltaTMatrix(ucp, ucl)
    
    
    p1278.plotGridTempMatrix(type="DeltaT", show_plot=True)
    

    testCases = GentestCase(
        outputFolder="testcases",
        genCases=3,
        numPowerSource=2,
        powerRange=[0.05, 0.5],
        powerLocRange=[[20, 25], [20, 25]],
        designArea=[51, 51]
    )
    #print(testCases)
    """
    
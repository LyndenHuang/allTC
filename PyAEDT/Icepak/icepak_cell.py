import os
import sys
import math
import time
import json
import pandas as pd

from ansys.aedt.core import Icepak

from collections import OrderedDict
from IPython.display import Image

"""
Cell-level power-thermal characterization script
SIZE (resolution), POWER_SOURCES (resolution)
Power in "mW", Geometry in "um"
"""

SIZEX = 31
SIZEY = 31
UCPOWER = 0.001

LLX = int(math.floor(SIZEX*0.5))
LLY = int(math.floor(SIZEY*0.5))
URX = LLX+1
URY = LLY+1

DIE = {
    "STRUCTURE": {
        "RESOLUTION": [0.05, 0.16],
        "OFFSET": [0.0, 0.0],
        "SIZE": [SIZEX, SIZEY],
        "LAYERS": ["BSB", "BSV", "BSIC", "Xtor", "FSIC"],
        "BSB": {
            "THICKNESS": 15.7,
            "K_MODEL": "BSB_K"
        },
        "BSV": {
            "THICKNESS": 5.9,
            "K_MODEL": "BSV_K"
        },
        "BSIC": {
            "THICKNESS": 12.87,
            "K_MODEL": "BSIC_K"
        },
        "Xtor": {
            "THICKNESS": 0.18,
            "K_MODEL": "Si_K"
        },
        "FSIC": {
            "THICKNESS": 2.24,
            "K_MODEL": "FSIC_K"
        }
    },
    "POWER_PROFILE": {
        "POSITION": ["Xtor", "TOP"],
        "TYPE": "SOURCES",
        "SOURCES": {
            "S01": [LLX, LLY, URX, URY, UCPOWER]
      }
    },
    "BCs": {
        "AMBT": "25cel",
        "TOP": 4000,
        "BOT": 100
    },
    "K_MODELS": {
        "BSB_K": {
            "KX_KY_KZ": [0.5, 0.5, 10.7]
        },
        "BSV_K": {
            "KX_KY_KZ": [0.5, 0.5, 10.7]
        },
        "BSIC_K": {
            "KX_KY_KZ": [120.0, 120.0, 12.0]
        },
        "Si_K":{
            "KX_KY_KZ": [120, 120, 120]
        },
        "FSIC_K": {
            "KX_KY_KZ": [18.0, 18.0, 1.7]
        }
    }
}

GLOBAL_MESH_SETTINGS = {
    "MaxElementSizeX": "1um",
    "MaxElementSizeY": "1um",
    "MaxElementSizeZ": "0.5um",
    "MinGapX": "0.01um",
    "MinGapY": "0.01um", 
    "MinGapZ": "0.01um",
    "EnableMLM": True,
    "MaxLevels": "3"
}


AEDT_VERSION = "2025.1"
NG_MODE = True  # Open AEDT UI when it is launched.
OUTPUT_FOLDER = "C://PY//Ansys"
CASENAME = f"cellUPTR_{SIZEX}x{SIZEY}"
PROJECT = os.path.join(OUTPUT_FOLDER, f"{CASENAME}.aedt")
MODEL_UNIT = "um"
AMBIENT_TEMP = DIE["BCs"]["AMBT"]
NUM_CORES = 1

JSONCONF_PATH = ""
POSTPROCESS_OUTPUT = os.path.join(OUTPUT_FOLDER, f"{CASENAME}_postprocess.data")


def float_precision(val, prec=4):
    precStr = "{:."+str(prec)+"f}"
    return float(precStr.format(val))


if os.path.exists(PROJECT):
    os.remove(PROJECT)

ipk = Icepak(
    project=PROJECT,
    version=AEDT_VERSION,
    non_graphical=NG_MODE,
    close_on_exit=True,
    new_desktop=True,
    remove_lock=True
)

ipk.solution_type = "SteadyState"
ipk.problem_type = "TemperatureOnly"
#ipk.design_settings["ExportSettings"] = True

ipk.edit_design_settings(ambient_temperature=AMBIENT_TEMP)


ipk.modeler["Region"].delete()   # Remove the air region

ipk.modeler.model_units = MODEL_UNIT  
 

### create materials ###
MATDICT = {}
for mat in DIE["K_MODELS"].keys():
    MATDICT.setdefault(mat, ipk.materials.add_material(mat))
    MATDICT[mat].thermal_conductivity = DIE["K_MODELS"][mat]["KX_KY_KZ"]


### create stacking ###
POWER_LAYER = None
STACK = []

high_priority, low_priority = [], []
offsetX, offsetY = DIE["STRUCTURE"]["OFFSET"]
resolutionX, resolutionY = DIE["STRUCTURE"]["RESOLUTION"]
dx = float_precision(DIE["STRUCTURE"]["SIZE"][0]*resolutionX)
dy = float_precision(DIE["STRUCTURE"]["SIZE"][1]*resolutionY)
thickness = 0.0
total_thickness = 0.0
power_position = 0.0
for ly in DIE["STRUCTURE"]["LAYERS"]:
    mat = DIE["STRUCTURE"][ly]["K_MODEL"]
    layer_thickness = DIE["STRUCTURE"][ly]["THICKNESS"]

    if ly == DIE["POWER_PROFILE"]["POSITION"][0]:
        if DIE["POWER_PROFILE"]["POSITION"][1] == "TOP":
            power_position = total_thickness + layer_thickness
        elif DIE["POWER_PROFILE"]["POSITION"][1] == "BOT":
            power_position = total_thickness
        else:
            power_position = total_thickness

    layer = ipk.modeler.create_box((offsetX, offsetY, total_thickness), \
                                   (offsetX+dx, offsetY+dy, layer_thickness), \
                                    name=ly, material=mat)
    
    if ly == DIE["POWER_PROFILE"]["POSITION"][0]:
        POWER_LAYER = layer
        high_priority.append(layer.name)
    else:
        low_priority.append(layer.name)

    STACK.append(layer)
    total_thickness += layer_thickness
    total_thickness = float_precision(total_thickness)


### create power sources ###
MONITOR_BOUNDARIES = []
SOURCENAMES = {}

totalPW = 0.0
if DIE["POWER_PROFILE"]["TYPE"] == "POWERMAP":
    ### power value in "mW" ###
    sources = []
    dx, dy = DIE["POWER_PROFILE"]["TILE_SIZE"]
    with open(DIE["POWER_PROFILE"]["PATH"]) as f:
        for line in f:
            lls = (line.split()[0]).split(",")
            #print(lls)
            sources.append([float(i) for i in lls])
    
    for m, i in enumerate(sources):
        for n, pvalue in enumerate(i):
            name = f"rectX{n}_Y{m}"
            cell = ipk.modeler.create_rectangle("XY", 
                                               (f"{n*dx}um", f"{m*dy}um", f"{power_position}um"),
                                               (f"{dx}um", f"{dy}um"),
                                               name=name)
            SOURCENAMES.setdefault(name, cell)

            totalPW += pvalue
            
            source_name = f"Source_{m}_{n}"
            ipk.assign_source(cell.name, "Total Power", f"{pvalue}mW", f"X{n}_Y{m}",
                              boundary_name=source_name)
            MONITOR_BOUNDARIES.append(source_name)

elif DIE["POWER_PROFILE"]["TYPE"] == "SOURCES":
    SOURCES = DIE["POWER_PROFILE"]["SOURCES"]
    for pi in SOURCES.keys():
        llx = float_precision((SOURCES[pi][0]*resolutionX) + offsetX)
        lly = float_precision((SOURCES[pi][1]*resolutionY) + offsetY)
        urx = float_precision((SOURCES[pi][2]*resolutionX) + offsetX)
        ury = float_precision((SOURCES[pi][3]*resolutionY) + offsetY)
        width = float_precision((urx - llx))   ## in um
        height = float_precision((ury - lly))  ## in um
        ### power in mW ###
        pvalue = SOURCES[pi][-1]

        name = pi
        cell = ipk.modeler.create_rectangle("XY",
                                            (f"{llx}um",f"{lly}um", f"{power_position}um"),
                                            (f"{width}um", f"{height}um"),
                                            name=name)
        SOURCENAMES.setdefault(name, cell)

        totalPW += pvalue
        
        source_name = f"Source_{pi}"
        ipk.assign_source(cell.name, "Total Power", f"{pvalue}mW",
                          boundary_name=source_name)
        MONITOR_BOUNDARIES.append(source_name)
        
else:
    pass

### Assign monitor points on power_position ###
MONITOR_POINTS = []
MONITOR_POINTS_DICT = {}

num_points_x = int(math.ceil(DIE["STRUCTURE"]["SIZE"][0] * 0.5))
num_points_y = int(math.ceil(DIE["STRUCTURE"]["SIZE"][1] * 0.5))

x_spacing = DIE["STRUCTURE"]["RESOLUTION"][0]
y_spacing = DIE["STRUCTURE"]["RESOLUTION"][1]

X_POS = float_precision((DIE["POWER_PROFILE"]["SOURCES"]["S01"][0]*resolutionX) + offsetX + (resolutionX*0.5))
Y_POS = float_precision((DIE["POWER_PROFILE"]["SOURCES"]["S01"][1]*resolutionY) + offsetY + (resolutionY*0.5))
Z_POS = power_position
### in X direction only ###
for i in range(num_points_x):
    x_pos = DIE["STRUCTURE"]["OFFSET"][0] + (i*x_spacing) + (x_spacing*0.5)
    x_pos = float_precision(x_pos)
    
    point_name = f"PX_{i+1}"
    m = ipk.modeler.create_point([f"{x_pos}um", f"{Y_POS}um", f"{Z_POS}um"],
                                 name=point_name)
    
    MONITOR_POINTS.append(point_name)
    MONITOR_POINTS_DICT.setdefault(point_name, [f"{x_pos}", f"{Y_POS}", f"{Z_POS}"])

### in Y direction only ###
for j in range(num_points_y):
    y_pos = DIE["STRUCTURE"]["OFFSET"][1] + (j*y_spacing) + (y_spacing*0.5)
    y_pos = float_precision(y_pos)
    
    point_name = f"PY_{j+1}"
    m = ipk.modeler.create_point([f"{X_POS}um", f"{y_pos}um", f"{Z_POS}um"],
                                 name=point_name)
    
    MONITOR_POINTS.append(point_name)
    MONITOR_POINTS_DICT.setdefault(point_name, [f"{X_POS}", f"{y_pos}", f"{Z_POS}"])

### in both XY direction (Diagonal) ###
pointCounter = 0
while True:
    x_pos = X_POS - ((pointCounter+1)*resolutionX)
    x_pos = float_precision(x_pos)
    
    y_pos = Y_POS - ((pointCounter+1)*resolutionY)
    y_pos = float_precision(y_pos)
    
    if x_pos > 0 and y_pos > 0:
        point_name = f"PXY_{pointCounter+1}"
        m = ipk.modeler.create_point([f"{x_pos}um", f"{y_pos}um", f"{Z_POS}um"],
                                     name=point_name)
        MONITOR_POINTS.append(point_name)
        MONITOR_POINTS_DICT.setdefault(point_name, [f"{x_pos}", f"{y_pos}", f"{Z_POS}"])
    else:
        break
    
    pointCounter += 1


### assign boundary ####
TOP = STACK[-1]
BOT = STACK[0]
BCTop = DIE["BCs"]["TOP"]
BCBot = DIE["BCs"]["BOT"]
ipk.assign_stationary_wall(TOP.top_face_z.id, 
                           boundary_condition = "Heat Transfer Coefficient",
                           htc = f"{BCTop}w_per_m2kel", ref_temperature=AMBIENT_TEMP,
                           name="BCTop"
                           )
ipk.assign_stationary_wall(BOT.bottom_face_z.id, 
                          boundary_condition = "Heat Transfer Coefficient",
                          htc = f"{BCBot}w_per_m2kel", ref_temperature=AMBIENT_TEMP,
                          name="BCBot"
                          )

MONITOR_BOUNDARIES.append("BCTop")
MONITOR_BOUNDARIES.append("BCBot")

### assign mesh setting ###
glob_msh = ipk.mesh.global_mesh_region   ### global mesh setting

glob_msh.UserSpecifiedSettings = True
for key, value in GLOBAL_MESH_SETTINGS.items():
    glob_msh.UserSpecifiedSettings = True
    if hasattr(glob_msh, key):
        setattr(glob_msh,key,value)

glob_msh.update()

## assign mesh operation to source ##
for source_name in SOURCENAMES.keys():
    ipk.mesh.assign_mesh_level({source_name:2})
    ipk.mesh.meshoperations[0].props.update(OrderedDict({
            "MaxLevel": "5",
            "MinLevel": "5",
    }))
    ipk.mesh.meshoperations[0].props.pop("Level")
    ipk.mesh.meshoperations[0].update()


### assign priorities ###
priorities = [low_priority, high_priority]

ipk.mesh.assign_priorities(priorities)

setup = ipk.create_setup()
setup.props["Convergence Criteria - Energy"] = 1e-12
setup.props["Convergence Criteria - Max Iterations"] = 500


ipk.save_project()


PLOT_SURFACES = {
    "TOP": TOP.top_face_z.id,
    "POWER": POWER_LAYER.top_face_z.id
}


POSSPROCESS_DATA = {
    "MONITOR_BOUNDARIES": MONITOR_BOUNDARIES,
    "MONITOR_POINTS": MONITOR_POINTS,
    "PLOT_SURFACES": PLOT_SURFACES,
    "DESIGN_DATA": DIE,
    "MONITOR_POINTS_DICT": MONITOR_POINTS_DICT
}

with open(POSTPROCESS_OUTPUT, "w") as f:
    json.dump(POSSPROCESS_DATA, f, default=str, indent=2)


### BUG: Cannot run successfully in my manchine ###
#ipk.analyze()


ipk.release_desktop()
#ipk.release_desktop(close_desktop=False)
time.sleep(1)

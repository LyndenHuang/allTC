import os
import json
from ansys.aedt.core import Icepak

### power source: [llx, lly, urx, ury, PD(W/m^2)]
### BCs unit: W/(Km2)
"""
DIE = {
    "STRUCTURE": {
        "OFFSET": [0.0, 0.0],
        "SIZE": [27.0, 27.0],
        "LAYERS": ["BSB", "BSV", "BSIC", "FSIC"],
        "BSB": {
            "THICKNESS": 15.7,
            "K_MODEL": "BSB_K"
        },
        "BSV": {
            "THICKNESS": 5.8,
            "K_MODEL": "BSV_K"
        },
        "BSIC": {
            "THICKNESS": 12.87,
            "K_MODEL": "BSIC_K"
        },
        "FSIC": {
            "THICKNESS": 2.24,
            "K_MODEL": "FSIC_K"
        }
    },
    "POWER_PROFILE": {
        "POSITION": ["BSIC", "TOP"],
        "TYPE": "POWERMAP",
        "TILE_SIZE": [3, 3],
        "PATH": "./PW_9x9.csv"
    },
    "BCs": {
        "TOP": 4000,
        "BOT": 100
    },
    "K_MODELS": {
        "BSB_K": {
            "KX_KY_KZ": [0.5, 0.5, 10.7],
        },
        "BSV_K": {
            "KX_KY_KZ": [0.5, 0.5, 10.7],
        },
        "BSIC_K": {
            "KX_KY_KZ": [120.0, 120.0, 12.0],
        },
        "FSIC_K": {
            "KX_KY_KZ": [18.0, 18.0, 1.7],
        }
    }
}
"""

DIE = {
    "STRUCTURE": {
        "OFFSET": [0.0, 0.0],
        "SIZE": [21.0, 21.0],
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
            "S01": [10, 10, 11, 11, 0.1]
      }
    },
    "BCs": {
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


AEDT_VERSION = "2025.1"
NG_MODE = True  # Open AEDT UI when it is launched.
project = os.path.join("C://PY//Ansys", "UC21b21_xtor.aedt")

if os.path.exists(project):
    os.remove(project)

ipk = Icepak(
    project=project,
    version=AEDT_VERSION,
    non_graphical=NG_MODE,
    close_on_exit=True,
    new_desktop=True,
)
    
ipk.solution_type = "SteadyState"
ipk.problem_type = "TemperatureOnly"
#ipk.design_settings["ExportSettings"] = True

ipk.edit_design_settings(ambient_temperature="25cel")


ipk.modeler["Region"].delete()   # Remove the air region

ipk.modeler.model_units = "um"   
ipk.modeler.delete("Region")

### create materials ###
MATDICT = {}
for mat in DIE["K_MODELS"].keys():
    MATDICT.setdefault(mat, ipk.materials.add_material(mat))
    MATDICT[mat].thermal_conductivity = DIE["K_MODELS"][mat]["KX_KY_KZ"]


### create stacking ###
POWER_POSITION = 0.0
POWER_LAYER = DIE["POWER_PROFILE"]["POSITION"][0]
STACK = []

high_priority, low_priority = [], []
offsetX, offsetY = DIE["STRUCTURE"]["OFFSET"]
dx, dy = DIE["STRUCTURE"]["SIZE"]
thickness = 0.0
total_thickness = 0.0
for ly in DIE["STRUCTURE"]["LAYERS"]:
    mat = DIE["STRUCTURE"][ly]["K_MODEL"]
    layer_thickness = DIE["STRUCTURE"][ly]["THICKNESS"]

    if ly == POWER_LAYER:
        if DIE["POWER_PROFILE"]["POSITION"][1] == "TOP":
            POWER_POSITION = total_thickness + layer_thickness
        elif DIE["POWER_PROFILE"]["POSITION"][1] == "BOT":
            POWER_POSITION = total_thickness
        else:
            POWER_POSITION = total_thickness

    layer = ipk.modeler.create_box((offsetX, offsetY, total_thickness), \
                                   (offsetX+dx, offsetY+dy, layer_thickness), \
                                    name=ly, material=mat)
    
    if ly == POWER_LAYER:
        high_priority.append(layer.name)
    else:
        low_priority.append(layer.name)

    STACK.append(layer)
    total_thickness += layer_thickness
    total_thickness = float("{:.4f}".format(total_thickness))


### create power sources ###
MONITORSOURCES = {}
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
                                               (f"{n*dx}um", f"{m*dy}um", f"{POWER_POSITION}um"),
                                               (f"{dx}um", f"{dy}um"),
                                               name=name)
            SOURCENAMES.setdefault(name, cell)

            totalPW += pvalue
            ipk.assign_source(cell.name, "Total Power", f"{pvalue}mW", f"X{n}_Y{m}")
            ### assign monitor ###
            Mcell = ipk.assign_surface_monitor(name, monitor_name="M{}".format(name))
            MONITORSOURCES.setdefault("M{}".format(name), Mcell)


elif DIE["POWER_PROFILE"]["TYPE"] == "SOURCES":
    SOURCES = DIE["POWER_PROFILE"]["SOURCES"]
    for pi in SOURCES.keys():
        llx, lly, urx, ury = SOURCES[pi][0:4]
        width = float("{:.4f}".format(urx - llx))   ## in um
        height = float("{:.4f}".format(ury - lly))  ## in um
        ### power in mW ###
        pvalue = SOURCES[pi][-1]

        name = pi
        cell = ipk.modeler.create_rectangle("XY",
                                            (f"{llx}um",f"{lly}um", f"{POWER_POSITION}um"),
                                            (f"{width}um", f"{height}um"),
                                            name=name)
        SOURCENAMES.setdefault(name, cell)

        totalPW += pvalue
        ipk.assign_source(cell.name, "Total Power", f"{pvalue}mW")
        ### assign monitor ###
        Mcell = ipk.assign_surface_monitor(name, monitor_name="M{}".format(name))
        MONITORSOURCES.setdefault("M{}".format(name), Mcell)
else:
    pass



### assign boundary ####
TOP = STACK[-1]
BOT = STACK[0]
BCTop = DIE["BCs"]["TOP"]
BCBot = DIE["BCs"]["BOT"]
ipk.assign_stationary_wall(TOP.top_face_z.id, 
                           boundary_condition = "Heat Transfer Coefficient",
                           htc = f"{BCTop}w_per_m2kel", ref_temperature="25cel"
                           )
ipk.assign_stationary_wall(BOT.bottom_face_z.id, 
                          boundary_condition = "Heat Transfer Coefficient",
                          htc = f"{BCBot}w_per_m2kel", ref_temperature="25cel"
                          )

### create monitors ###
mTop = ipk.monitor.assign_face_monitor(
    face_id=TOP.top_face_z.id,
    monitor_quantity="Temperature",
    monitor_name="TOP",
)

"""
point_monitors = []
for x_pos in range(0, 60, 10):
    m = ipk.monitor.assign_point_monitor(
        point_position=[f"{x_pos}um", "50um", f"{POWER_POSITION}um"], 
        monitor_quantity="Temperature"
    )
    point_monitors.append(m)
"""

### assign priorities ###
priorities = [low_priority, high_priority]

ipk.mesh.assign_priorities(priorities)

setup = ipk.create_setup()
setup.props["Convergence Criteria - Energy"] = 1e-12
setup.props["Convergence Criteria - Max Iterations"] = 500

### Mesh setting ###
ipk.globalMeshSettings(3)


#icepak.analyze()
ipk.save_project()
ipk.close_project()



import os
import json
from ansys.aedt.core import Edb
from itertools import product
import math

DIE = {
    "STRUCTURE":{
        "LAYERS": ["BLB", "BLV", "BSIC", "FSIC"],
        "BLB": {
            "THICKNESS": 14.0,
            "K_MODEL": "BLB_K"
        },
        "BLV": {
            "THICKNESS": 1.7,
            "K_MODEL": "BLV_K"
        },
        "BSIC": {
            "THICKNESS": 12.87,
            "K_MODEL": "BSIC_K"
        },
        "FSIC": {
            "THICKNESS": 2.37,
            "K_MODEL": "FSIC_K"
        }
    },
    "POWER_PROFILE":{

    },
    "K_MODELS": {
        "BLB_K": {
            "KX_KY_KZ": [0.5, 0.5, 10.7],
        },
        "BLV_K": {
            "KX_KY_KZ": [0.5, 0.5, 10.7],
        },
        "BSIC_K": {
            "KX_KY_KZ": [120.0, 120.0, 12.0],
        },
        "FSIC_K": {
            "KX_KY_KZ": [18.0, 18.0, 1.9],
        }
    }
}

layer_name = ""
thickness = 0.0
dx, dy = 10, 10
row, col = 3, 3


edb = Edb(edbversion='2025.1')

total_thickness = 0
for layer_name in DIE["STRUCTURE"]["LAYERS"]:
    thickness = DIE["STRUCTURE"][layer_name]["THICKNESS"]
    edb.stackup.add_layer(layer_name, method='add_on_top', thickness=f'{thickness}um',)
    total_thickness += thickness

for layer_name in DIE["STRUCTURE"]["LAYERS"]:
    for m in range(row):
        for n in range(col):
            rect = edb.modeler.create_rectangle(layer_name, 'gnd',
                                                (f'{dx*m}um', f'{dy*n}um'),
                                                (f'{dx*(m+1)}um', f'{dy*(n+1)}um'),)

edb.save_edb_as("./chip.aedb")
edb.close_edb()
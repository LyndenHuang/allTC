import os
import sys
import json
import pandas as pd
import matplotlib.pyplot as plt

from ansys.aedt.core import Icepak

from IPython.display import Image


CASENAME = "cellUPTR_31x31"

AEDT_VERSION = "2025.1"
NG_MODE = True  # Open AEDT UI when it is launched.
OUTPUT_FOLDER = "C://PY//Ansys"
PROJECT = os.path.join(OUTPUT_FOLDER, f"{CASENAME}.aedt")

POSTPROCESS_DATA_PATH = os.path.join(OUTPUT_FOLDER,  f"{CASENAME}_postprocess.data")

with open(POSTPROCESS_DATA_PATH, "r") as f:
    postprocess_data = json.load(f)


def float_precision(val, prec=4):
    precStr = "{:."+str(prec)+"f}"
    return float(precStr.format(val))


if not os.path.exists(PROJECT):
    print("Project not exist.")
    sys.exit(1)

ipk = Icepak(
    project=PROJECT,
    version=AEDT_VERSION,
    non_graphical=NG_MODE,
    remove_lock=True
)

"""
monitor_temperature = {}
for quantity in ipk.post.available_report_quantities(quantities_category="Monitor"):
    data = ipk.post.get_solution_data(quantity)
    monitor_temperature[quantity] = data.data_real()[0]

print(monitor_temperature)
"""

temperature_points = ipk.post.create_field_summary()
temperature_boundaries = ipk.post.create_field_summary()


for name in postprocess_data["MONITOR_POINTS"]:
    temperature_points.add_calculation(
        entity="Object", geometry="Volume", geometry_name=name, quantity="Temperature"
    )

for name in postprocess_data["MONITOR_BOUNDARIES"]:
    temperature_boundaries.add_calculation(
        entity="Boundary", geometry="Surface", geometry_name=name, quantity="Temperature"
    )

temperature_points_data = temperature_points.get_field_summary_data(pandas_output=True)
temperature_boundaries_data = temperature_boundaries.get_field_summary_data(pandas_output=True)

#temperature_points_data.head()

for surface_name in postprocess_data["PLOT_SURFACES"].keys():
    plot3 = ipk.post.create_fieldplot_surface(
        assignment=postprocess_data["PLOT_SURFACES"][surface_name], 
        quantity="SurfTemperature"
    )
    path = plot3.export_image(
        full_path=os.path.join(OUTPUT_FOLDER, f"{CASENAME}_{surface_name}.png"),
        orientation="top",
        show_region=False,
    )
    Image(filename=path)  # Display the image


ipk.release_desktop()


### Re-format data and summarize ###
DIE = postprocess_data["DESIGN_DATA"]
POINT_DICT = postprocess_data["MONITOR_POINTS_DICT"]   ### {"Name": [x(um), y(um), z(um)]}

# temperature_points_data index need to be extracted are: Entity, Mean
# temperature_boundaries_data to be extracted are: Entity, Min, Max, Mean, Stdev
points_temp_dict = dict(
    zip(
        temperature_points_data["Entity"],
        temperature_points_data["Mean"]
    )
)
#print(points_temp_dict)

# Extract Min, Max, Mean for Entity named "BCTop" from temperature_boundaries_data
bctop_row = temperature_boundaries_data[temperature_boundaries_data["Entity"] == "BCTop"]
if not bctop_row.empty:
    bctop_min = bctop_row["Min"].values[0]
    bctop_max = bctop_row["Max"].values[0]
    bctop_mean = bctop_row["Mean"].values[0]
    print(f"BCTop - Min: {bctop_min}, Max: {bctop_max}, Mean: {bctop_mean}")
else:
    print("Entity 'BCTop' not found in temperature_boundaries_data.")

# Extract Min, Max, Mean for Entity named "Source_S01" from temperature_boundaries_data
UC_power = DIE["POWER_PROFILE"]["SOURCES"]["S01"][-1]
UC_power = float(UC_power)*0.001    ## from "mW" to "W"
UC_row = temperature_boundaries_data[temperature_boundaries_data["Entity"] == "Source_S01"]
if not UC_row.empty:
    UC_min = UC_row["Min"].values[0]
    UC_max = UC_row["Max"].values[0]
    UC_mean = UC_row["Mean"].values[0]
    print(f"UC - Min: {UC_min}, Max: {UC_max}, Mean: {UC_mean}")
else:
    print("Entity 'UC' not found in temperature_boundaries_data.")


resolution = DIE["STRUCTURE"]["RESOLUTION"]
offset = DIE["STRUCTURE"]["OFFSET"]
power_llx = (int(DIE["POWER_PROFILE"]["SOURCES"]["S01"][0])*float(resolution[0])) + offset[0]
power_lly = (int(DIE["POWER_PROFILE"]["SOURCES"]["S01"][1])*float(resolution[1])) + offset[1]
power_ref_x = power_llx + (float(resolution[0])*0.5)
power_ref_y = power_lly + (float(resolution[1])*0.5)

### ReX: resistance in X direction ###
distX, deltaTX = [], []
ReX = []
indX = DIE["POWER_PROFILE"]["SOURCES"]["S01"][0]
for i in range(int(indX), 0, -1):
    point_name = f"PX_{i}"
    if point_name in points_temp_dict:
        x = float(POINT_DICT[point_name][0])
        dist = abs(x - power_ref_x)
        dist = float_precision(dist, prec=2)
        temp = points_temp_dict[point_name]
        if pd.isna(temp):
            continue
        
        deltaT = UC_max - temp
        deltaT = float_precision(deltaT, prec=4)
        distX.append(dist)
        deltaTX.append(deltaT)
        if UC_power != 0:
            re = float_precision(deltaT/UC_power, prec=4)
            ReX.append(re)
        else:
            ReX.append(float('nan'))

### ReY: resistance in Y direction ###
distY, deltaTY = [], []
ReY = []
indY = DIE["POWER_PROFILE"]["SOURCES"]["S01"][1]
for i in range(int(indY), 0, -1):
    point_name = f"PY_{i}"
    if point_name in points_temp_dict:
        y = float(POINT_DICT[point_name][1])
        dist = abs(y - power_ref_y)
        dist = float_precision(dist, prec=2)
        temp = points_temp_dict[point_name]
        if pd.isna(temp):
            continue
        
        deltaT = UC_max - temp
        deltaT = float_precision(deltaT, prec=4)
        distY.append(dist)
        deltaTY.append(deltaT)
        if UC_power != 0:
            re = float_precision(deltaT/UC_power, prec=4)
            ReY.append(re)
        else:
            ReY.append(float('nan'))

### ReXY: resistance in XY direction ###
distXY, deltaTXY = [], []
ReXY = []
pointCounter = 1
while True:
    point_name = f"PXY_{pointCounter}"
    if point_name in points_temp_dict:
        x = float(POINT_DICT[point_name][0])
        y = float(POINT_DICT[point_name][1])
        dist = ((x - power_ref_x) ** 2 + (y - power_ref_y) ** 2) ** 0.5
        dist = float_precision(dist, prec=2)
        temp = points_temp_dict[point_name]
        if pd.isna(temp):
            pointCounter += 1
            continue

        deltaT = UC_max - temp
        deltaT = float_precision(deltaT, prec=4)
        distXY.append(dist)
        deltaTXY.append(deltaT)
        if UC_power != 0:
            re = float_precision(deltaT/UC_power, prec=4)
            ReXY.append(re)
        else:
            ReXY.append(float('nan'))
    else:
        break

    pointCounter += 1

### output extracted results to saveDict ###
# Combine all distances and resistances into a single list
combined_list = []

for dist, rex in zip(distX, ReX):
    combined_list.append({"Direction": "X", "Distance": dist, "Resistance": rex})
for dist, rey in zip(distY, ReY):
    combined_list.append({"Direction": "Y", "Distance": dist, "Resistance": rey})
for dist, rexy in zip(distXY, ReXY):
    combined_list.append({"Direction": "XY", "Distance": dist, "Resistance": rexy})

# Sort the combined list by Distance
combined_list_sorted = sorted(combined_list, key=lambda x: x["Distance"])

saveDict = {
    "Input": {
        "Resolution": DIE["STRUCTURE"]["RESOLUTION"],
        "DesignArea(resolution)": DIE["STRUCTURE"]["SIZE"],
        "UCPower(W)": UC_power,
        "BCs(W/m^2K)": {"RefT": DIE["BCs"]["AMBT"], "HTCs":[DIE["BCs"]["TOP"], DIE["BCs"]["BOT"]]}
    },
    "Output": {
        "UCTemp": UC_max,
        "XX": {"distX": distX, "deltaTX": deltaTX, "ReX": ReX},
        "YY": {"distY": distY, "deltaTY": deltaTY, "ReY": ReY},
        "XY": {"distXY": distXY, "deltaTXY": deltaTXY, "ReXY": ReXY},
        "COMBINE": combined_list_sorted
    }
}

# Output saveDict to JSON format
output_json_path = os.path.join(OUTPUT_FOLDER, f"{CASENAME}_TRe_summary.json")
with open(output_json_path, "w") as json_file:
    json.dump(saveDict, json_file, indent=4)
print(f"Thermal resistance summary saved to {output_json_path}")

# Output distance & resistance to CSV format
output_csv_path = os.path.join(OUTPUT_FOLDER, f"{CASENAME}_TRe_summary.csv")

# Flatten saveDict for CSV output
rows = []

# XX direction
for dist, rex in zip(saveDict["Output"]["XX"]["distX"], saveDict["Output"]["XX"]["ReX"]):
    rows.append({
        "Direction": "X",
        "Distance": dist,
        "Resistance": rex
    })

# YY direction
for dist, rey in zip(saveDict["Output"]["YY"]["distY"], saveDict["Output"]["YY"]["ReY"]):
    rows.append({
        "Direction": "Y",
        "Distance": dist,
        "Resistance": rey
    })

# XY direction
for dist, rexy in zip(saveDict["Output"]["XY"]["distXY"], saveDict["Output"]["XY"]["ReXY"]):
    rows.append({
        "Direction": "XY",
        "Distance": dist,
        "Resistance": rexy
    })

# Add combined_list_sorted to rows
for item in combined_list_sorted:
    rows.append({
        "Direction": item["Direction"],
        "Distance": item["Distance"],
        "Resistance": item["Resistance"]
    })

df = pd.DataFrame(rows)
df.to_csv(output_csv_path, index=False)
print(f"Thermal resistance summary saved to {output_csv_path}")
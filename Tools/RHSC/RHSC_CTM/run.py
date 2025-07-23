import os
central_dir = os.getcwd()
os.environ["cps_data_path_env"]=central_dir

gp.open_scheduler_window()
ll = create_local_launcher("local")
register_default_launcher(ll, min_num_workders=5, max_num_workers=10)

include("./input_files.py")
include("./options.py")

TOP_CELL_NAME = "TOP"
RESOLUTION = 10

db = gp.open_db("./db")

### create liberty view ###
lv = db.create_liberty_view(liberty_files=lib_files, tag="lv", options=options)

### create design view ###
dv = db.create_design_view(lib_views=lv, top_cell_name=TOP_CELL_NAME, def_files=def_files, lef_files=lef_files, options=options, tag="dv0")

### create tech view ###
nv = db.create_tech_view(tech_file_name=tech_file, options=options, tag="nv")

### create extraction view ###
extraction_settings = {}
ev = db.create_extract_view(dv, tech_view=nv, tag="ev", options=options, settings=extraction_settings)

### create power view ###
pwr_settings = {}
pwr = db.create_power_view(design_view=dv, power_files=ipf_files, extract_view=ev, options=options, settings=pwr_settings, tag="pwr")

### create CTM view ###
ctm_output_directory = "./CTM"
temperatures = [25, 50, 75, 100, 125]
power_settings = {"regions":[{"value":0.2, "region":RealRect(0, -0.1, 5.2, 1.5)},]}

ctm_settings = {"leakage":{"leakage_model":"", "temperatures": temperatures}, 
                "report": {"ctm_output_directory": ctm_output_directory},
                "power": power_settings}
db.create_chip_thermal_model(ev, power_view=pwr, tile_dimension=RESOLUTION, tag="ctm", settings=ctm_settings)
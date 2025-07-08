import glob

def_files = glob.glob("../def/*.def") + glob.glob("../def/*.def.gz")

lef_files = glob.glob("../lef/*.lef") + glob.glob("../lef/*.lef.gz")

lib_files = glob.glob("../lib/*lib")

tech_file = "../tech/fake.tech" #"../tech/rc_apache_tttt.tech" #"../tech/GENERIC.tech"

ipf_files = ["../ipf/thermal_case.ipf"]


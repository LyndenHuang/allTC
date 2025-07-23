import glob

def_files = glob.glob("./00.DesignData/def/*.def") + glob.glob("./00.DesignData/def/*.def.gz")

lef_files = glob.glob("./00.DesignData/lef/*.lef") + glob.glob("./00.DesignData/lef/*.lef.gz")

lib_files = glob.glob("./00.DesignData/lib/*lib")

tech_file = "./00.DesignData/tech/GENERIC.tech"

ipf_files = "./00.DesignData/ipf/test.ipf"


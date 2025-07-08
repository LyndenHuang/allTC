import os
from setups import utilities

if __name__ == "__main__":
    ### command: python NgBatchMode_openET.py
    root_ut1 = os.path.join(os.getcwd(), "CASEs")
    _caseFolder = utilities.createCASE(root_ut1, "OpenET")
    _caseDB = os.path.join(_caseFolder, "DB")

    runcmd = ["#!/bin/csh",
              "source /nfs/site/disks/x5e2d_gwa_chienchi_001/Tools/licenses/ansys.csh", \
              "redhawk_sc_et -3dic"]
    
    runcshPath = os.path.join(_caseDB, "runETGUI.csh")
    utilities.submitJob(runcmd, runcshPath=runcshPath)

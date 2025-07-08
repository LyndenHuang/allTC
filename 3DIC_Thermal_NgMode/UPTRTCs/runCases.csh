#!/bin/csh -h
source /nfs/site/disks/x5e2d_gwa_chienchi_001/Tools/myPy3.12/bin/activate.csh
python NgBatchMode.py --JSON=UPTRTCs/TC_1.json --caseFolder=UPTRTCs/ET_1
python NgBatchMode.py --JSON=UPTRTCs/TC_2.json --caseFolder=UPTRTCs/ET_2
python NgBatchMode.py --JSON=UPTRTCs/TC_3.json --caseFolder=UPTRTCs/ET_3

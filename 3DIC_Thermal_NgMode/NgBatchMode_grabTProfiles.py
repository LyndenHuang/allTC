import os
import sys
import argparse
import json

from parsers import RHSCETparser
from setups import utilities

def arg():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--caseFolder", type=str, required=False, default="./NgBatch", help="Create non-GUI batch run folder")
    parser.add_argument(
        "--selectedLayer", type=str, required=False, default="NPTAB", help="Select which detail thermal profile layer")
    parser.add_argument(
        "--cellListFile", type=str, required=False, default="", help="if provide the cellListFile, grap this regional temperatures")
    parser.add_argument(
        "--reportFolder", type=str, required=False, default="./Report", help="Output report folder")

    return parser


if __name__ == "__main__":
    ### command: python NgBatchMode_grabTProfiles.py --caseFolder=./CASENAME1;./CASENAME2;..., --selectedLayer="NPTAB" --reportFolder=./outTop
    ###                                              --cellListFile=./xxx.list
    args = arg().parse_args()

    CASEs, TMaxs, TMins = ["Case"], ["TMax"], ["TMin"]
    DETAILs = []
    cases = args.caseFolder.split(",")
    selectedLayer = args.selectedLayer

    isCellListFile = False
    if os.path.isfile(args.cellListFile):
        isCellListFile = True
        CELLTMaxs, CELLTAvg, CELLTMins = ["Cells_TMax"], ["Cells_TAvg"], ["Cells_TMin"] 
        cellLLX, cellLLY, cellURX, cellURY = utilities.calCellListArea(args.cellListFile)

    for case in cases:
        if len(case) > 0:
            pass
        else:
            continue
            
        CASEs.append(case)
        DETAILs.append(case)

        caseName = os.path.join(os.path.join(case, "core"), "MAIN_et")
        TProfilePath = os.path.join(caseName, "ThermalProfile_DIE.txt")

        if not os.path.isfile(TProfilePath):
            print("<WARNING> Thermal profile: {} not found".format(TProfilePath))
            continue
        
        etView = RHSCETparser.RHSCETView(TProfilePath)
        TMax = etView.getLayerTMax(selectedLayer=selectedLayer)
        TMin = etView.getLayerTMin(selectedLayer=selectedLayer)

        if isCellListFile:
            cellMaxT, cellavgT, cellMinT, cellallT = etView.getLayerRegionalT(selectedLayer=selectedLayer, \
                                                            region=[cellLLX, cellLLY, cellURX, cellURY])
            CELLTMaxs.append(cellMaxT)
            CELLTAvg.append(cellavgT)
            CELLTMins.append(cellMinT)

        TMaxs.append(TMax)
        TMins.append(TMin)
        header, vals = etView.getLayerTvals(selectedLayer=selectedLayer)
        DETAILs.append(",".join(header))
        DETAILs.append(",".join(vals))

        if isCellListFile:
            DETAILs.append("## cellListFile ##")
            DETAILs.append(",".join(cellallT))

    outStr = [",".join(CASEs), ",".join(TMaxs), ",".join(TMins)]

    if isCellListFile:
        outStr = [",".join(CASEs), ",".join(TMaxs), ",".join(TMins), ",".join(CELLTAvg), ",".join(CELLTMaxs), ",".join(CELLTMins)]

    reportPath = os.path.join(args.reportFolder, "report.txt")
    
    if not os.path.isdir(args.reportFolder):
        os.makedirs(args.reportFolder, 0o755)
    
    with open(reportPath, "w") as fid:
        fid.write("\n".join(outStr))
        fid.write("\n\nDetail\n")
        fid.write("\n".join(DETAILs))

    print("<INFO> DONE")

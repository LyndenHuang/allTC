import os
import sys
import re
import argparse
import copy

def arg():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fc_powermap", type=str, required=False, default="", help="FC powermap csv path")
    parser.add_argument(
        "--outputFolder", type=str, required=False, default="./", help="output folder")
    parser.add_argument(
        "--outputName", type=str, required=False, default="pwd.mhs", help="output name")   

    return parser

def FCpowermap2RHSCETmhs(FCcsvpath, outputFolder, outputName):
    def __F2Sprecision(fval):
        return "{:.5f}".format(fval)

    if not os.path.isfile(FCcsvpath):
        print("[ERROR] {} powermap csv path not found".format(FCcsvpath))
        return
    
    LLX, LLY, URX, URY = 10000, 10000, -10000, -10000
    dbDict = {}  ### "avgPD" unit: uW/um^2, "PWR" unit: mW
    count = 0
    with open(FCcsvpath, "r") as fid:
        for ll in fid:
            ll = ll.split("\n")[0]
            if re.match(r"^{", ll, re.M|re.I):
                lls = ll.split(",")
                coord = re.match(r"{([-+]?\d*\.?\d+) ([-+]?\d*\.?\d+)} {([-+]?\d*\.?\d+) ([-+]?\d*\.?\d+)}", ll)
                llx, lly = float(coord.group(1)), float(coord.group(2))
                urx, ury = float(coord.group(3)), float(coord.group(4))
                pd1, pd2 = lls[1:3]
                avgPD = float("{:.3f}".format((float(pd1)+float(pd2))*0.5))
                area = (urx-llx)*(ury-lly)
                pwr = avgPD*area*0.001*0.1  ## uW -> mW 
                if LLX > llx:
                    LLX = llx
                if LLY > lly:
                    LLY = lly
                if URX < urx:
                    URX = urx
                if URY < ury:
                    URY = ury
                dbDict.setdefault(count, {"llx":llx, "lly":lly, "urx":urx, "ury":ury, \
                                          "avgPD":avgPD, "PWR":pwr})

                count += 1
    
    print("<INFO> Area:{},{},{},{}".format(LLX, LLY, URX, URY))
    ### to RHSC_ET mhs coordination ###
    offsetX = float("{:.5f}".format((URX-LLX)*0.5))
    offsetY = float("{:.5f}".format((URY-LLY)*0.5))

    EToutStr = ["#BBOX <llx(um)> <lly(um)> <urx(um)> <ury(um)>", \
                "#<Box_ID> <llx(um)> <lly(um)> <urx(um)> <ury(um)> <Power(mW)>"]
    
    llx, lly = __F2Sprecision(0-offsetX), __F2Sprecision(0-offsetY)
    urx, ury = __F2Sprecision(0+offsetX), __F2Sprecision(0+offsetY)
    bbox = "BBOX {} {} {} {}".format(llx, lly, urx, ury)
    EToutStr.append(bbox)

    for i, k in enumerate(dbDict.keys()):
        llx = __F2Sprecision(dbDict[k]["llx"]-offsetX)
        lly = __F2Sprecision(dbDict[k]["lly"]-offsetY)
        urx = __F2Sprecision(dbDict[k]["urx"]-offsetX)
        ury = __F2Sprecision(dbDict[k]["ury"]-offsetY)
        pwr = __F2Sprecision(dbDict[k]["PWR"])
        _str = "{} {} {} {} {} {}".format(i+1, llx, lly, urx, ury, pwr)
        EToutStr.append(_str)
    
    if not os.path.isdir(outputFolder):
        os.makedirs(outputFolder)
    
    outPath = os.path.join(outputFolder, outputName)
    with open(outPath, "w") as fid:
        fid.write("\n".join(EToutStr))



if __name__ == "__main__":
    ## python FCpowermap.py --fc_powermap=./thermal_case.csv

    args = arg().parse_args()
    FCpowermap2RHSCETmhs(args.fc_powermap, args.outputFolder, args.outputName)
    

import os
import sys
import shutil
import re
import math
import argparse
import copy

def createCASE(root, caseName, subFolders=["DB"]):
    caseFolder = os.path.join(root, caseName)
    
    if not os.path.isdir(caseFolder):
        os.makedirs(caseFolder, 0o755)
    else:
        ### remove the existed case ###
        contents = [os.path.join(caseFolder, i)  for i in os.listdir(caseFolder)]
        [shutil.rmtree(i) if os.path.isdir(i) and not os.path.islink(i) else os.remove(i) for i in contents]

    
    ### create sub-folders ####
    subFolders = subFolders
    for f in subFolders:
        _subFolder = os.path.join(caseFolder, f)
        if not os.path.isdir(_subFolder):
            os.makedirs(_subFolder, 0o755)
    
    return caseFolder

def createETscript(paraDict, template, outputFolder="./", outputName="DEMO_et.tcl"):
    if not os.path.isfile(template):
        print("<ERROR> ET template script not specified: {}".format(template))
        return
    
    newStr = []
    with open(template, "r") as fid:
        for ll in fid:
            ll = ll.split("\n")[0]
            replace = re.match(r"(.*)<\$(.*)>.*", ll)
            if replace:
                #print(replace.group(1), replace.group(2), paraDict[replace.group(2)])
                replaceStr = replace.group(1)+paraDict[replace.group(2)]
                newStr.append(replaceStr)
            else:
                newStr.append(ll)
    
    outPath = os.path.join(outputFolder, outputName)
    with open(outPath, "w") as fid:
        fid.write("\n".join(newStr))
    
    return outPath

def simpleCalHTC(totalPWR, designArea, deltaT=10):
    ### unit: power (mW), length (um) ###
    ## PWR: mW --> W,  length: um --> m ##
    pwr = float("{:.6f}".format(float(totalPWR)*0.001))
    length = float("{:.8f}".format((float(designArea[2])-float(designArea[0]))*0.000001))
    width = float("{:.8f}".format((float(designArea[3])-float(designArea[1]))*0.000001))
    pwrDensity = float("{:.3f}".format(pwr/(length*width)))

    HTC = float("{:.1f}".format(pwrDensity/deltaT))
    return HTC

def viewImg(imgPath):
    import matplotlib.pyplot as plt
    import matplotlib.cbook as cbook

    if not os.path.isfile(imgPath):
        print("<ERROR> image path {} not found")
        return
    
    with cbook.get_sample_data(imgPath) as img_fid:
        image = plt.imread(img_fid)
    
    fig, ax = plt.subplots()
    im = ax.imshow(image)
    plt.show()

def saveGridImagesWithCBar(XX, YY, vmin, vmax, imgList,
                           caseFolder="./", imgName="merged.png", isShowImg=False):
    import matplotlib.pyplot as plt
    import numpy as np

    import matplotlib.cbook as cbook
    import matplotlib.cm as cm
    from mpl_toolkits.axes_grid1 import AxesGrid

    fig = plt.figure(figsize=(XX*5,YY*5))
    grid = AxesGrid(fig, 111, nrows_ncols=(YY, XX), axes_pad=0.05, cbar_mode="single",
                    cbar_location="right", cbar_pad=0.1)

    for i, ax in enumerate(grid):
        ax.set_axis_off()
        if i > len(imgList)-1:
            continue
    
        with cbook.get_sample_data(imgList[i]) as img_file:
            img = plt.imread(img_file)
    
        im = ax.imshow(img, vmin=vmin, vmax=vmax, cmap="coolwarm")

    cbar = ax.cax.colorbar(im)
    cbar = grid.cbar_axes[0].colorbar(im)

    cbar.ax.set_yticks(np.linspace(vmin, vmax, num=5))

    if isShowImg:
        imgPath = os.path.join(caseFolder, imgName)
        plt.savefig(imgPath, bbox_inches="tight")
        plt.close(fig)
        print("save image: {}".format(imgPath))
        viewImg(imgPath)
    else:
        imgPath = os.path.join(caseFolder, imgName)
        plt.savefig(imgPath, bbox_inches="tight")
        plt.close(fig)
        print("save image: {}".format(imgPath))


def submitJob(runcmd, cores=16, mem=256, runcshPath="./run.csh", \
              progressBar=None, checkFiles=None):
    import subprocess
    import time

    with open(runcshPath, "w") as fid:
        fid.write("\n".join(runcmd))
    
    os.system("chmod +x {}".format(runcshPath))
    
    machine = "SLES15SP4 && {}C && {}G".format(str(cores), str(mem))
    machine = "SLES15SP4"
    cmd = ["nbjob", "run", "--target", "zsc9_normal", "--qslot", "/IFS/FTE/GENERAL", \
           "--class", machine, runcshPath]
    cmd = ["nbjob", "run", "--target", "zsc9_dts", "--qslot", "/de/pdk/dev/sl_int", "--class", machine, runcshPath]
    
    PP = subprocess.Popen(cmd)
    PP.wait()
    time.sleep(5.0)
    #print(PP.returncode)
    if PP.returncode == 0:  ### return zero --> successful
        #print(checkFiles)
        if not progressBar is None:
            while True:
                checkAll = True
                for f in checkFiles:
                    if os.path.isfile(f):
                        pass
                    else:
                        checkAll = False
                
                if checkAll:
                    break

                if progressBar.value >= 100:
                    progressBar.value = 0
                
                progressBar.value += 1
                time.sleep(0.1)
                progressBar.description = "Running"
            
            progressBar.description = "Done"
    else:
        print("<ERROR> Job is not submitted")
        return False
    
    return True



if __name__ == "__main__":
    ## python FCpowermap.py --fc_powermap=./thermal_case.csv

    args = arg().parse_args()
    #FCpowermap2RHSCETmhs(args.fc_powermap, args.outputFolder, args.outputName)

    #designArea = [0, 0, 48, 48]
    #FCipf2RHSCETmhs(args.fc_powermap, args.outputFolder, args.outputName, designArea)

    #ipfPath = "./pwd.mhs"
    #plotIPF(ipfPath)

    FCpwrView = FCPowerView(args.fc_powerfile, "CSV")
    FCpwrView.RHSCETmhs()

    #topPwrCells = FCpwrView.getTopNHotSpots()
    topPwrCells = []
    FCpwrView.plot(highlighted=topPwrCells)
    

#!/bin/env python
import sys
import os
import re
import glob
from optparse import OptionParser
import logging
import random

#logging.basiccontig(filename="debug.log", formata"(t(levelname)s]%(message)s", level=logging INFO)
logging.basicConfig(format="[%(levelname)s] %(message)s", level=logging.INFO)

class Node:
    def __init__(self, cellName, inNum, outNum):
        self.cellName = cellName
        self.inNum = inNum
        self.outNum = outNum
        self.out = []
        self.useIn = 0
        self.useOut = 0
        self.instName = ""
        self.inNetName = []
        self.outNetName = []
        for i in range(0, outNum):
            self.out.append([])

class REMatcher(object):
    def __init__(self, matchstring):
        self.matchstring = matchstring

    def match(self, regexp):
        self.rematch = re.match(regexp, self.matchstring)
        return bool(self.rematch)

    def search(self, regexp):
        self.rematch = re.search(regexp, self.matchstring)
        return bool(self.rematch)

    def group(self, i):
        return self.rematch.group(i)

#parse LEF file to get pin direction
def parseLEF(cellInfo, lefFile):
    if not os.path.exists(lefFile):
       logging.error("LEF file %s is not found" % lefFile)
       sys.exit(1)

    cellName = None
    pinName = None
    pinType = None
    pinDir = None
    f = open(lefFile)
    for line in f:
        line = line.strip()
        if line == "": continue
        m = REMatcher(line)
        if m.search("^#"): continue

        if "MACRO" in line:
            cellName = line.split("MACRO ")[-1]
            print("cellName: {}".format(cellName))
            cellInfo[cellName] = {"in":[], "out":[], "pin_cnt":0}


        if m.search("MACRO\s+(\S+)."):
           pass
        #   cellName = m.group(1)
        #   print ("first %s" % cellName)
        #   cellInfo[cellName] = {
        #        "in": [],
        #        "out": []
        #   }
        elif m.search("PIN\s+(\S+)"):
            pinName = m.group(1)
        elif m.search("DIRECTION\s+(\S+)"):
            pinDir = m.group(1)
        elif m.search("USE\s+(\S+)"):
            pinType = m.group(1)
            if pinType not in ["POWER", "GROUND"]:
                cellInfo[cellName]["pin_cnt"] += 1
        elif m.search("END\s+(\S+)"):
            if m.group(1) == cellName:
                 cellName == None
            elif m.group(1) == pinName:
                if pinType == "SIGNAL" or pinType == None:
                    if pinDir == "INPUT":
                        cellInfo[cellName]["in"].append(pinName)
                    elif pinDir == "OUTPUT":
                        cellInfo[cellName]["out"].append(pinName)
                pinName = None
                pinDir = None
                pinType = None
    f.close()
     # remove physical cells which should be inserted in ApR stage
#    for key in sorted(cellInfo.keys()):
#        if re.search ("EILL|TAPCELL|BOUNDARY|DCAP", key):
#           cellInfo.pop(key, None)
#        else:
#           pass
#           #logging.info("%s, in: %s, out: %s" % (key, " ".join(ce

def parseVLG(cellInfo, vlgFile):
    f= open(vlgFile, "r")
    cellList = {}
    for line in f:
        line = line.strip()
        if line == "": continue
        m = REMatcher(line)

        if m.search("(\s+)\s+(\s+)\s+\("):
            cellName = m.group(1)
            if cellName not in cellInfo: continue

            if cellName not in cellList:
                cellList[cellName] = 1
            else:
                cellList[cellName] += 1
    f.close()

    f = open("vlg2cellList", "w")
    for key in cellList.keys():
        f.write("%s %d\n" % (key, cellList[key]))
    f.close()

    return "vlg2cellList"

# get number of cells used in design
def useCells(cellInfo, cellFile, cellMulti):
    if cellFile == None:
        logging.info("cell list is not specity, one instance for each cell") 
        f = open("%s_multi" % cellFile, "w")
        for key in cellInfo.keys():
            if cellMulti < 1.0 + 1e-8:
                cellInfo[key]["num"] = 1
            else:
                cellInfo[key]["num"] = int(round(cellMulti))
            f.write("%s %d\n" % (key, cellInfo[key]["num"]))
        f.close()
   
    if not os.path.exists(cellFile):
        logging.error("cell list %s is not found" % cellFile)
        sys.exit(1)

    f = open("%s_pin_cnt" % cellFile, "w")
    for key in cellInfo.keys():
        f.write("%s %d\n" % (key, cellInfo[key]["pin_cnt"]))
    f.close()

    fo = open("%s_multi" % cellFile, "w")
    f = open(cellFile)
    lineNum = 0
    for line in f:
        lineNum += 1
        line = line.strip()
        print ("%s" % line)
        if line == "" or re.search("^#", line): continue
        arr = line.split()
        if arr[0] not in cellInfo:
            logging.warning("%s is not defined in LEF file" % (arr[0]))
            sys.exit(1)
        else:
            if len(arr) != 2:
                if cellMulti <1.0 + 1e-8:
                    cellInfo[arr[0]]["num"] = 1
                else:
                    cellInfo[arr[0]]["num"] = int(round(cellMulti))
            else:
                cellInfo[arr[0]]["num"] = int(round(int(arr[1])*cellMulti))
                if cellInfo[arr[0]]["num"] < 1:
                    cellInfo[arr[0]]["num"] = 1
            fo.write("%s %d\n" % (arr[0], cellInfo[arr[0]]["num"]))
    f.close()
    fo.close()

    #remove cells if not in cell list
    for key in cellInfo.keys():
        if "num" not in cellInfo[key]:
            cellInfo.pop(key, None)

# build up the graph tor cells
def genGraph(cellInfo, graph):
    keys = cellInfo.keys()
    keys.sort(reverse=True)
    for key in keys:
        for i in range(0, cellInfo[key]["num"]):
            graph.append(Node(key, len(cellInfo[key]["in"]), len(cellInfo[key]["out"])))

    random.shuffle(graph)

    for i in range(0, len(graph)):
        graph[i].instName = "DC1_%d" % i

# link global/local nets
def linkNet(graph, netRatio, numInPad):
    numNode = len(graph)

    numCellIn = 0
    numCellOut = 0
    numCellNotInLoop = 0
    for i in range(0, numNode):
        curNode = graph[i]
        numCellOut += curNode.outNum
        numCellIn += curNode.inNum
        if curNode.inNum == 0 and curNode.outNum == 0:
            numCellNotInLoop += 1

    if (numCellIn-numInPad) < (numNode-numCellNotInLoop):
        logging.error("number of input pad should <= %d" % (numCellIn+numCellNotInLoop-numNode))
        sys.exit(1)

    # form a cycle
    for i in range(0, numNode):
        print ("Node: %s" % numNode)
        curNode = graph[i]
        nextNodeNum = (i+1) % numNode
        nextNode = graph[nextNodeNum]
        #print("graph: {}, graph[1]: {}".format(graph, graph[0]))
        #print("curNode.outNum: {}".format(curNode.outNum))

        if curNode.outNum == 0:
            backTraceCount = 1
            while True:
                curNodeNum = (i-backTraceCount+numNode) % numNode
                if curNodeNum == i:
                    print ("%s" % curNodeNum)
                    logging.error("chosen cells cannot form a cycle")
                    sys.exit(1)
                curNode = graph[curNodeNum]
                if curNode.outNum != 0: break
                backTraceCount += 1

            while nextNode.inNum == 0:
                nextNodeNum = (nextNodeNum+1) % numNode
                nextNode = graph[nextNodeNum]

            if nextNode.useIn == 0:
                curNode.useOut -= 1
            else:
                continue

        while curNode.useOut < curNode.outNum:
            if nextNode.useIn < nextNode.inNum:
                curNode.out[curNode.useOut].append(nextNodeNum)
                curNode.useOut += 1
                nextNode.useIn += 1

            nextNodeNum = (nextNodeNum+1) % numNode
            if nextNodeNum == i and curNode.useOut < curNode.outNum:
                logging.error("chosen cells cannot form a cycle")
                sys.exit(1)

            nextNode = graph[nextNodeNum]

    # random judge for global/local net and link
    for i in range(0, numInPad):
        targetNodeNum = random.randint(0, numNode-1)
        targetNode = graph[targetNodeNum]
        if targetNode.useIn < targetNode.inNum:
            targetNode.useIn += 1
            targetNode.inNetName.append(i)

    for i in range(0, numNode):
        curNode = graph[i]
        localShift = 0
        for j in range(0, curNode.inNum-curNode.useIn):
            if random.random() < netRatio:
                globalNetConnect = False
                while not globalNetConnect:
                    targetNodeNum = random.randint(0, numNode-1)
                    if abs(targetNodeNum-i) <= 3: continue

                    targetNode = graph[targetNodeNum]
                    for k in range(0, targetNode.outNum):
                        if i not in targetNode.out[k]:
                          targetNode.out[k].append(i)
                          globalNetConnect = True
                          break
            else:
                localNetConnect = False
                base = (i-2) % numNode
                while not localNetConnect:
                    targetNodeNum = (base-localShift+numNode) % numNode
                    localShift += 1
                    if targetNodeNum == i:
                        logging.error("Node %d cell %s %s cannot connect a local net" % (i, curNode.instName, curNode.cellName))
                        sys,exit(1)

                    targetNode = graph[targetNodeNum]
                    for k in range(0, targetNode.outNum):
                        if i not in targetNode.out[k]:
                             targetNode.out[k].append(i)
                             localNetConnect = True
                             break

    # generate net name
    netCount = numInPad
    for i in range(0, numNode):
        curNode = graph[i]
        for j in range(0, curNode.outNum):
            curNode.outNetName.append(netCount)
            netLoad = curNode.out[j]
            for k in range(0, len(netLoad)):
                graph[netLoad[k]].inNetName.append(netCount)
            netCount += 1

    return netCount

    # output netlist in verilog
def outNetlist(cellInfo, graph, designName, numInPad, numOutPad, netCount):
    f = open("%s.v" % designName, "w")

    f.write("module %s (" % designName)
    
    outNetList = []
    if numOutPad > 0:
        usedOutNet = []
        for i in range(0, netCount-numInPad):
            usedOutNet.append(False)

        outNet = random.randint(0, netCount-numInPad-1)
        f.write(" I%d", outNet+numInPad)
        outNetList.append(outNet)
        usedOutNet[outNet] = True
        for i in range(0, numOutPad-1):
            while True:
                outNet = random.randint(0, netCount-numInPad-1)
                outNetList.append(outNet)
                if not usedOutNet[outNet]:
                    f.write(", I%d", outNet+numInPad)
                    usedOutNet[outNet] = True
                    break

    if numInPad > 0:
        if numOutpad > 0:
             f.write(", IO")
        else:
             f.write(" IO")

        for i in range(1, numInPad-1):
             f.write(", I%d", i)

    f.write(" );\n\n")

    if numOutPad > 0:
        f.write("output I%d" % (outNetList[0]+numInPad))
        for i in range(1, len(outNetList)):
            f.write(", I%d" % (outNetList[i]+numInPad))
        f.write(";\n\n")

    if numInPad > 0:
        f.write("input I0")
        for i in range(1, numInPad):
            f.write(", I%d" % i)
        f.write(";\n\n")

    f.write("wire I0")
    for i in range(1, netCount):
        f.write(", I%d" % i)
    f.write(";\n\n")

    for i in range(0, len(graph)):
        curNode = graph[i]
        inPin = cellInfo[curNode.cellName]["in"]
        outPin = cellInfo[curNode.cellName]["out"]
        f.write("%s %s (" % (curNode.cellName, curNode.instName))
        for j in range(0, curNode.outNum-1) :
            f.write(" .%s(I%d)," % (outPin[j], curNode.outNetName [j]))
        if curNode .outNum > 0:
            f.write(" .%s(I%d)" % (outPin[-1], curNode.outNetName[-1]))
            if curNode.inNum > 0:
                f.write(",")
        for j in range (0, curNode.inNum-1) :
            f.write(" .%s(I%d)," % (inPin[j], curNode.inNetName[j]))
        if curNode.inNum > 0:
            f.write(" .%s(I%d)" % (inPin[-1], curNode.inNetName[-1]))
        f.write(" );\n")
    f.write("\nendmodule\n")
    f.close()
def main():
    usage = "Usage: %prog [options]"
    parser = OptionParser(usage)
    parser.add_option("--lef", action = "store", help = "lef file contain a1l cells")
    parser.add_option("--gds", action = "store", help = "gds file contain a11 cells")
    parser.add_option("--layer_map", action = "store",help = "layer mapping file for tpr")
    parser.add_option("--top", action = "store", help = "(optional) top design name, default = netlistg", default = "netiistg")
    parser.add_option("--cell", action = "store", help = "(optional) cell list and count, default use all cells and conut = 1")
    parser.add_option("--vlg", action = "store",help ="(optional) automatic generate cell list from input verilog")
    parser.add_option("--multi", action = "store", type = "float",help="(optional) multiply cell count by a constant, detault = 1.0", default =1.0)
    parser.add_option("--ratio", action="store", type="float",help ="ratio for global nets (0.0~1.0)")
    parser.add_option("--num_input", action = "store", type = "int", help = "(optional) number of input pad, detault = 0", default = 0)
    parser.add_option("--num_output", action = "store", type = "int", help = "(optional) number of output pad, detault = 0", default = 0) 
    parser.add_option("--random_seed", action = "store",type = "int", help = "(optional) random seed, detault = 0", default = 0)

    (options,args) = parser.parse_args()

    if options.lef == None and options.gds == None:
        logging,error("std cell lef file or gds file should be specify")
        sys.exit(1)
    elif options.ratio == None:
        logging.error("Global net ratio should be specify")
        sys.exit(1)
    elif options.ratio < -1e-8 or options.ratio > 1.0+1e-8:
        logging,error("Global net ratio should be in range 0.0~1.0")
        sys.exit(1)
    elif options.gds != None and options.lef != None:
        logging.error("Cannot specify std cell gds and lef simultaneously")
        sys.exit(1)
    elif options.gds != None and options.layer_map == None:
        logging.error("please specify layer mapping file")
        sys.exit(1)
    elif options.cell != None and options.vlg != None:
        logging.error("Cannot specify cell list and verilog simultaneously")
        sys.exit(1)

    lefFile = options.lef
    gdsFile = options.gds
    layerMapFile = options.layer_map
    designName = options.top
    cellFile = options.cell
    vlgFile = options.vlg
    cellMulti = options.multi
    netRatio = options.ratio
    numInPad = options.num_input
    numOutPad = options.num_output

    randomSeed = options.random_seed
    if randomSeed == None:
        random.seed(0)
    else:
        random.seed(randomSeed)

    cellInfo = dict()
    if gdsFile != None:
        lefFile = gds2lef(gdsFile, layerMapFile)
    parseLEF(cellInfo, lefFile)
    # write cell_list

    if vlgFile != None:
        cellFile = parseVLG(cellInfo, vlgFile)
    useCells(cellInfo, cellFile, cellMulti)

    graph = []
    genGraph(cellInfo, graph)
    netCount = linkNet(graph, netRatio, numInPad)
    outNetlist(cellInfo, graph, designName, numInPad, numOutPad, netCount)

if __name__ == "__main__": main()

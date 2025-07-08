import os
import sys
import argparse
import json

from batchSetups import simpleTSFbatch

def arg():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--JSON", type=str, required=True, help="JSON configuration") 
    parser.add_argument(
        "--caseFolder", type=str, required=False, default="./NgBatch", help="Create non-GUI batch run folder")

    return parser


if __name__ == "__main__":
    ### command: python NgBatchMode.py --JSON=./T_CaseTest.json --caseFolder="./CASENAME"
    args = arg().parse_args()

    JSONSetupPath = args.JSON
    caseFolder = args.caseFolder

    batch = simpleTSFbatch.simpleTFSBatchRun(JSONSetupPath, caseFolder)
    batch.genCoreCase()
    batch.runBatch()

    print("<INFO> DONE")

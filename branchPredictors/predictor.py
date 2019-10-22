#!/usr/bin/python3

import sys


TABLE_SIZE=4096

def alwaysTaken(trace):
    predictedTrace = []
    stats = {"error": 0, "numberOfBranches": 0}
    
    for line in trace:
        split = line.split(" ")
        gt = split[1][:-1] 
        print(split[0] + " 0")
        if gt != "0":
            stats["error"] += 1
        stats["numberOfBranches"] += 1
    return stats



def updateBranchState(branchState, taken):
    if not taken :
        branchState -= 1
    else:
        branchState += 1

    branchState = 0 if (branchState < 0)  else  branchState
    branchState = 3 if (branchState > 3)  else  branchState
    return branchState

def twoBit(trace):
    table = {}
    stats = {"error": 0, "numberOfBranches": 0}

    for line in trace:
        split = line.split(" ")
        index = str(int(split[0][7:]) % TABLE_SIZE)
        gt = split[1]
        predict = None
        try :
            if table[index] < 2:
                predictTaken = 0
            else:
                predictTaken = 1
        except(KeyError):
            table[index] = 0
            predictTaken = 0
   
        if predictTaken != int(gt) :
       #     print("predicted " + str(predictTaken) + " but gt was : " + str(line))
            stats["error"]  += 1
        table[index] = updateBranchState(table[index], bool(int(gt)))

       # if table[index] >= 2 and predictTaken:
       #     stats["error"] += 1
       # elif table[index] < 2 and not predictTaken:
       #     stats["error"] += 1
        stats["numberOfBranches"] += 1

    return stats


def main(tracePath, predictor):
    stats = {}
    with open(tracePath, "r") as trace:
        if(predictor == "alwaysTaken"):
            stats = alwaysTaken(trace)
        if(predictor == "2bit"):
            stats = twoBit(trace)
    print("Number of branches: " + str(stats["numberOfBranches"]))
    print("Success rate : "  +  str(100 - (stats["error"] * 100)/stats["numberOfBranches"]))



main(sys.argv[1], sys.argv[2])

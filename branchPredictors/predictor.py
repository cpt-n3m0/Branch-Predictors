#!/usr/bin/python3

import sys


TABLE_SIZE=4096
GHR_SIZE=3

def alwaysTaken(trace):
    predictedTrace = []
    stats = {"error": 0, "numberOfBranches": 0}
    
    for line in trace:
        split = line.split(" ")
        gt = split[1][0] 
       # print(split[0] + " 1")
        if gt != "1":
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

def get2bitIndex(iAddress, tableSize):
    iAddressBits = "{0:b}".format(int(iAddress))
    leastSign = iAddressBits[-8:]
    return int(leastSign, 2) % TABLE_SIZE

def twoBit(trace):
    table = {}
    stats = {"error": 0, "numberOfBranches": 0}

    for line in trace:
        split = line.split(" ")
        index = get2bitIndex(split[0], TABLE_SIZE)
        gt = split[1][0]
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

        stats["numberOfBranches"] += 1

    return stats


def getGShareIndex(iAddress, pattern):
    iAddressBits = "{0:b}".format(int(iAddress))
    leastSign = iAddressBits[-8:]

    return int(leastSign, 2) ^  int(pattern, 2)

def shiftRegisterLeft(register, newEntry):
    register = register[1:]
    register += newEntry
    return register

def gShare(trace):
    globalHistoryRegister = "0" * GHR_SIZE
    predictionTable = {}
    stats = {"error": 0, "numberOfBranches": 0}

    for line  in trace:
        split = line.split(" ")
        index = getGShareIndex(int(split[0]), (globalHistoryRegister))
        gt = split[1][0]

        try :
            if predictionTable[index] < 2:
                predictTaken = 0
            else:
                predictTaken = 1
        except(KeyError):
            predictionTable[index] = 0
            predictTaken = 0
        if predictTaken != int(gt) :
            stats["error"]  += 1

        predictionTable[index] = updateBranchState(predictionTable[index], bool(int(gt)))
        globalHistoryRegister = shiftRegisterLeft(globalHistoryRegister, gt)
        stats["numberOfBranches"] += 1
    return stats


def main(tracePath, predictor):
    stats = {}
    with open(tracePath, "r") as trace:
        if(predictor == "alwaysTaken"):
            stats = alwaysTaken(trace)
        if(predictor == "2bit"):
            stats = twoBit(trace)
        if(predictor == "gShare"):
            stats = gShare(trace)
    print("Number of branches: " + str(stats["numberOfBranches"]))
    print("Success rate : "  +  str(100 - (stats["error"] * 100)/stats["numberOfBranches"]))



main(sys.argv[1], sys.argv[2])

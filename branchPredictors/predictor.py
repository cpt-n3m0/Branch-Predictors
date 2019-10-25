#!/usr/bin/python3

import sys
import json
import os


TABLE_SIZE= 4096
GHR_SIZE=4
ADDRESS_I_SIZE = 8

def alwaysTaken(trace):
    predictedTrace = []
    stats = {"error": 0, "numberOfBranches": 0}
    
    for line in trace:
        split = line.split(" ")
        gt = split[1] 
        pedicted = 1
        if predicted != int(gt):
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
    leastSign = iAddressBits[-ADDRESS_I_SIZE:]
#    print(leastSign)
    return hash(str(int(leastSign, 2))) % tableSize 

def twoBit(trace):
    predictionTable = {}
    stats = {"error": 0, "numberOfBranches": 0}

    for line in trace:
        split = line.split(" ")
        index = get2bitIndex(split[0], TABLE_SIZE)
#        print(index)
        gt = split[1][0]
        predict = None
        try :
            predictTaken = int(not (predictionTable[index] < 2))
            #if predictionTable[index] < 2:
            #    predictTaken = 0
            #else:
            #    predictTaken = 1
        except(KeyError):
            predictionTable[index] = 0
            predictTaken = 0
   
        if predictTaken != int(gt) :
       #     print("predicted " + str(predictTaken) + " but gt was : " + str(line))
            stats["error"]  += 1
        predictionTable[index] = updateBranchState(predictionTable[index], bool(int(gt)))

        stats["numberOfBranches"] += 1

    return stats


def getGShareIndex(iAddress, pattern, tableSize):
    iAddressBits = "{0:b}".format(int(iAddress))
    leastSign = iAddressBits[-ADDRESS_I_SIZE:]
#    print("address : " + leastSign)
    if(len(pattern) < len(leastSign)):
        pattern += "0" * abs(len(leastSign) - (len(pattern)))
#    print("pattern : " + pattern)

#    print("result  : " +("{0:b}".format(int(leastSign, 2) ^  int(pattern, 2))))
    return hash(str(int(leastSign, 2) ^  int(pattern, 2))) % tableSize

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
        index = getGShareIndex(split[0], (globalHistoryRegister), TABLE_SIZE)
        print(index)
        gt = split[1][0]

        if index in predictionTable :
            if predictionTable[index] < 2:
                predictTaken = 0
            else:
                predictTaken = 1
        else:
            predictionTable[index] = 0
            predictTaken = 0
        if predictTaken != int(gt) :
            stats["error"]  += 1

        predictionTable[index] = updateBranchState(predictionTable[index], bool(int(gt)))
        globalHistoryRegister = shiftRegisterLeft(globalHistoryRegister, gt)
        stats["numberOfBranches"] += 1
    return stats



def createProfile(trace, out):
    branchStatusTable = {}
    profile = {}
    counter = 0
    for line in trace:
        split = line.split(" ")
        gt = split[1][0]
        if split[0] in branchStatusTable:
            branchStatusTable[split[0]]["taken_count"] += int(gt)
            branchStatusTable[split[0]]["occurence"] += 1
            
        else:
            counter += 1
            branchStatusTable[split[0]] = {"occurence" : 1, "taken_count" : int(gt), "order" : counter}

    for branch in branchStatusTable :
        b = branchStatusTable[branch]
        profile[b["order"]] = int(((b["taken_count"] * 100)/b["occurence"]) > 50 )

    with open(out, "w") as outFile:
        outFile.write(json.dumps(profile, indent=4, sort_keys=True))
    with open("dump.out", "w") as dump :
        dump.write(json.dumps(branchStatusTable, indent=4, sort_keys=True))

def profiledPredict(trace, proFile):
    profile = json.load(proFile)
    branchMap = {}
    stats = {"error": 0, "numberOfBranches": 0}
    counter = 0
    for line in trace:
        split = line.split(" ")
        address = split[0]
        gt = split[1]
        if address not in branchMap:
            counter += 1
            branchMap[address] = counter
        if str(branchMap[address]) in profile:
            prediction = profile[str(branchMap[address])] 
        else:
            prediction = 0
        if prediction != int(gt):
            stats["error"] += 1

        
        stats["numberOfBranches"] += 1
    
    return stats







def main(tracePath, predictor, profile=None):
    stats = {}
    with open(tracePath, "r") as trace:
        if(predictor == "alwaysTaken"):
            stats = alwaysTaken(trace)
        if(predictor == "2bit"):
            stats = twoBit(trace)
        if(predictor == "gShare"):
            stats = gShare(trace)
        if(predictor == "createProfile"):
            createProfile(trace, os.path.basename(tracePath).split(".")[0] + ".profile")
        if(predictor == "profiled"):
            with open(profile, "r") as pf:
                stats = profiledPredict(trace, pf)
    if len(stats):
        print("Number of branches: " + str(stats["numberOfBranches"]))
        print("Success rate : "  +  str(100 - (stats["error"] * 100)/stats["numberOfBranches"]))


try :
    tracePath = sys.argv[1]
    command = sys.argv[2]
    if command == "profiled" :
        profile = sys.argv[3]
    else:
        profile = None
except:
    print("ERROR: insufficient number of arguments")
    sys.exit(-1)
main(tracePath, command, profile=profile )

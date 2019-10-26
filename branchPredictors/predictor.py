#!/usr/bin/python3

import sys
import json
import os


TABLE_SIZE= 4096
GHR_SIZE=4
ADDRESS_I_SIZE = 8

#Profiled config
HIGHLEVEL = True
TCOUNT_SIZE = 16
OCOUNT_SIZE = 16
BRANCHMAP_SIZE = PIS = 24

PROFILE_TABLE_SIZE = 24


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

def getLeastIndex(iAddress, tableSize, bitSize):
    iAddressBits = "{0:b}".format(int(iAddress))
    leastSign = iAddressBits[-bitSize:]
#    print(leastSign)
    return int(leastSign, 2) % tableSize 

def twoBit(trace):
    predictionTable = {}
    stats = {"error": 0, "numberOfBranches": 0}

    for line in trace:
        split = line.split(" ")
        index = getLeastIndex(split[0], TABLE_SIZE, ADDRESS_I_SIZE)
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



def createProfileLowLevel(trace, out):
    branchStatusTable = {}
    profile = {}
    counter = 0
    for line in trace:
        split = line.split(" ")
        iAddress = split[0]
        gt = split[1][0]
        index = getLeastIndex(iAddress, pow(2, PROFILE_TABLE_SIZE), PIS)
        if index in branchStatusTable:
            tCount = branchStatusTable[index]["taken_count"] 
            oCount = branchStatusTable[index]["occurence"] 
            branchStatusTable[index]["taken_count"] = tCount + int(gt) if tCount < pow(2, TCOUNT_SIZE) else tCount
            branchStatusTable[index]["occurence"] = oCount + 1 if oCount < pow(2, OCOUNT_SIZE) else oCount
            
        elif counter < pow(2, PROFILE_TABLE_SIZE):
            counter += 1
            branchStatusTable[index] = {"occurence" : 1, "taken_count" : int(gt), "order" : counter}
        else:
            print("profile table saturated.")
            

    for branch in branchStatusTable :
        b = branchStatusTable[branch]
        profile[b["order"]] = int(((b["taken_count"] * 100)/b["occurence"]) > 50 )

    if not os.path.exists("profiles"):
        os.makedirs("profiles")
    with open("profiles/" +out, "w") as outFile:
        outFile.write(json.dumps( profile, indent=4, sort_keys=True))
    with open("dump.out", "w") as dump :
        dump.write(json.dumps(branchStatusTable, indent=4, sort_keys=True))


def createProfileHighLevel(trace, out):
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

    if not os.path.exists("profiles"):
        os.makedirs("profiles")
    with open("profiles/" +out, "w") as outFile:
        outFile.write(json.dumps( profile, indent=4, sort_keys=True))
    with open("dump.out", "w") as dump :
        dump.write(json.dumps(branchStatusTable, indent=4, sort_keys=True))

def profiledPredict(trace, proFile):
    profile = json.load(proFile)
    branchMap = {}
    stats = {"error": 0, "numberOfBranches": 0}
    counter = 0
    for line in trace:
        split = line.split(" ")
        iAddress = split[0]
        gt = split[1]
        index = iAddress if HIGHLEVEL else getLeastIndex(iAddress, pow(2, BRANCHMAP_SIZE),  PIS) 
        if index not in branchMap:
            counter += 1
            branchMap[index] = counter
        if str(branchMap[index]) in profile:
            prediction = profile[str(branchMap[index])] 
        else:
            prediction = 1
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
            if HIGHLEVEL:
                createProfileHighLevel(trace, os.path.basename(tracePath).split(".")[0] + ".profile")
            else:
                createProfileLowLevel(trace, os.path.basename(tracePath).split(".")[0] + ".profile")
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

    if command in ["profiled", "createProfile"]:
        lvl = sys.argv[-1]
        if lvl == "--high":
            HIGHLEVEL = True
        elif lvl =="--low":
            HIGHLEVEL = False
        else:
            print("ERROR: missing level flag")
            sys.exit(-1)
except:
    print("ERROR: insufficient number of arguments")
    sys.exit(-1)
main(tracePath, command, profile=profile )

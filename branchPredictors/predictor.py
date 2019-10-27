#!/usr/bin/python3

import sys
import json
import os


TABLE_SIZE= 4096
GHR_SIZE=4
ADDRESS_I_SIZE = 8

#Profiled config
HIGHLEVEL = False
SINGLESTRUCTURE = False

TCOUNT_SIZE = 16
OCOUNT_SIZE = 16
PROFILE_TABLE_SIZE = 16
PIS = 16


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
    return int(leastSign, 2) ^  int(pattern, 2) % tableSize

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


def createProfileLowLevelSingleStructure(trace, out):
    profile = {}
    counter = 0
    lc = 0
    for line in trace:
        split = line.split(" ")
        iAddress = split[0]
        gt = split[1][0]
        exists = False
        for index in profile:
            entry = profile[index]
            if entry["tag"] == getLeastIndex(iAddress, pow(2, PROFILE_TABLE_SIZE), PIS):
                tCount = entry["taken_count"] 
                oCount = entry["occurence"] 
                entry["taken_count"] = tCount + int(gt) if tCount < pow(2, TCOUNT_SIZE) else tCount
                entry["occurence"] = oCount + 1 if oCount < pow(2, OCOUNT_SIZE) else oCount
                exists = True
                
        if not exists and counter < pow(2, PROFILE_TABLE_SIZE) :
            counter += 1
            profile[counter] = {"occurence" : 1, "taken_count" : int(gt), "tag" : getLeastIndex(iAddress, pow(2, PROFILE_TABLE_SIZE), PIS), "adviceBit": 0}
            if not counter % 100:
                print(counter)
        lc += 1
        if not lc % 1000:
            print("branch number: " + str(lc))
    for i in profile :
        entry = profile[i]
        entry["adviceBit"] = int(((entry["taken_count"] * 100)/entry["occurence"]) > 50 )

    if not os.path.exists("profiles"):
        os.makedirs("profiles")
    with open("profiles/ss_" + out, "w") as outFile:
        outFile.write(json.dumps( profile, indent=4, sort_keys=True))
#    with open("dump.out", "w") as dump :
#        dump.write(json.dumps(branchStatusTable, indent=4, sort_keys=True))


   

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
        profile[b["order"]] =  int(((b["taken_count"] * 100)/b["occurence"]) > 50)

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
        profile[b["order"]] =  int(((b["taken_count"] * 100)/b["occurence"]) > 50 )

    if not os.path.exists("profiles"):
        os.makedirs("profiles")
    with open("profiles/" +out, "w") as outFile:
        outFile.write(json.dumps( profile, indent=4, sort_keys=True))
    #with open("dump.out", "w") as dump :
        #dump.write(json.dumps(branchStatusTable, indent=4, sort_keys=True))


def profiledPredictSingleStructure(trace, proFile):
    profile = json.load(proFile)
    stats = {"error": 0, "numberOfBranches": 0}
    counter = 0

    for line in trace:
        split = line.split(" ")
        iAddress = split[0]
        gt = split[1]

        exists = False
        for i in profile:
            if profile[i]["tag"] == getLeastIndex(iAddress, pow(2, PROFILE_TABLE_SIZE),  PIS):
                prediction = int(profile[i]["adviceBit"])

        if not exists:
            prediction = 1

        #index = iAddress if HIGHLEVEL else getLeastIndex(iAddress, pow(2, PROFILE_TABLE_SIZE),  PIS) 
        if prediction != int(gt):
            stats["error"] += 1

        
        stats["numberOfBranches"] += 1
    
    return stats


def profiledPredict(trace, proFile):
    profile = json.load(proFile)
    branchMap = {}
    stats = {"error": 0, "numberOfBranches": 0}
    counter = 0
    for line in trace:
        split = line.split(" ")
        iAddress = split[0]
        gt = split[1]
        index = iAddress if HIGHLEVEL else getLeastIndex(iAddress, pow(2, PROFILE_TABLE_SIZE),  PIS) 
        if index not in branchMap:
            counter += 1
            branchMap[index] = counter
        if str(branchMap[index]) in profile:
            prediction = int(profile[str(branchMap[index])])
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
                print("creating high level profile...")                 
                createProfileHighLevel(trace, os.path.basename(tracePath).split(".")[0] + ".profile")
            else:
                if SINGLESTRUCTURE:
                    print("creating single structure profile...")                 
                    createProfileLowLevelSingleStructure(trace, os.path.basename(tracePath).split(".")[0] + ".profile")
                else:
                    print("creating profile...")                 
                    createProfileLowLevel(trace, os.path.basename(tracePath).split(".")[0] + ".profile")
        if(predictor == "profiled"):
            with open(profile, "r") as pf:
                if os.path.basename(profile)[:2] == "ss":
                    print("Single structure profiled")
                    stats = profiledPredictSingleStructure(trace, pf)
                else:
                    print("Profiled")
                    stats = profiledPredict(trace, pf)
    if len(stats):
        print("Number of branches: " + str(stats["numberOfBranches"]))
        print("Success rate : "  +  str(100 - (stats["error"] * 100)/stats["numberOfBranches"]))



def is_flag(arg):
    return arg[0] == "-"

try :
    tracePath = sys.argv[1]
    command = sys.argv[2]

    if command == "profiled" :
        profile = sys.argv[3]        
    else:
        profile = None
    
    
    for arg in sys.argv[2:]:
        if is_flag(arg):
            if arg.lower() == "--high":
                HIGHLEVEL = True
            elif arg.lower() == "--low":
                HIGHLEVEL = False
            elif arg.lower() == "--singlestructure":
                SINGLESTRUCTURE = True

except:
    print("ERROR: insufficient number of arguments")
    sys.exit(-1)
main(tracePath, command, profile=profile )

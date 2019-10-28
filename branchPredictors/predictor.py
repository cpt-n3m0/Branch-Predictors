#!/usr/bin/python3

import sys
import json
import os
import time


TABLE_SIZE= 4096
GHR_SIZE=8
ADDRESS_I_SIZE = 16

#Profiled config
HIGHLEVEL = False
SINGLESTRUCTURE = False

TCOUNT_SIZE = 16
OCOUNT_SIZE = 16
PROFILE_TABLE_SIZE = 16
PIS = 16


getTime = lambda: time.time() * 1000

def alwaysTaken(trace):
    predictedTrace = []
    stats = {"error" : 0, "numberOfBranches": 0, "uniqueBranches" : 0, "numberOfProfiledBranches": 0, "avg_branch_frequency": 0, "numberOfCollisions" : 0, "duration": 0}    
    start = getTime()
    for line in trace:
        split = line.split(" ")
        gt = split[1] 
        predicted = 1
        if predicted != int(gt):
            stats["error"] += 1
        stats["numberOfBranches"] += 1
    stats["duration"] = getTime() - start
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
    collisionMap = {}
    stats = {"error" : 0, "numberOfBranches": 0, "uniqueBranches" : 0, "numberOfProfiledBranches": 0, "avg_branch_frequency": 0, "numberOfCollisions" : 0, "duration": 0}
    start = getTime()
    for line in trace:
        split = line.split(" ")
        iAddress= split[0]
        gt = split[1][0]
        index = getLeastIndex(iAddress, TABLE_SIZE, ADDRESS_I_SIZE)
        if index not in collisionMap :
            collisionMap[index] = [iAddress]

        if iAddress not in collisionMap[index]:
            stats["numberOfCollisions"] += 1
            collisionMap[index].append(iAddress)

#        print(index)
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

    stats["duration"] = getTime() - start
    for b in collisionMap.values():
        stats["uniqueBranches"] += len(b)
    stats["avg_branch_frequency"] = stats["numberOfBranches"] / stats["uniqueBranches"]

    return stats


def getGShareIndex(iAddress, pattern, tableSize):
    iAddressBits = "{0:b}".format(int(iAddress))
    leastSign = iAddressBits[-ADDRESS_I_SIZE:]
    if(len(pattern) < len(leastSign)):
        pattern += "0" * abs(len(leastSign) - (len(pattern)))

    return( int(leastSign, 2) ^  int(pattern, 2)) % tableSize

def shiftRegisterLeft(register, newEntry):
    register = register[1:]
    register += newEntry
    return register

def gShare(trace):
    globalHistoryRegister = "0" * GHR_SIZE
    predictionTable = {}
    stats = {"error" : 0, "numberOfBranches": 0, "uniqueBranches" : 0, "numberOfProfiledBranches": 0, "avg_branch_frequency": 0, "numberOfCollisions" : 0, "duration": 0} 
    collisionMap = {}
    start = getTime()

    for line  in trace:
        split = line.split(" ")
        iAddress = split[0]
        gt = split[1][0]
        index = getGShareIndex(iAddress, (globalHistoryRegister), TABLE_SIZE)
        if index not in collisionMap :
            collisionMap[index] = [iAddress]

        elif iAddress not in collisionMap[index]:
            stats["numberOfCollisions"] += 1
            collisionMap[index].append(iAddress)

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

    for b in collisionMap.values():
        stats["uniqueBranches"] += len(b)
    stats["avg_branch_frequency"] = stats["numberOfBranches"] / stats["uniqueBranches"]
    stats["duration"] = getTime() - start

    return stats


def createProfileLowLevelSingleStructure(trace, out):
    profile = {}
    counter = 0
    stats = {"numberOfBranches": 0, "uniqueBranches" : 0, "numberOfProfiledBranches": 0, "avg_branch_frequency": 0, "numberOfCollisions" : 0, "duration": 0}
    collisionMap = {}
    start = getTime()
    for line in trace:
        split = line.split(" ")
        iAddress = split[0]
        gt = split[1][0]
        exists = False
        for index in profile:
            entry = profile[index]

            if entry["tag"] == getLeastIndex(iAddress, pow(2, PROFILE_TABLE_SIZE), PIS):
        
                if iAddress not in collisionMap[entry["tag"]]:
                    stats["numberOfCollisions"] += 1
                    collisionMap[entry["tag"]].append(iAddress)
            
                tCount = entry["taken_count"] 
                oCount = entry["occurence"] 
                entry["taken_count"] = tCount + int(gt) if tCount < pow(2, TCOUNT_SIZE) else tCount
                entry["occurence"] = oCount + 1 if oCount < pow(2, OCOUNT_SIZE) else oCount
                exists = True 
        if not exists and counter < pow(2, PROFILE_TABLE_SIZE) :
            counter += 1
            profile[counter] = {"occurence" : 1, "taken_count" : int(gt), "tag" : getLeastIndex(iAddress, pow(2, PROFILE_TABLE_SIZE), PIS), "adviceBit": 0}
            collisionMap[profile[counter]["tag"]] = [iAddress]
        
        stats["numberOfBranches"] += 1
    
    for i in profile :
        entry = profile[i]
        entry["adviceBit"] = int(((entry["taken_count"] * 100)/entry["occurence"]) > 50 )


    if not os.path.exists("profiles"):
        os.makedirs("profiles")
    with open("profiles/ss_" + out, "w") as outFile:
        outFile.write(json.dumps( profile, indent=4, sort_keys=True))
    
    stats["numberOfProfiledBranches"] = len(profile)
    for b in collisionMap.values():
        stats["uniqueBranches"] += len(b) 
    stats["avg_branch_frequency"] = stats["numberOfBranches"] / stats["uniqueBranches"]
    stats["duration"] = getTime() - start

    return stats
   

def createProfileLowLevel(trace, out):
    branchStatusTable = {}
    profile = {}
    counter = 0
    stats = {"numberOfBranches": 0, "uniqueBranches" : 0, "numberOfProfiledBranches": 0, "avg_branch_frequency": 0, "numberOfCollisions" : 0, "duration": 0}
    collisionMap = {}
    start = getTime()
    for line in trace:
        split = line.split(" ")
        iAddress = split[0]
        gt = split[1][0]
        index = getLeastIndex(iAddress, pow(2, PROFILE_TABLE_SIZE), PIS)

        if index not in collisionMap :
            collisionMap[index] = [iAddress]

        elif iAddress not in collisionMap[index]:
            stats["numberOfCollisions"] += 1
            collisionMap[index].append(iAddress)

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
        stats["numberOfBranches"] += 1            

    for branch in branchStatusTable :
        b = branchStatusTable[branch]
        profile[b["order"]] =  int(((b["taken_count"] * 100)/b["occurence"]) > 50)

    if not os.path.exists("profiles"):
        os.makedirs("profiles")
    with open("profiles/" +out, "w") as outFile:
        outFile.write(json.dumps( profile, indent=4, sort_keys=True))

    stats["numberOfProfiledBranches"] = len(profile)
    for b in collisionMap.values():
        stats["uniqueBranches"] += len(b) 
    stats["avg_branch_frequency"] = stats["numberOfBranches"] / stats["uniqueBranches"]
    stats["duration"] = getTime() - start

    return stats
   


def createProfileHighLevel(trace, out):
    branchStatusTable = {}
    profile = {}
    counter = 0
    seenBranches = []
    stats = {"numberOfBranches": 0, "uniqueBranches" : 0, "numberOfProfiledBranches": 0, "avg_branch_frequency": 0, "numberOfCollisions" : 0, "duration": 0}
    start = getTime()

    for line in trace:
        split = line.split(" ")
        iAddress = split[0]
        gt = split[1][0]
        
        if iAddress not in seenBranches:
            seenBranches.append(iAddress)

        if iAddress in branchStatusTable:
            branchStatusTable[iAddress]["taken_count"] += int(gt)
            branchStatusTable[iAddress]["occurence"] += 1
            
        else:
            counter += 1
            branchStatusTable[split[0]] = {"occurence" : 1, "taken_count" : int(gt), "order" : counter}
        stats["numberOfBranches"] += 1
    for branch in branchStatusTable :
        b = branchStatusTable[branch]
        profile[b["order"]] =  int(((b["taken_count"] * 100)/b["occurence"]) > 50 )

    if not os.path.exists("profiles"):
        os.makedirs("profiles")
    with open("profiles/" +out, "w") as outFile:
        outFile.write(json.dumps( profile, indent=4, sort_keys=True))
    #with open("dump.out", "w") as dump :
        #dump.write(json.dumps(branchStatusTable, indent=4, sort_keys=True))
    stats["numberOfProfiledBranches"] = len(profile)
    stats["uniqueBranches"] += len(seenBranches) 
    stats["avg_branch_frequency"] = stats["numberOfBranches"] / stats["uniqueBranches"]
    stats["duration"] = getTime() - start

    return stats

def profiledPredictSingleStructure(trace, proFile):
    profile = json.load(proFile)
    counter = 0
    stats = {"error": 0, "numberOfBranches": 0, "uniqueBranches" : 0, "numberOfProfiledBranches": 0, "avg_branch_frequency": 0, "numberOfCollisions" : 0, "duration": 0}

    collisionMap = {}
    start = getTime()


    for line in trace:
        split = line.split(" ")
        iAddress = split[0]
        gt = split[1]

        exists = False
        for i in profile:
            if profile[i]["tag"] == getLeastIndex(iAddress, pow(2, PROFILE_TABLE_SIZE),  PIS):
                
                if profile[i]["tag"] not in collisionMap:
                    collisionMap[profile[i]["tag"]] = [iAddress]
                elif iAddress not in collisionMap[entry["tag"]]:
                    stats["numberOfCollisions"] += 1
                    collisionMap[entry["tag"]].append(iAddress)
                
                prediction = int(profile[i]["adviceBit"])

        if not exists:
            prediction = 1

        if prediction != int(gt):
            stats["error"] += 1
        
        stats["numberOfBranches"] += 1
  
    for b in collisionMap.values():
        stats["uniqueBranches"] += len(b)
    stats["uniqueBranches"] += len(seenBranches)
    stats["avg_branch_frequency"] = stats["numberOfBranches"] / stats["uniqueBranches"]
    stats["duration"] = getTime() - start 
    return stats


def profiledPredict(trace, proFile):
    profile = json.load(proFile)
    branchMap = {}
    start = getTime()
    stats = {"error" : 0, "numberOfBranches": 0, "uniqueBranches" : 0, "numberOfProfiledBranches": 0, "avg_branch_frequency": 0, "numberOfCollisions" : 0, "duration": 0}
    collisionMap = {}
    counter = 0
    for line in trace:
        split = line.split(" ")
        iAddress = split[0]
        gt = split[1]
        index = iAddress if HIGHLEVEL else getLeastIndex(iAddress, pow(2, PROFILE_TABLE_SIZE),  PIS) 
        
        if index not in collisionMap :
            collisionMap[index] = [iAddress]

        elif iAddress not in collisionMap[index]:
            stats["numberOfCollisions"] += 1
            collisionMap[index].append(iAddress)
        
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
   
    for b in collisionMap.values():
        stats["uniqueBranches"] += len(b)
    stats["avg_branch_frequency"] = stats["numberOfBranches"] / stats["uniqueBranches"]
    stats["duration"] = getTime() - start

    return stats

#stats = {"error": 0, "numberOfBranches": 0, "duration" : 0, "numberOfCollisions" : 0}
#{"error" : 0, "numberOfBranches": 0, "uniqueBranches" : 0, "numberOfProfiledBranches": 0, "avg_branch_frequency": 0, "numberOfCollisions" : 0, "duration": 0}

def showStat(stats):
    print("branches      unique       collisions        frequency       runtime     errorRate")
    print(str(stats["numberOfBranches"]) + "\t" + str(stats["uniqueBranches"]) + "\t\t"+ str(stats["numberOfCollisions"]) + "\t\t" + str(round(stats["avg_branch_frequency"])) + "\t\t" + str(round(stats["duration"])) + "ms\t\t" + str(round(stats["errorRate"])) + "\t\t")

def analyse_dynamic(pred, traces, testFiles):
    tf_info = {}
    tstCounter = 0
    for tf in testFiles:
        tff = open(traces + "/" + tf, "r")
        tf_info[tf] = pred(tff)
        tf_info[tf]["errorRate"] =  (tf_info[tf]["error"] * 100)/tf_info[tf]["numberOfBranches"]
        tstCounter += 1
        print("\t\t\t\t" +  tf)
        print("-" * 100)
        showStat( tf_info[tf])
        print("-" * 100)
        print("")

    avg = {"error": 0 , "errorRate" : 0, "numberOfBranches": 0, "uniqueBranches" : 0, "numberOfProfiledBranches": 0, "avg_branch_frequency": 0, "numberOfCollisions" : 0, "duration": 0}
    for tf in tf_info:
        for stat in tf_info[tf] :
            avg[stat] += tf_info[tf][stat]

    for stat in avg:
        avg[stat] = avg[stat]/tstCounter

    print("\t\t\t\tAVERAGE STATS")
    print("+" * 100)
    showStat(avg)
    print("+" * 100)

def analysis(traces):
    # predictor data 
    global TABLE_SIZE 
    TABLE_SIZE = 0
    dPredictors = {"always taken": alwaysTaken, "2bits": twoBit, "gShare" : gShare}
    
    for predictor in dPredictors:
        print("\n\n")
        print("*********************\t\tAnalysing " + predictor + "\t\t ****************************")
        for predictorSize in [512, 1024, 2048, 4096, 7000]:
            TABLE_SIZE = predictorSize
            print("\t\t\t\tTABLE_SIZE = " + str(TABLE_SIZE))
            testFiles = ["chromium-1.out", "firefox-1.out", "libreoffice-1.out", "gcc-1.out"]
            results = analyse_dynamic(dPredictors[predictor], traces, testFiles)



def main(tracePath, cmd, profile=None):
    stats = {}
    if(cmd == "analyse"):
            analysis(tracePath)
            return
    with open(tracePath, "r") as trace:
        if(cmd == "alwaysTaken"):
            stats = alwaysTaken(trace)
        if(cmd == "2bit"):
            stats = twoBit(trace)
        if(cmd == "gShare"):
            stats = gShare(trace)
        if(cmd == "createProfile"):
            if HIGHLEVEL:
                print("creating high level profile...")                 
                stats = createProfileHighLevel(trace, os.path.basename(tracePath).split(".")[0] + ".profile")
            else:
                if SINGLESTRUCTURE:
                    print("creating single structure profile...")                 
                    stats = createProfileLowLevelSingleStructure(trace, os.path.basename(tracePath).split(".")[0] + ".profile")
                else:
                    print("creating profile...")                 
                    stats = createProfileLowLevel(trace, os.path.basename(tracePath).split(".")[0] + ".profile")
        if(cmd == "profiled"):
            with open(profile, "r") as pf:

                if os.path.basename(profile)[:3] == "ss_":
                    print("Single structure profiled")
                    stats = profiledPredictSingleStructure(trace, pf)
                else:
                    print("Profiled")
                    stats = profiledPredict(trace, pf)
    
    print(stats)
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

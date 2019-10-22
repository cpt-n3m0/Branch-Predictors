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



def check(branchState, taken):
    if (branchState == 0 and not taken):
        return 0
    if (branchState == 0 and taken):
        return 1
    if (branchState == 1 and not taken):
        return 0
    if (branchState == 1 and taken):
        return 2
    if (branchState == 2 and not taken):
        return 1
    if (branchState == 2 and taken):
        return 3
    if (branchState == 3 and not taken):
        return 2
    if (branchState == 3 and taken):
        return 3


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
        table[index] = check(table[index], bool(int(gt)))

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

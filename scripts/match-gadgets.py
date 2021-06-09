#!/usr/bin/env python3

import argparse
from pathlib import Path
import subprocess

PROJECTS = {'baseline':'freertos_microbenchmarks_clang', 
                   'baseline_mpu':'freertos_mpu_microbenchmarks_clang',
                   'kage':'microbenchmarks'}
DEVICE = 'demos/st/stm32l475_discovery/ac6'
OCD_CMD = 'program $PATH$ reset exit'

def findGadgetSource(gadgetList, objResult):
    # Generate Objdump dataset
    objLineList = objResult.split('\n')
    currentSection = ''
    # int(addr):'section:function' 
    funcTable = {}
    # 'section:function' : count
    result = {}
    # Build funcTable
    for line in objLineList:
        if 'Disassembly of' in line:
            currentSection = line.split(' ')[-1].replace(':', '')
        elif '>:' in line:
            address = int(line.split(' ')[0], 16)
            function = line.split('<')[1].split('>')[0]
            funcTable[address] = currentSection + ':' + function
    # Query all the gadgets
    for gadget in gadgetList:
        prevFunc = ''
        for addr in funcTable:
            if gadget < addr:
                # We found the function
                if not prevFunc in result:
                    result[prevFunc] = 1
                else:
                    result[prevFunc] += 1
                break
            else:
                prevFunc = funcTable[addr]
    return result

# Main routine
if __name__ == "__main__":
    # Argparse
    parser = argparse.ArgumentParser()
    # Optional custom workspace path
    parser.add_argument('--bin', type=Path, required=True)
    # Get arguments
    args = parser.parse_args()

    # Reject if input isn't a file
    if not args.bin.is_file():
        print('ERROR: Expect a binary file')
        exit()
    # Run ROPgadget
    ropProc = subprocess.run(['ROPgadget', '--thumb', '--bin',\
        args.bin.as_posix()], capture_output=True)
    ropResult = ropProc.stdout.decode()

    # Run objdump
    objProc = subprocess.run(['arm-none-eabi-objdump', '-d',\
        args.bin.as_posix()], capture_output=True)
    objResult = objProc.stdout.decode()
    
    # Process ROPgadget result
    ropGadgetAddrList = []
    ropGadgetList = ropResult.split('\n')
    for gadget in ropGadgetList:
        if ' : ' in gadget:
            ropGadgetAddrList.append(int(gadget.split(' : ')[0], 16))
    
    # Find source of each gadget
    result = findGadgetSource(ropGadgetAddrList, objResult)
    for entry in result:
        print(entry, ': ', result[entry])
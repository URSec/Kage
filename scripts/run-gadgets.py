#!/usr/bin/env python3

import argparse
from pathlib import Path
import re
import subprocess

PRESET = {'kage':Path('/home/artifact/Kage/workspace/coremark/demos/st/stm32l475_discovery/ac6/kage-coremark-3-threads/kage-coremark-3-threads.elf'),
          'freertos':Path('/home/artifact/Kage/workspace/freertos_coremark_clang/demos/st/stm32l475_discovery/ac6/baseline-coremark-3-threads/baseline-coremark-3-threads.elf')}

# Main routine
if __name__ == "__main__":
    # Argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', type=Path, 
        help="Specify the binary file to analyze")
    parser.add_argument('--preset', action='store_true', default=False,
        help="Use the CoreMark binary file (depending on the mode)")
    parser.add_argument('--mode', type=str,
        choices=['kage','freertos'],
        default='kage',
        help="Choose the mode (kage or freertos)")
    parser.add_argument('--secure_api', type=Path,
        default=Path('secure_api.conf'),
        help="Specify path to the list of secure API functions")
    parser.add_argument('--out_total', type=Path, required=False,
        help="Write the list of all gadgets to a file")
    parser.add_argument('--out_reachable', type=Path, required=False,
        help="Write the list of reachable gadgets to a file")
    parser.add_argument('--sh_script', type=Path,
        default=Path('find_filter_gadgets.sh'),
        help="Manually specify the location of the find_filter_gadgets.sh script")
    # Get arguments
    args = parser.parse_args()

    # Determine the binary file
    if (not args.f is None) == args.preset:
        print("ERROR: If using the preset, then no custom binary file is allowed.")
        print("If not using the preset, then a binary file is required.")
        exit(1)
    if args.preset:
        binPath = PRESET[args.mode]
    else:
        binPath = args.f

    # In kage mode, first find the range of untrusted code and store the string
    # to rangeStr.
    if args.mode == 'kage':
        objdumpStr = subprocess.run(['arm-none-eabi-objdump', '-h',
                                     binPath.as_posix()],
                                    capture_output=True).stdout
        objdumpStr = objdumpStr.decode('utf-8')
        # We only care about the boundaries of .text, the untrusted code
        p = re.compile('(?<= )[0-9a-f]+') # Match hex values separated by space
        rangeStr = None
        for line in objdumpStr.split('\n'):
            if '.text' in line:
                values = p.findall(line)
                # Should never reach here, but we should have a sanity check
                if len(values) < 3:
                    continue
                start = int(values[2], 16)
                end = start + int(values[1], 16)
                rangeStr = hex(start) + '-' + hex(end)
                break
        # A sanity check to ensure that we find the range successfully
        if rangeStr is None:
            print("ERROR: Could not find the range of untrusted code section.")
            exit(1)
    
    # Find all gadgets, regardless if they're reachable
    totalStr = subprocess.run(['sh', args.sh_script.as_posix(), '-f',
                               binPath.as_posix(), '-a', '-b'],
                              capture_output=True).stdout
    totalStr = totalStr.decode('utf-8')
    # Count number
    numTotal = totalStr.count('\n')
    # If requested, save the list of gadgets to file
    if not args.out_total is None:
        with args.out_total.open('w') as file:
            file.write(totalStr)
    print('Total gadgets found: ', numTotal)

    # Find reachable gadgets
    reachStr = ''
    # For freertos, all gadgets are reachable since there is no protection
    # at all.
    if args.mode == 'freertos':
        print('NOTE: All gadgets are reachable in FreeRTOS.')
        reachStr = totalStr
    else:
        reachStr = subprocess.run(['sh', args.sh_script.as_posix(), '-f',
                                   binPath.as_posix(), '-b', '-r', rangeStr],
                                  capture_output=True).stdout
        reachStr = reachStr.decode('utf-8')
    # Count number
    numReachable = reachStr.count('\n')
    # If requested, save the list of gadgets to file
    if not args.out_reachable is None:
        with args.out_reachable.open('w') as file:
            file.write(reachStr)
    print('Reachable gadgets: ', numReachable)

    # Count number of privileged stores in reachable gadgets

    # STR instructions (lt and gt are conditional suffixes that may appear
    # for stores inside an IT block)
    pPrivStore = re.compile(' (str[a-su-z]*(lt|gt)?) ')
    numPrivStore = len(pPrivStore.findall(reachStr))
    # STM/STMIA/STMEA/STMDB/STMFD instructions
    pPrivStoreMultiple = re.compile(' stm[a-z]* ')
    numPrivStore += len(pPrivStoreMultiple.findall(reachStr))
    # PUSH instructions
    pPrivPush = re.compile(' push[a-z]* ')
    numPrivStore += len(pPrivPush.findall(reachStr))
    print('Privileged stores in reachable gadgets: ', numPrivStore)
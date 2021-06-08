#!/usr/bin/env python3

import sys
import getopt
import os.path
import pdb
from pprint import pprint
import re

gadgets = dict()
stitchable = dict()
not_stitchable = dict()
def usage():
    print(f"./{os.path.basename(__file__)} -f <gadgetfile>")

def main(argv):

    gadgetfilename = ""
    INVERSE=False
    # Fetch arguments
    try :
        opts, args = getopt.getopt(argv, "hif:")
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt == "-h":
            usage()
            sys.exit()
        elif opt == "-f":
            gadgetfilename = arg
        if opt == "-i":
            INVERSE=True

    if not gadgetfilename:
        usage()
        sys.exit(2)

    # Open file containing gadgets
    with open(gadgetfilename) as fp:
        # Loop through each line containing a gadget
        for line in fp:
            # Sanity check, first word is an address
            a, g = line.split(":", 1)
            # Remove whitespace around gadget and address
            addr = int(a.strip(),16)
            gadget = g.strip()
            gadgetl = [x.strip() for x in gadget.split(";")]

            # Map gadget address to its instructions in dictionary
            gadgets[addr] = gadgetl
            

    # Set of regexes that make gadgets stitchable
    stitchers = [r'bx', r'bxne', r'bl', r'blx']
    # Set of regexes that describe instructions writing to pc
    pc_writers = [r'pop.*pc', r'ld[rm].*\spc']

    # instructions that are obviously stitchable
    for addr,gadget in gadgets.items():
        found = False
        # Stitchable if gadget ends in a return/call/jump to register
        for s in stitchers:
            x = re.compile(s)
            if x.match(gadget[-1]):
                stitchable[addr] = gadget
                found = True
                break
        if found:
            continue
        # Check if gadget instructions write to pc
        for p in pc_writers:
            x = re.compile(p)
            # Check each instruction in the current gadget
            for instr in gadget:
                if x.match(instr):
                    stitchable[addr] = gadget
                    pdb.set_trace()
                    found = True
                    break
            if found:
                break
        if found:
            continue

        # Check if branch to static address is the start of another gadget
        b = re.compile(r'b\.w.*#0x.*')
        if b.match(gadget[-1]):
            # Check if branch destination is a gadget address
            jumps_to = int(gadget[-1].split(" ")[-1][1:],16)
            if jumps_to in gadgets:
                stitchable[addr] = gadget
                continue
            
    # output non-stitchable gadgets
    if INVERSE:
        # Remove stitchable gadgets from gadgets list
        for addr in stitchable.keys():
            gadgets.pop(addr)

        for addr,gadget in gadgets.items():
            gadget_str = " ; ".join(gadget)
            print(f"{hex(addr)} : {gadget_str}")

    # output stitchable gadgets
    else :
        for addr,gadget in stitchable.items():
            gadget_str = " ; ".join(gadget)
            print(f"{hex(addr)} : {gadget_str}")



    
if __name__ == "__main__":
    main(sys.argv[1:])


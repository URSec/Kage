#!/usr/bin/env python3

import sys
import getopt
import os.path
import pdb
from pprint import pprint
import re

gadgets = dict()
stitchable = dict()

def usage():
    print(f"./{os.path.basename(__file__)} -f <gadgetfile>")

def main(argv):

    gadgetfilename = ""
    # Fetch arguments
    try :
        opts, args = getopt.getopt(argv, "hf:")
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt == "-h":
            usage()
            sys.exit()
        elif opt == "-f":
            gadgetfilename = arg

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
    stitchers = [r'pop.*pc', r'bx', r'bxne', r'bl', r'blx', r'^.+pc']
    # instructions that are obviously stitchable
    for addr,gadget in gadgets.items():
        # Obviously stitchable if gadget ends in a return/call/jump
        for s in stitchers:
            x = re.compile(s)
            if x.match(gadget[-1]):
                stitchable[addr] = gadget
                break
            
    # output stitchable gadgets
    for addr,gadget in stitchable.items():
        gadget_str = " ; ".join(gadget)
        print(f"{hex(addr)} : {gadget_str}")
    
    
if __name__ == "__main__":
    main(sys.argv[1:])


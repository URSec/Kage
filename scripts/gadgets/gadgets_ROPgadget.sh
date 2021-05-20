#!/usr/bin/env bash

while getopts ":bar:f:" flag
do
    case "${flag}" in
        b) BATCH=true;;
        a) ALL=true;;
        r) range=${OPTARG};;
        f) binary=${OPTARG};;
    esac
done

if [ -z "${binary}" ]
then
    echo "Usage: ./gadgets.sh [-b] [-a] [-r 0x...-0x...] -f <path_to_elf>"
    exit 1
fi

# Run ROPgadget to collect the set of gadget start addresses
if [ ! "$BATCH" = true ] ; then echo "Collecting gadget addresses..."; fi
# Run ROPgadget over a specified range if provided
if [ -z "${range}" ]
then
    gadgets=$(ROPgadget --thumb --binary ${binary} |
                  egrep ^0x)
else
    gadgets=$(ROPgadget --thumb --range "${range}" --binary ${binary} |
                  egrep ^0x)
fi

# No filtering. Directly emit ROPgadget output and exit
if [ "$ALL" = true ]
then
    while read -r gadget;
    do 
        echo $gadget
    done <<< $gadgets
    exit 0
fi

gadgets_addr=$(while IFS= read -r gadget; do
                   echo $gadget | cut -f 1 -d ' ' |
                       cut -c 3- |
                       sed 's/^0*//'
               done <<< "$gadgets")

# Collect function start addresses
if [ ! "$BATCH" = true ] ; then echo "Collecting function addresses..."; fi
functions=$(llvm-objdump -d ${binary} |
                egrep "<.*?>:" |
                cut -f 1 -d ' ')

# Collect instruction addresses that follow a call
if [ ! "$BATCH" = true ] ; then echo "Collecting addresses following callsites..."; fi
rettargets=$(llvm-objdump -d ${binary} |
                 awk "/[[:space:]]bl/{getline; print}" |
                 cut -f 2 -d " " |
                 tr -d ":")

# Filter gadgets only reachable within Kage's restricted control flow  
if [ ! "$BATCH" = true ] ; then echo "Filtering gadgets unreachable in Kage..."; fi
REACHABLE=$(
    for addr in $gadgets_addr
    do
        # Select gadget addresses aligned with the start of functions
        grep $addr <<< $functions
        # Select gadget addresses aligned with return targets
        grep $addr <<< $rettargets
    done | sort | uniq)

# Filter gadgets that depennd on instruction properties 
if [ ! "$BATCH" = true ] ; then echo "Filtering gadgets that rely on Kage-protected entities..."; fi
USABLE=$(
    while read -r addr;
    do
        # Skip current line if it's empty
        if [ -z "${addr}" ]; then continue; fi
        # Filter gadgets that rely on the Kage-protected link register
        FOUND=$(grep $addr <<< $gadgets | egrep -v "lr$")
        # Check if the address isn't filtered
        if [ ! -z "${FOUND}" ]
        then
            echo $FOUND
        fi
    done <<< $REACHABLE)

# Output
if [ ! "$BATCH" = true ] ; then echo "Usable gadgets:"; fi
while read -r gadget;
do
    echo $gadget;
done <<< $USABLE


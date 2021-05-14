#!/usr/bin/env bash

while getopts b: flag
do
    case "${flag}" in
        b) binary=${OPTARG};;
    esac
done

if [ -z "${binary}" ]
then
    echo "Usage: ./gadgets.sh -b <path_to_elf>"
    exit 1
fi

echo "Collecting function addresses..."
functions=$(llvm-objdump -d ${binary} | egrep "<.*?>:" | cut -f 1 -d ' ')

echo "Collecting gadget addresses..."
gadgets=$(ROPgadget --thumb --binary ${binary} |
              egrep ^0x)
gadgets_addr=$(while IFS= read -r gadget; do
                   echo $gadget | cut -f 1 -d ' ' |
                       cut -c 3- |
                       sed 's/^0*//'
               done <<< "$gadgets")

echo "Filtering gadgets reachable in Kage..."
for gadget in $gadgets_addr
do
    grep $gadget <<< $functions | while read -r addr; do grep $addr <<< $gadgets | egrep -v "lr$"; done
done | sort | uniq


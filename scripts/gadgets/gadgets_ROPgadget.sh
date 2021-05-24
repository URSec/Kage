#!/usr/bin/env bash


usage() {
  cat <<EOF

Usage: $(basename "${BASH_SOURCE[0]}") [-h] -f <path_to_file> [OPTIONS]"

This script produces a list of Kage-reachable gadgets for a given elf file using ROPgadget. 

Available options:

-h      Print this help and exit
-b      Omit procesing status prints
-a      Emit all gadgets, even those unreachable in Kage
-r 0x..-0x..              Emit gadgets within a specified address range
-s <secure_api_desc>      Specify a file containing newline separated names of reachable Secure API functions  

EOF
  exit
}

while getopts ":hf:bar:s:" flag
do
    case "${flag}" in
        h) usage;;
        f) binary=${OPTARG};;
        b) BATCH=true;;
        a) ALL=true;;
        r) range=${OPTARG};;
        s) SAPI=$(cat ${OPTARG});;
    esac
done

if [ -z "${binary}" ]
then
    echo "Usage: ./gadgets.sh -f <path_to_elf> [-b] [-a] [-r 0x...-0x...] [-s <path_secure_api>]"
    exit 1
fi

# Collect secure API function addresses
if [ ! "$BATCH" = true ] ; then echo "Collecting Secure API function addresses..."; fi
if [ ! -z "$SAPI" ] ; then 
    secure_api=$(llvm-objdump -d ${binary} |
                     egrep "<.*?>:" |
                     while read -r fun; do
                         name=$(cut -f 2 -d ' ' <<< $fun | tr -d '<>:')
                         if grep -q $name <<< $SAPI
                         then
                             echo -n $fun | cut -f 1 -d ' ' | sed 's/^0*//' | tr -d ' '
                         fi
                     done)
fi

# Run ROPgadget to collect the set of gadget start addresses
if [ ! "$BATCH" = true ] ; then echo "Collecting gadget addresses..."; fi
# Run ROPgadget over a specified range if provided
if [ ! -z "${range}" ]
then
    gadgets=$(ROPgadget --thumb --range "${range}" --binary ${binary} |
                  egrep "^0x")
else
    gadgets=$(ROPgadget --thumb --binary ${binary} |
                  egrep "^0x")
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

# Cut addresses from gadget descriptions 
gadgets_addr=$(while IFS= read -r gadget; do
                   echo $gadget | cut -f 1 -d ' ' |
                       cut -c 3- |
                       sed 's/^0*//'
               done <<< "$gadgets")
# Identify Kage-trusted code region from binary
if [ ! "$BATCH" = true ] ; then echo -n "Identifying trusted code region.."; fi
trusted_region=$(readelf -S ${binary} |
                   egrep -o "privileged_f.*?$" |
                   tr -s ' ' |
                   cut -d ' ' -f 3,5)
trusted_base=$(echo $trusted_region | cut -f 1 -d ' ')
trusted_max=$(echo $trusted_region | 
                  sed 's/ /+/' |
                  tr "a-f" "A-F" |
                  awk '{print "obase=16;ibase=16;"$1}' |
                  bc);

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
        # Skip gadgets in trusted region and not part of Secure API
        grep $addr <<< $secure_api
        if [[ "0x${addr}" -lt "0x${trusted_max}" && "0x${addr}" -gt "0x${trusted_base}" ]]
        then
            continue
        fi
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
        FOUND=$(grep "$addr :" <<< $gadgets | egrep -v "lr$")
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


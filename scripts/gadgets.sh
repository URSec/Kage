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

#functions=$(readelf -sW aws_demos.elf  | grep FUNC | grep -v HIDDEN | tr -s ' ' | cut -f 3 -d ' ')
echo "Collecting function addresses..."
functions=$(llvm-objdump -D aws_demos.elf | egrep "<.*?>:" aws_demos.s | cut -f 1 -d ' ')

echo "Collecting gadget addresses..."
gadgets=$(ROPgadget --thumb --binary ${binary} |
              egrep ^0x)
gadgets_addr=$(while IFS= read -r gadget; do
                   echo $gadget | cut -f 1 -d ' ' |
                       cut -c 3- |
                       sed 's/^0*//'
               done <<< "$gadgets")

echo "Finding function-aligned gadgets..."
for gadget in $gadgets_addr
do
    grep $gadget <<< $functions | while read -r addr; do grep $addr <<< $gadgets; done
done | sort | uniq
# for fun in ${functions}
# do
#     echo $fun | sed 's/^0*//'
#     echo $fun | sed 's/^0*//' | xargs -I{} grep {}  <<< "$gadgets_addr"
#     #grep "$gadget" <<< "$functions" | xargs -I{} grep {} <<< "$gadgets"
# done

# readelf -sW aws_demos.elf  | grep FUNC | grep -v HIDDEN | tr -s ' ' | cut -f 3 -d ' '


    
# for addr in $(egrep "<.*?>:" aws_demos.s | cut -f 1 -d ' ')
# do
#     grep $addr aws_demos_gadgets.txt
# done                                                                    

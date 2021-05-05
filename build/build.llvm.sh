#!/bin/sh

#
# Path to the project root directory.
#
ROOT_DIR=`dirname $0 | sed 's/$/\/../' | xargs realpath`

#
# Path to the LLVM source directory.
#
LLVM_SRC="$ROOT_DIR/llvm-project"

#
# Path to the LLVM build directory.
#
LLVM_BUILD="$ROOT_DIR/build/llvm"

###############################################################################

set -e

mkdir -p "$LLVM_BUILD" && cd "$LLVM_BUILD"

rm -rf CMakeCache.txt

export CC=clang
export CXX=clang++
export LD=clang
export AR=llvm-ar
export NM=llvm-nm
export RANLIB=llvm-ranlib
export READELF=llvm-readelf
export STRIP=llvm-strip

cmake -G Ninja                                                              \
      -DCMAKE_BUILD_TYPE=Release                                            \
      -DCMAKE_CXX_STANDARD=17                                               \
      -DLLVM_ENABLE_PROJECTS="clang;lld"                                    \
      -DLLVM_TARGETS_TO_BUILD="ARM;X86"                                     \
      -DLLVM_ENABLE_ASSERTIONS=ON                                           \
      -DLLVM_OPTIMIZED_TABLEGEN=ON                                          \
      -DLLVM_APPEND_VC_REV=OFF                                              \
      "$LLVM_SRC/llvm"

ninja

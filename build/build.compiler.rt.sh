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

#
# Path to the newlib install directory.
#
NEWLIB_INSTALL="$ROOT_DIR/build/newlib-cygwin/install"

#
# Path to the compiler-rt build directory.
#
COMPILER_RT_BUILD="$ROOT_DIR/build/compiler-rt"

#
# Path to the compiler-rt install directory.
#
COMPILER_RT_INSTALL="$ROOT_DIR/build/compiler-rt/install"

#
# The target for which to build compiler-rt.
#
TARGET="arm-none-eabihf"

#
# CFLAGS to use to build compiler-rt.
#
CFLAGS="--target=$TARGET"
CFLAGS="$CFLAGS -mcpu=cortex-m4"
CFLAGS="$CFLAGS -mfpu=fpv4-sp-d16"
CFLAGS="$CFLAGS -mfloat-abi=hard"
CFLAGS="$CFLAGS -mthumb"
CFLAGS="$CFLAGS -g"
CFLAGS="$CFLAGS -O3"
CFLAGS="$CFLAGS -ffunction-sections"
CFLAGS="$CFLAGS -fdata-sections"
CFLAGS="$CFLAGS -ffreestanding"
CFLAGS="$CFLAGS -fomit-frame-pointer"
CFLAGS="$CFLAGS -I$NEWLIB_INSTALL/arm-none-eabi/include"
CFLAGS="$CFLAGS -mexecute-only"
CFLAGS="$CFLAGS -mllvm -enable-arm-silhouette-str2strt"
CFLAGS="$CFLAGS -mllvm -enable-arm-silhouette-shadowstack"
#CFLAGS="$CFLAGS -mllvm -enable-arm-silhouette-cfi" # Do not enable CFI
CFLAGS="$CFLAGS -DSILHOUETTE"

#
# ASMFLAGS to use to build compiler-rt.
#
ASMFLAGS="--target=$TARGET"
ASMFLAGS="$ASMFLAGS -mcpu=cortex-m4"
ASMFLAGS="$ASMFLAGS -mfpu=fpv4-sp-d16"
ASMFLAGS="$ASMFLAGS -mfloat-abi=hard"
ASMFLAGS="$ASMFLAGS -mthumb"
ASMFLAGS="$ASMFLAGS -g"
ASMFLAGS="$ASMFLAGS -O3"
ASMFLAGS="$ASMFLAGS -ffunction-sections"
ASMFLAGS="$ASMFLAGS -fdata-sections"
ASMFLAGS="$ASMFLAGS -ffreestanding"
ASMFLAGS="$ASMFLAGS -fomit-frame-pointer"
ASMFLAGS="$ASMFLAGS -I$NEWLIB_INSTALL/arm-none-eabi/include"
ASMFLAGS="$ASMFLAGS -DSILHOUETTE"

###############################################################################

set -e

mkdir -p "$COMPILER_RT_BUILD" && cd "$COMPILER_RT_BUILD"

rm -rf CMakeCache.txt

cmake -G Ninja                                                              \
      -DCMAKE_BUILD_TYPE=Release                                            \
      -DCOMPILER_RT_INSTALL_PATH="$COMPILER_RT_INSTALL"                     \
      -DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY                        \
      -DCOMPILER_RT_OS_DIR="baremetal"                                      \
      -DCOMPILER_RT_BUILD_BUILTINS=ON                                       \
      -DCOMPILER_RT_BUILD_SANITIZERS=OFF                                    \
      -DCOMPILER_RT_BUILD_XRAY=OFF                                          \
      -DCOMPILER_RT_BUILD_LIBFUZZER=OFF                                     \
      -DCOMPILER_RT_BUILD_PROFILE=OFF                                       \
      -DCMAKE_C_COMPILER="$LLVM_BUILD/bin/clang"                            \
      -DCMAKE_AR="$LLVM_BUILD/bin/llvm-ar"                                  \
      -DCMAKE_NM="$LLVM_BUILD/bin/llvm-nm"                                  \
      -DCMAKE_RANLIB="$LLVM_BUILD/bin/llvm-ranlib"                          \
      -DCOMPILER_RT_BAREMETAL_BUILD=ON                                      \
      -DCOMPILER_RT_DEFAULT_TARGET_ONLY=ON                                  \
      -DLLVM_CONFIG_PATH="$LLVM_BUILD/bin/llvm-config"                      \
      -DCMAKE_C_COMPILER_TARGET="$TARGET"                                   \
      -DCMAKE_ASM_COMPILER_TARGET="$TARGET"                                 \
      -DCMAKE_C_FLAGS="$CFLAGS"                                             \
      -DCMAKE_ASM_FLAGS="$ASMFLAGS"                                         \
      "$LLVM_SRC/compiler-rt"

ninja install

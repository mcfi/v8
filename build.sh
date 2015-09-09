#!/bin/bash
# Before executing this file, remember to cd verifier and run
# build.sh there to build the verifier.
# Add -DNO_CFI to compiler flags to disable CFI instrumentation
# for the JITted code
export MCFI_SDK=/home/ben/MCFI/toolchain
export CXX="$MCFI_SDK/bin/clang++"
export CC="$MCFI_SDK/bin/clang"
export CPP="$CC -E"
export LINK="$MCFI_SDK/bin/clang++"
#make x64.debug disassembler=on snapshot=off werror=no -j4
make x64.release disassembler=on snapshot=off werror=no -j4

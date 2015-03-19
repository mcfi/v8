#!/bin/bash

export MCFI_SDK=/home/ben/MCFI/toolchain
export CXX="$MCFI_SDK/bin/clang++"
export CC="$MCFI_SDK/bin/clang"
export CPP="$CC -E"
export LINK="$MCFI_SDK/bin/clang++"
#make x64.debug disassembler=on snapshot=off werror=no -j4
make x64.release disassembler=on snapshot=off werror=no -j4

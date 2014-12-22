#!/bin/bash

#make x64.debug disassembler=on snapshot=off werror=no -j4
#CC="clang"
#CXX="clang++"
make x64.release disassembler=on snapshot=off werror=no -j4

#!/bin/bash

make x64.debug gdbjit=on disassembler=on snapshot=off werror=no -j4
#make x64.release disassembler=on snapshot=off werror=no -j4

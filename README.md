Introduction
==
This is a modified v8 JavaScript Just-In-Time (JIT) compiler that can be built with the MCFI/PICFI toolchain. The JIT comiler was modified to CFI-instrumented JITted code.

How to Build
==
1. First you need to build the MCFI/PICFI toolchain. Download it here at ```https://github.com/mcfi/MCFI``` and following the build instructions.

2. In the current directory, type ```make dependencies``` and ```./build.sh``` you are good to go. ```make dependencies``` would report some errors, which you could just ignore.

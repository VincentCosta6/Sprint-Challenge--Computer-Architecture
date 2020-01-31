#!/usr/bin/env python3

"""Main."""

import sys
from cpu import *

debug_mode = False

if len(sys.argv) == 3:
    debug_mode = sys.argv[2] == '-v'

cpu = CPU(8, 10000, debug_mode)

cpu.load(sys.argv[1])
cpu.run()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MANTA, the light chair (the one built at home): NOT a copy of the algorithm.
It runs manta_ribbon.py itself with the "light" preset (see PRESETS there):
a 70 kg sitter, walls at 75 % of the entry's, 15 % gyroid, 4 perimeters.
Verified by manta_strength_check_personal.py (weakest glued check ~1.6x).
Do NOT use this for the competition submission.

RUN:  python manta_ribbon_personal.py      (writes MANTA_PERSONAL/)
Other scripts can `import manta_ribbon_personal` exactly like manta_ribbon.
"""
import importlib.util
import os
import sys

_name = "manta_ribbon_personal"
_spec = importlib.util.spec_from_file_location(
    _name, os.path.join(os.path.dirname(os.path.abspath(__file__)), "manta_ribbon.py"))
_m = importlib.util.module_from_spec(_spec)
_m.VARIANT = "light"
sys.modules[_name] = _m
_spec.loader.exec_module(_m)

if __name__ == "__main__":
    _m.main()

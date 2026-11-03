#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MANTA, the light chair: strength check. NOT a copy: it runs
manta_strength_check.py itself on manta_ribbon_personal (the "light" preset
in manta_ribbon.py: 70 kg sitter, 75 % walls, 15 % gyroid).

RUN:  python manta_strength_check_personal.py
"""
import importlib.util
import os
import sys

_name = "manta_strength_check_personal"
_spec = importlib.util.spec_from_file_location(
    _name, os.path.join(os.path.dirname(os.path.abspath(__file__)), "manta_strength_check.py"))
_m = importlib.util.module_from_spec(_spec)
_m.GEN = "manta_ribbon_personal"
sys.modules[_name] = _m
_spec.loader.exec_module(_m)

if __name__ == "__main__":
    _m.report()

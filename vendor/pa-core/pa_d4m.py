#!/usr/bin/env python3
"""Run the pa-d4m CLI from a checkout or a vendored copy: python3 vendor/pa-core/pa_d4m.py <cmd> ..."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pa_core.cli import main
sys.exit(main())

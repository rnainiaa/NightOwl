#!/usr/bin/env python3
"""
Entry point to start NightOwl C2 server
"""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'server'))

from server.main import main

if __name__ == "__main__":
    main()
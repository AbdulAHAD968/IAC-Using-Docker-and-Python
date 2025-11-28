#!/usr/bin/env python3

import os
import sys

# Add the cms directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'cms'))

from cms.main import main

if __name__ == "__main__":
    main()
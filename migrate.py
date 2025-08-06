#!/usr/bin/env python3
"""
Temporary migration script to test the new architecture.
This helps bridge the gap between old concat-notes.py and new CLI.
"""

import sys
from pathlib import Path

# Add the package to path for development
sys.path.insert(0, str(Path(__file__).parent))

from note_concatenator.cli.main import main

if __name__ == "__main__":
    # Temporary entry point for testing during development
    print("🚀 Using new Notes Concatenator v2.0 architecture")
    main()
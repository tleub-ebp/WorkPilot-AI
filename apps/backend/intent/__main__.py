#!/usr/bin/env python3
"""
Intent Recognition CLI Entry Point
===================================

Allows running the intent CLI as a module:
    python -m intent analyze "Add user authentication"
"""

from .cli import main

if __name__ == "__main__":
    main()

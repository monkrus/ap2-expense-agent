#!/usr/bin/env python
"""Wrapper to run seed_screenshot_data.py with proper UTF-8 encoding on Windows"""
import sys
import os

# Set UTF-8 encoding for stdout/stderr on Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Import and run the seed module
if __name__ == "__main__":
    exec(open('seed_screenshot_data.py', encoding='utf-8').read())

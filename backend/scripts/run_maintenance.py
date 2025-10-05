#!/usr/bin/env python3
"""
Database maintenance scheduler script
Run this script with cron or as a scheduled task
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.maintenance import run_maintenance

if __name__ == "__main__":
    try:
        stats = run_maintenance()
        print(f"Maintenance completed: {stats}")
        sys.exit(0)
    except Exception as e:
        print(f"Maintenance failed: {e}")
        sys.exit(1)

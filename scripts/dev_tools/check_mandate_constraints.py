#!/usr/bin/env python3
"""
Check what constraints are stored in a mandate
"""

import sys
import sqlite3
import json
sys.stdout.reconfigure(encoding='utf-8')

def main():
    print("=" * 60)
    print("Checking Mandate Constraints")
    print("=" * 60)

    # Connect to the backend database
    db_path = "backend/test.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Get the most recent intent mandate
        cursor.execute("""
            SELECT id, user_id, constraints, status, created_at
            FROM intent_mandates
            ORDER BY created_at DESC
            LIMIT 1
        """)

        result = cursor.fetchone()

        if not result:
            print("\n❌ No mandates found in database")
            return

        mandate_id, user_id, constraints_json, status, created_at = result

        print(f"\n📋 Most Recent Mandate:")
        print(f"   ID: {mandate_id}")
        print(f"   User ID: {user_id}")
        print(f"   Status: {status}")
        print(f"   Created: {created_at}")

        print(f"\n📝 Raw Constraints JSON:")
        print(f"   {constraints_json}")

        # Parse and display constraints
        if constraints_json:
            try:
                constraints = json.loads(constraints_json)
                print(f"\n🔍 Parsed Constraints:")
                for key, value in constraints.items():
                    print(f"   {key}: {value}")
            except json.JSONDecodeError as e:
                print(f"\n⚠️ Error parsing constraints: {e}")
        else:
            print(f"\n⚠️ No constraints stored")

    finally:
        conn.close()

    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()

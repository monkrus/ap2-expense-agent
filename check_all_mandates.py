#!/usr/bin/env python3
"""
Check ALL mandates in database
"""

import sys
import sqlite3
import json
sys.stdout.reconfigure(encoding='utf-8')

def main():
    print("=" * 60)
    print("All Mandates in Database")
    print("=" * 60)

    # Connect to the backend database
    db_path = "backend/test.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Get all intent mandates
        cursor.execute("""
            SELECT id, user_id, constraints, status, created_at
            FROM intent_mandates
            ORDER BY created_at DESC
            LIMIT 5
        """)

        results = cursor.fetchall()

        if not results:
            print("\n❌ No mandates found in database")
            return

        print(f"\n📊 Found {len(results)} mandate(s):\n")

        for idx, result in enumerate(results, 1):
            mandate_id, user_id, constraints_json, status, created_at = result

            print(f"#{idx} Mandate:")
            print(f"   ID: {mandate_id[:20]}...")
            print(f"   Status: {status}")
            print(f"   Created: {created_at}")

            if constraints_json:
                try:
                    constraints = json.loads(constraints_json)
                    print(f"   Constraints:")
                    for key, value in constraints.items():
                        if isinstance(value, list):
                            print(f"     - {key}: {', '.join(str(v) for v in value)}")
                        else:
                            print(f"     - {key}: {value}")
                except json.JSONDecodeError as e:
                    print(f"   ⚠️ Error parsing: {e}")
            else:
                print(f"   ⚠️ No constraints")
            print()

    finally:
        conn.close()

    print("=" * 60)

if __name__ == "__main__":
    main()

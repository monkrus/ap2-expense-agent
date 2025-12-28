import requests
import json

# Get auth token (you'll need to update this)
# For now, let's just check what the endpoint returns without auth

BASE_URL = "http://127.0.0.1:8000/api/v1"

# Test the expenses endpoint
print("Testing GET /api/v1/expenses?status_filter=pending")
print("-" * 60)

# We need to check what headers are being sent
print("\nNote: This test requires authentication.")
print("Please check the browser DevTools Network tab:")
print("1. Go to Network tab")
print("2. Filter for 'expenses'")
print("3. Click on the request to '/api/v1/expenses?status_filter=pending'")
print("4. Check the 'Headers' section")
print("5. Look for:")
print("   - Authorization: Bearer [token]")
print("   - X-Organization-Id: [org-id]")
print("\nThen check the 'Response' tab to see what data is returned")

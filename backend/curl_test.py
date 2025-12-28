import requests

url = "http://127.0.0.1:8000/api/v1/expenses?status_filter=pending"
headers = {"X-Organization-Id": "bd5fb358-d354-4089-a9b6-531e43b77540"}

print(f"Testing: {url}")
print(f"Headers: {headers}")
print()

try:
    response = requests.get(url, headers=headers)
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Response type: {type(data).__name__}")

        if isinstance(data, dict):
            print(f"SUCCESS! It's a dict with keys: {list(data.keys())}")
            if 'expenses' in data:
                print(f"Has 'expenses' key with {len(data['expenses'])} items")
            else:
                print("ERROR: Dict but no 'expenses' key")
        elif isinstance(data, list):
            print(f"ERROR! It's a list with {len(data)} items (should be dict)")
        else:
            print(f"ERROR! Unknown type: {type(data)}")
    else:
        print(f"Error response: {response.text}")
except Exception as e:
    print(f"Request failed: {e}")

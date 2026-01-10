# Restart Backend Server

The backend code has been updated to include `auto_approved` and `auto_approved_via` fields in the API response.

## Steps to Restart:

### Option 1: If backend is running in a terminal
1. Go to the terminal where backend is running
2. Press `Ctrl+C` to stop it
3. Run: `uvicorn src.api:app --reload`

### Option 2: Kill and restart
1. Find the process:
   ```bash
   # On Windows
   tasklist | findstr python
   ```

2. Kill it:
   ```bash
   # On Windows (replace PID with actual process ID)
   taskkill /F /PID <PID>
   ```

3. Restart:
   ```bash
   cd backend
   uvicorn src.api:app --reload
   ```

## After Restart:

Run the test again to verify fields are now included:
```bash
cd backend
python test_fresh_user_api.py
```

## Expected Result:
```json
{
  "auto_approved": true,
  "auto_approved_via": "intent_mandate",
  ...
}
```

Then test in the UI at http://localhost:5173:
- Login as: **testuser2**
- Password: **testpass123**
- Look for: Purple **✨ AI Agent** badge on the $75.50 Amazon expense

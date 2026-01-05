# Fixed Quick Start Guide - No Docker Required!

## Issues Fixed
- ✅ Removed Docker/PostgreSQL requirement (using SQLite instead)
- ✅ Fixed psycopg2 build error
- ✅ Simplified setup process

## Quick Start (3 Steps)

### Step 1: Start the Backend

```bash
cd /Users/jackson/docketassist-v3/backend

# Create virtual environment (if not already done)
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies (fixed version)
pip install -r requirements.txt

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Leave this terminal running!** Backend will be at: http://localhost:8000

Check it works: http://localhost:8000/health

### Step 2: Start the Frontend (New Terminal Window)

Open a **NEW terminal window** and run:

```bash
cd /Users/jackson/docketassist-v3/frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

**Leave this terminal running!** Frontend will be at: http://localhost:3000

### Step 3: Test It!

1. Open browser to: **http://localhost:3000**
2. Drag and drop a PDF file
3. Watch it analyze with Claude AI!

## What Changed?

**Before (Broken)**:
- Required Docker + PostgreSQL
- Needed PostgreSQL development headers
- Complex setup

**Now (Working)**:
- Uses SQLite database (built into Python)
- No external dependencies
- Simple setup

## Database Location

The SQLite database will be created at:
`/Users/jackson/docketassist-v3/backend/docketassist.db`

All your cases and documents are stored there.

## Troubleshooting

### "command not found: uvicorn"
Make sure you:
1. Activated the virtual environment: `source venv/bin/activate`
2. Installed requirements: `pip install -r requirements.txt`
3. See `(venv)` in your terminal prompt

### "Cannot connect to backend"
1. Make sure backend terminal is still running
2. Check for errors in backend terminal
3. Try: http://localhost:8000/health

### Frontend won't start
```bash
cd /Users/jackson/docketassist-v3/frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

## Need PostgreSQL Later?

For production, you'll want PostgreSQL. But for development, SQLite works perfectly!

To switch back to PostgreSQL later:
1. Install PostgreSQL locally or use a hosted service
2. Uncomment psycopg2-binary in requirements.txt
3. Update DATABASE_URL in config.py

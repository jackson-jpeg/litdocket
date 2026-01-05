#!/bin/bash

echo "======================================"
echo "DocketAssist v3 - Startup Script"
echo "======================================"
echo ""

# Check if we're in the right directory
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "Error: Please run this script from /Users/jackson/docketassist-v3/"
    exit 1
fi

echo "Step 1: Setting up Backend..."
cd backend

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install requirements
echo "Installing Python dependencies..."
pip install -q -r requirements.txt

echo ""
echo "✅ Backend setup complete!"
echo ""
echo "======================================"
echo "NOW RUN THESE COMMANDS:"
echo "======================================"
echo ""
echo "1️⃣  Start Backend (in this terminal):"
echo "   cd /Users/jackson/docketassist-v3/backend"
echo "   source venv/bin/activate"
echo "   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "2️⃣  Start Frontend (in a NEW terminal):"
echo "   cd /Users/jackson/docketassist-v3/frontend"
echo "   npm install"
echo "   npm run dev"
echo ""
echo "3️⃣  Open browser:"
echo "   http://localhost:3000"
echo ""
echo "======================================"

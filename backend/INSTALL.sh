#!/bin/bash

echo "Installing DocketAssist Backend..."
echo ""

# Make sure we're in the right directory
cd /Users/jackson/docketassist-v3/backend

# Remove old venv if exists
if [ -d "venv" ]; then
    echo "Removing old virtual environment..."
    rm -rf venv
fi

# Create new venv
echo "Creating virtual environment..."
python3 -m venv venv

# Activate venv
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies one by one to catch errors
echo ""
echo "Installing dependencies..."
echo "This may take a few minutes..."
echo ""

pip install fastapi==0.110.0
pip install "uvicorn[standard]==0.27.0"
pip install python-multipart==0.0.9
pip install sqlalchemy==2.0.25
pip install alembic==1.13.1
pip install pydantic==2.6.0
pip install pydantic-settings==2.1.0
pip install "python-jose[cryptography]==3.3.0"
pip install "passlib[bcrypt]==1.7.4"
pip install python-dateutil==2.8.2
pip install anthropic==0.18.1
pip install openai==1.12.0
pip install PyPDF2==3.0.1
pip install python-dotenv==1.0.0

echo ""
echo "✅ Installation complete!"
echo ""
echo "Now run:"
echo "  source venv/bin/activate"
echo "  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

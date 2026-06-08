#!/bin/bash
# AI Traffic System — Full Setup Script
# Run: chmod +x setup.sh && ./setup.sh

set -e
echo "======================================================"
echo "  AI Traffic System — Setup"
echo "======================================================"

# Check Python
if ! command -v python3 &>/dev/null; then
  echo "❌ Python 3 not found. Install Python 3.10+"
  exit 1
fi

# Check Node
if ! command -v node &>/dev/null; then
  echo "❌ Node.js not found. Install Node.js 18+"
  exit 1
fi

echo ""
echo "📦 Setting up Backend..."
cd backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

# Copy .env example if not present
if [ ! -f .env ]; then
  cp .env.example .env
  echo "✅ Created backend/.env (edit with your API keys)"
fi

deactivate
cd ..

echo ""
echo "📦 Setting up Frontend..."
cd frontend
npm install --silent
cd ..

echo ""
echo "📦 Setting up ML..."
cd ml
python3 -m venv venv
source venv/bin/activate
pip install ultralytics librosa tensorflow --quiet
mkdir -p weights dataset/images/{train,val,test} dataset/labels/{train,val,test} dataset/audio/{siren,background}
deactivate
cd ..

echo ""
echo "======================================================"
echo "✅ Setup complete!"
echo ""
echo "To start the system:"
echo "  Backend:   cd backend && source venv/bin/activate && uvicorn main:app --reload"
echo "  Frontend:  cd frontend && npm run dev"
echo ""
echo "Then open: http://localhost:3000"
echo "======================================================"

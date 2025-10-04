#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "========================================"
echo "AP2 Expense Management - Quick Start"
echo "========================================"
echo ""

# Check prerequisites
echo "Checking prerequisites..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERROR] Python not found. Please install Python 3.10+${NC}"
    exit 1
fi
echo -e "${GREEN}[OK] Python found: $(python3 --version)${NC}"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}[ERROR] Node.js not found. Please install Node.js 18+${NC}"
    exit 1
fi
echo -e "${GREEN}[OK] Node.js found: $(node --version)${NC}"

# Check PostgreSQL
if ! command -v psql &> /dev/null; then
    echo -e "${YELLOW}[WARNING] PostgreSQL command not found${NC}"
    echo "Please make sure PostgreSQL is installed and running"
    echo ""
fi

echo ""
echo "========================================"
echo "Step 1: Database Setup"
echo "========================================"
echo ""

# Create database
echo "Setting up database..."
psql -U postgres -c "CREATE DATABASE expenses;" 2>/dev/null || echo "Database may already exist"
psql -U postgres -c "CREATE USER ap2user WITH PASSWORD 'changeme';" 2>/dev/null || echo "User may already exist"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE expenses TO ap2user;" 2>/dev/null

echo -e "${GREEN}Database setup complete${NC}"
echo ""

echo "========================================"
echo "Step 2: Backend Setup"
echo "========================================"
echo ""

cd backend

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install -q -r requirements.txt

# Create .env file
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << EOF
DATABASE_URL=postgresql://ap2user:changeme@localhost:5432/expenses
JWT_SECRET=development-secret-change-in-production-please
ENVIRONMENT=development
DEBUG=true
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost
EOF
fi

# Run migrations
echo "Running database migrations..."
alembic upgrade head

# Setup authentication
echo "Setting up authentication system..."
python setup_auth.py

echo ""
echo -e "${GREEN}========================================"
echo "Backend setup complete!"
echo "========================================${NC}"
echo ""
echo "Default admin credentials:"
echo "  Username: admin"
echo "  Password: Admin123!"
echo ""
echo -e "${YELLOW}[IMPORTANT] Change this password after first login!${NC}"
echo ""

cd ..

echo "========================================"
echo "Step 3: Starting Servers"
echo "========================================"
echo ""

# Function to check if port is in use
check_port() {
    lsof -i:$1 > /dev/null 2>&1
    return $?
}

# Kill existing servers on ports 8000 and 5173
if check_port 8000; then
    echo "Killing existing process on port 8000..."
    kill $(lsof -ti:8000) 2>/dev/null
fi

if check_port 5173; then
    echo "Killing existing process on port 5173..."
    kill $(lsof -ti:5173) 2>/dev/null
fi

# Start backend
echo "Starting backend server..."
cd backend
source venv/bin/activate
uvicorn src.api:app --reload --host 0.0.0.0 --port 8000 > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo "Waiting for backend to start..."
sleep 3

# Start frontend
echo "Starting frontend server..."
cd frontend
npm install > /dev/null 2>&1
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

echo ""
echo -e "${GREEN}========================================"
echo "Servers are starting!"
echo "========================================${NC}"
echo ""
echo "Backend:  http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo "Frontend: http://localhost:5173"
echo ""
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo ""
echo "Logs:"
echo "  Backend:  tail -f backend.log"
echo "  Frontend: tail -f frontend.log"
echo ""
echo "Press Ctrl+C to stop servers and exit"
echo ""

# Wait a bit longer
sleep 5

# Run API tests
echo "Running API tests..."
python3 test_api.py

echo ""
echo -e "${GREEN}========================================"
echo "Setup Complete!"
echo "========================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Open browser: http://localhost:5173"
echo "  2. Login with: admin / Admin123!"
echo "  3. Change admin password"
echo "  4. See TEST_AUTHENTICATION.md for detailed testing"
echo ""
echo "To stop servers, run:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
echo ""

# Wait for user interrupt
trap "echo '' && echo 'Stopping servers...' && kill $BACKEND_PID $FRONTEND_PID 2>/dev/null && echo 'Servers stopped' && exit 0" INT

# Keep script running
wait

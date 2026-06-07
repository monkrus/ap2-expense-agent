#!/bin/bash
# Quick setup script for PostgreSQL migration

set -e

echo "🐘 AP2 Expense Agent - PostgreSQL Setup"
echo "========================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install Docker first.${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ docker-compose not found. Please install docker-compose first.${NC}"
    exit 1
fi

# Start PostgreSQL
echo -e "${YELLOW}📦 Starting PostgreSQL and Redis containers...${NC}"
docker-compose up -d postgres redis

# Wait for PostgreSQL to be ready
echo -e "${YELLOW}⏳ Waiting for PostgreSQL to be ready...${NC}"
sleep 5

# Check if PostgreSQL is healthy
until docker-compose exec -T postgres pg_isready -U ap2user -d expenses > /dev/null 2>&1; do
    echo -e "${YELLOW}   Still waiting for PostgreSQL...${NC}"
    sleep 2
done

echo -e "${GREEN}✅ PostgreSQL is ready!${NC}"
echo ""

# Update .env file
echo -e "${YELLOW}📝 Updating .env configuration...${NC}"

if [ -f .env ]; then
    # Backup existing .env
    cp .env .env.backup
    echo -e "${GREEN}   Created backup: .env.backup${NC}"
fi

# Update or create .env with PostgreSQL URL
if grep -q "^DATABASE_URL=" .env 2>/dev/null; then
    # Update existing line
    sed -i.bak 's|^DATABASE_URL=.*|DATABASE_URL=postgresql://ap2user:changeme@localhost:5432/expenses|' .env
    echo -e "${GREEN}   Updated DATABASE_URL in .env${NC}"
else
    # Add new line
    echo "DATABASE_URL=postgresql://ap2user:changeme@localhost:5432/expenses" >> .env
    echo -e "${GREEN}   Added DATABASE_URL to .env${NC}"
fi

# Run migrations
echo ""
echo -e "${YELLOW}🔄 Running database migrations...${NC}"

# Check current migration status
echo -e "${YELLOW}   Current migration status:${NC}"
alembic current || true

echo ""
echo -e "${YELLOW}   Applying migrations...${NC}"
alembic upgrade head

echo ""
echo -e "${GREEN}✅ Migrations completed!${NC}"

# Verify setup
echo ""
echo -e "${YELLOW}🔍 Verifying database setup...${NC}"

# Test connection
if docker-compose exec -T postgres psql -U ap2user -d expenses -c "\dt" > /dev/null 2>&1; then
    TABLE_COUNT=$(docker-compose exec -T postgres psql -U ap2user -d expenses -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | xargs)
    echo -e "${GREEN}   ✅ Database connection successful${NC}"
    echo -e "${GREEN}   ✅ Found ${TABLE_COUNT} tables${NC}"
else
    echo -e "${RED}   ❌ Database connection failed${NC}"
    exit 1
fi

# Run tests
echo ""
echo -e "${YELLOW}🧪 Running tests with PostgreSQL...${NC}"
echo -e "${YELLOW}   (This may take a minute...)${NC}"

if pytest tests/ -q --tb=no | tail -5; then
    echo -e "${GREEN}✅ Tests passed!${NC}"
else
    echo -e "${YELLOW}⚠️  Some tests may have failed. Check output above.${NC}"
fi

# Summary
echo ""
echo "======================================"
echo -e "${GREEN}🎉 PostgreSQL Setup Complete!${NC}"
echo "======================================"
echo ""
echo "Your application is now using PostgreSQL:"
echo "  - Database: expenses"
echo "  - User: ap2user"
echo "  - Port: 5432"
echo ""
echo "Useful commands:"
echo "  - View logs:        docker-compose logs -f postgres"
echo "  - Connect to DB:    docker-compose exec postgres psql -U ap2user -d expenses"
echo "  - Stop containers:  docker-compose down"
echo "  - View status:      docker-compose ps"
echo ""
echo "PgAdmin (optional):"
echo "  - Start:            docker-compose --profile tools up -d pgadmin"
echo "  - Access:           http://localhost:5050"
echo "  - Email:            admin@ap2.local"
echo "  - Password:         admin"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Run full test suite: pytest"
echo "  2. Configure QuickBooks and Stripe integration (see docs)"
echo "  3. Deploy to production (see deployment guide)"
echo ""

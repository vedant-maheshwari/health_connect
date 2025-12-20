#!/bin/bash

# Microservices Health Check Script
# This script verifies all services are running properly

echo "🏥 Telehealth Microservices Health Check"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check service health
check_service() {
    local service_name=$1
    local port=$2
    local url="http://localhost:${port}/health"
    
    echo -n "Checking $service_name (port $port)... "
    
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
    
    if [ "$response" = "200" ]; then
        echo -e "${GREEN}✓ Healthy${NC}"
        return 0
    else
        echo -e "${RED}✗ Unhealthy (HTTP $response)${NC}"
        return 1
    fi
}

# Check Docker Compose is running
echo "📦 Checking Docker containers..."
if ! docker-compose ps | grep -q "Up"; then
    echo -e "${RED}✗ Docker Compose services not running${NC}"
    echo -e "${YELLOW}💡 Run: docker-compose up -d${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose is running${NC}"
echo ""

# Check database
echo "🗄️  Checking PostgreSQL..."
if docker-compose exec -T postgres pg_isready -U telehealth_user &>/dev/null; then
    echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
else
    echo -e "${RED}✗ PostgreSQL is not ready${NC}"
fi
echo ""

# Check Redis
echo "💾 Checking Redis..."
if docker-compose exec -T redis redis-cli ping &>/dev/null; then
    echo -e "${GREEN}✓ Redis is ready${NC}"
else
    echo -e "${RED}✗ Redis is not ready${NC}"
fi
echo ""

# Check all microservices
echo "🔍 Checking Microservices..."
echo ""

all_healthy=true

check_service "API Gateway" "8000" || all_healthy=false
check_service "Auth Service" "8001" || all_healthy=false
check_service "Patient Service" "8002" || all_healthy=false
check_service "Doctor Service" "8003" || all_healthy=false
check_service "Appointment Service" "8004" || all_healthy=false
check_service "Family Service" "8005" || all_healthy=false
check_service "Chat Service" "8006" || all_healthy=false
check_service "Admin Service" "8007" || all_healthy=false

echo ""
echo "=========================================="

if [ "$all_healthy" = true ]; then
    echo -e "${GREEN}✅ All services are healthy!${NC}"
    echo ""
    echo "📱 Access the application at: http://localhost:8000"
    echo "📚 API Documentation: http://localhost:8000/docs"
    exit 0
else
    echo -e "${RED}❌ Some services are unhealthy${NC}"
    echo ""
    echo "🔧 Troubleshooting:"
    echo "  - Check logs: docker-compose logs [service-name]"
    echo "  - Restart services: docker-compose restart"
    echo "  - Rebuild: docker-compose up --build"
    exit 1
fi

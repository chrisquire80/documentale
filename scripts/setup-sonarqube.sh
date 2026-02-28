#!/bin/bash
# SonarQube Setup Script

set -e

echo "🚀 Starting SonarQube Setup..."
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SONARQUBE_VERSION="latest"
COMPOSE_FILE="docker-compose.sonarqube.yml"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
  echo -e "${RED}❌ Docker is not installed${NC}"
  echo "Please install Docker from https://docker.com"
  exit 1
fi

echo -e "${GREEN}✅ Docker found${NC}"

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
  echo -e "${RED}❌ Docker Compose is not installed${NC}"
  echo "Please install Docker Compose from https://docs.docker.com/compose/"
  exit 1
fi

echo -e "${GREEN}✅ Docker Compose found${NC}"
echo ""

# Start SonarQube
echo "📦 Starting SonarQube containers..."
docker-compose -f "$COMPOSE_FILE" up -d

# Wait for SonarQube to be ready
echo ""
echo "⏳ Waiting for SonarQube to be ready (this may take 1-2 minutes)..."
echo ""

max_attempts=60
attempts=0

while [ $attempts -lt $max_attempts ]; do
  if curl -s http://localhost:9000/api/system/health | grep -q '"status":"UP"'; then
    echo -e "${GREEN}✅ SonarQube is ready!${NC}"
    break
  fi

  attempts=$((attempts + 1))
  echo "⏳ Attempt $attempts/$max_attempts... waiting for SonarQube..."
  sleep 2
done

if [ $attempts -eq $max_attempts ]; then
  echo -e "${RED}❌ SonarQube failed to start${NC}"
  echo "Check logs with: docker-compose -f $COMPOSE_FILE logs sonarqube"
  exit 1
fi

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ SonarQube Setup Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo ""
echo "📊 SonarQube is running at: http://localhost:9000"
echo ""
echo "🔐 Default Credentials:"
echo "  Username: admin"
echo "  Password: admin_password"
echo ""
echo "⚠️  IMPORTANT: Change password on first login!"
echo ""
echo "📝 Next Steps:"
echo "  1. Open http://localhost:9000 in your browser"
echo "  2. Login with admin credentials"
echo "  3. Generate authentication token"
echo "  4. Add GitHub secrets:"
echo "     - SONAR_TOKEN: [token from step 3]"
echo "     - SONAR_HOST_URL: http://localhost:9000 (or your server URL)"
echo "  5. Run analysis:"
echo "     sonar-scanner -Dsonar.projectKey=documentale"
echo ""
echo "🔍 View Logs:"
echo "  docker-compose -f $COMPOSE_FILE logs -f sonarqube"
echo ""
echo "⛔ Stop SonarQube:"
echo "  docker-compose -f $COMPOSE_FILE down"
echo ""
echo "🗑️  Remove all data:"
echo "  docker-compose -f $COMPOSE_FILE down -v"
echo ""

# Create .env file for SonarQube
cat > .sonarqube.env << EOF
# SonarQube Environment Variables

# Server URL
SONAR_HOST_URL=http://localhost:9000

# Project Key
SONAR_PROJECT_KEY=documentale

# Project Name
SONAR_PROJECT_NAME=Documentale

# Sources
SONAR_SOURCES=backend/app,frontend/src

# Tests
SONAR_TESTS=backend/tests,frontend/src

# Coverage
SONAR_PYTHON_COVERAGE_REPORTPATHS=backend/coverage.xml
SONAR_JAVASCRIPT_LCOV_REPORTPATHS=frontend/coverage/lcov.info

# Exclusions
SONAR_EXCLUSIONS=**/migrations/**,**/node_modules/**,**/dist/**

# Authentication (set after creating token)
# SONAR_TOKEN=your_token_here
EOF

echo "✅ Created .sonarqube.env file"
echo ""
echo "📚 Documentation:"
echo "  - Full Setup: docs/SONARQUBE_SETUP.md"
echo "  - Quick Guide: docs/SONARQUBE_QUICKSTART.md"
echo ""

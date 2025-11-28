#!/bin/bash

# ==================== CMS Frontend Server Startup ====================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}CMS Frontend Server Startup${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Python3 found: $(python3 --version)${NC}"
echo ""

# Check if virtual environment exists
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo -e "${YELLOW}📦 Creating virtual environment...${NC}"
    python3 -m venv "$SCRIPT_DIR/venv"
    echo -e "${GREEN}✅ Virtual environment created${NC}"
else
    echo -e "${GREEN}✅ Virtual environment already exists${NC}"
fi

echo ""

# Activate virtual environment
echo -e "${YELLOW}🔄 Activating virtual environment...${NC}"
source "$SCRIPT_DIR/venv/bin/activate"
echo -e "${GREEN}✅ Virtual environment activated${NC}"

echo ""

# Install/upgrade requirements
echo -e "${YELLOW}📚 Installing requirements...${NC}"
pip install --upgrade pip > /dev/null 2>&1
pip install -r "$SCRIPT_DIR/requirements.txt" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Requirements installed successfully${NC}"
else
    echo -e "${RED}❌ Failed to install requirements${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Server Configuration${NC}"
echo -e "${BLUE}================================${NC}"
echo -e "Host: ${YELLOW}0.0.0.0${NC}"
echo -e "Port: ${YELLOW}5000${NC}"
echo -e "URL: ${YELLOW}http://localhost:5000${NC}"
echo ""
echo -e "${BLUE}Press Ctrl+C to stop the server${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Fix Docker environment variables for correct socket access
unset DOCKER_HOST  # Remove any existing value
export DOCKER_HOST='unix:///var/run/docker.sock'

# Ensure docker group is active and start Flask
# This fixes the docker socket permission issue
newgrp docker <<EOF
export DOCKER_HOST='unix:///var/run/docker.sock'
python "$SCRIPT_DIR/api.py"
EOF

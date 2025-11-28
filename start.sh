#!/bin/bash

# Enhanced CMS Startup Script

set -e

cd "$(dirname "$0")"

echo "🚀 Enhanced CMS - Starting..."
echo ""

# Check Docker
echo "🔍 Checking Docker daemon..."
if ! docker ps &> /dev/null; then
    echo "❌ Docker daemon is not running"
    echo "📌 Starting Docker..."
    sudo systemctl start docker
    sleep 2
fi

echo "✅ Docker is running"
echo ""

# Check Python dependencies
echo "📦 Checking Python dependencies..."
if ! python3 -c "import flask, docker, yaml" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

echo "✅ Dependencies installed"
echo ""

# Create SSH keys if needed
echo "🔑 Checking SSH keys..."
if [ ! -f "./keys/id_rsa" ]; then
    echo "🔑 Generating SSH keys..."
    mkdir -p keys
    ssh-keygen -t rsa -b 4096 -f ./keys/id_rsa -N "" -C "cms@infrastructure" 2>/dev/null
    echo "✅ SSH keys generated"
else
    echo "✅ SSH keys exist"
fi

echo ""
echo "════════════════════════════════════════════════════"
echo "🎯 CHOOSE DEPLOYMENT METHOD:"
echo "════════════════════════════════════════════════════"
echo ""
echo "1) Docker Compose (Recommended - Fastest)"
echo "2) Enhanced API (Full control - Port 5001)"
echo "3) Docker Compose + Enhanced API (Both)"
echo ""
read -p "Select option (1-3): " choice

case $choice in
    1)
        echo ""
        echo "🐳 Starting with Docker Compose..."
        echo "📊 Dashboard will be available at: http://localhost/dashboard"
        echo ""
        docker-compose up -d
        echo ""
        echo "✅ Infrastructure deployed! Waiting for containers to initialize..."
        sleep 30
        echo ""
        echo "📊 Open your browser:"
        echo "   http://localhost (if port 80 exposed)"
        echo ""
        docker-compose ps
        ;;
    2)
        echo ""
        echo "🚀 Starting Enhanced API Server..."
        echo "📊 Dashboard available at: http://localhost:5001"
        echo ""
        echo "Press Ctrl+C to stop the server"
        echo ""
        python3 enhanced_api.py
        ;;
    3)
        echo ""
        echo "🐳 Starting Docker Compose in background..."
        docker-compose up -d
        echo "✅ Docker Compose started"
        echo ""
        sleep 10
        echo ""
        echo "🚀 Starting Enhanced API Server..."
        echo "📊 Dashboard available at: http://localhost:5001"
        echo ""
        echo "Press Ctrl+C to stop the API server"
        echo ""
        python3 enhanced_api.py
        ;;
    *)
        echo "❌ Invalid option"
        exit 1
        ;;
esac

echo ""
echo "✅ Setup complete!"

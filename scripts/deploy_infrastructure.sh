#!/bin/bash

echo "Starting Secure IaC Infrastructure Deployment..."


# Generate SSH key if not exists
if [ ! -f "keys/id_rsa" ]; then
    echo "🔑 Generating SSH key pair..."
    mkdir -p keys
    ssh-keygen -t rsa -b 4096 -f keys/id_rsa -N ""
fi

# Run the CMS deployment
echo "🚀 Starting CMS deployment..."
python3 cms/main.py deploy

# Wait for containers to start
echo "⏳ Waiting for infrastructure to initialize..."
sleep 30

# Run security audit
echo "🔒 Running initial security audit..."
python3 cms/main.py audit

echo "✅ Deployment completed!"
echo ""
echo "📊 Infrastructure Status:"
python3 cms/main.py status

echo ""
echo "🌐 Available Services:"
echo "  Web Server: http://localhost:8080"
echo "  Email Server: SMTP on port 1025, IMAP on 1993"
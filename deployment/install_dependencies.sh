#!/bin/bash
# EC2 Setup Script for AI_CRDC_HUB
# This script sets up a fresh Ubuntu EC2 instance for the AI Test Automation System

set -e  # Exit on error

echo "=========================================="
echo "AI_CRDC_HUB - EC2 Setup Script"
echo "=========================================="

# Update system packages
echo "Step 1: Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python and pip
echo "Step 2: Installing Python 3 and pip..."
sudo apt install -y python3 python3-pip python3-venv python3-dev

# Install Node.js (for Playwright)
echo "Step 3: Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install system dependencies for Playwright
echo "Step 4: Installing system dependencies for Playwright..."
sudo apt install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2t64 \
    libpango-1.0-0 \
    libcairo2

# Install Playwright browsers
echo "Step 5: Installing Playwright browsers..."
sudo npm install -g playwright
sudo npx playwright install --with-deps chromium

# Install AWS CLI (for Bedrock access)
echo "Step 6: Installing AWS CLI..."
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
sudo apt install -y unzip
unzip awscliv2.zip
sudo ./aws/install
rm -rf aws awscliv2.zip

# Create project directory
echo "Step 7: Creating project directory..."
PROJECT_DIR="/opt/AI_CRDCHub"
sudo mkdir -p $PROJECT_DIR
sudo chown $USER:$USER $PROJECT_DIR

# Create virtual environment
echo "Step 8: Creating Python virtual environment..."
cd $PROJECT_DIR
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies (will be done when code is deployed)
echo "Step 9: Python dependencies will be installed when code is deployed"
echo "  Run: pip install -r requirements.txt"

# Create necessary directories
echo "Step 10: Creating project directories..."
mkdir -p data/{stories,test_cases,selections,results}
mkdir -p generated_tests screenshots reports logs
mkdir -p api core integrations utils templates static/{css,js,images}

# Set up log rotation
echo "Step 11: Setting up log rotation..."
sudo tee /etc/logrotate.d/ai-crdc-hub > /dev/null <<EOF
$PROJECT_DIR/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 $USER $USER
}
EOF

# Install and configure systemd service (will be done after app.py is created)
echo "Step 12: Systemd service will be configured after application is deployed"

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo "Next steps:"
echo "1. Clone/deploy your code to: $PROJECT_DIR"
echo "2. Create .env file with AWS credentials and configuration"
echo "3. Install Python dependencies: pip install -r requirements.txt"
echo "4. Set up systemd service (see deployment/app.service)"
echo "5. Start the application"
echo ""
echo "Project directory: $PROJECT_DIR"
echo "Python virtual env: $PROJECT_DIR/venv"
echo "=========================================="


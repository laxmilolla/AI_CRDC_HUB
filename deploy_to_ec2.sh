#!/bin/bash
# Deployment script for AI_CRDC_HUB to EC2
# Usage: ./deploy_to_ec2.sh /path/to/mcp-playwright-key-final.pem

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
EC2_IP="3.221.24.93"
EC2_USER="ubuntu"
PROJECT_DIR="/opt/AI_CRDC_HUB"
SSH_KEY="$1"

# Check if SSH key is provided
if [ -z "$SSH_KEY" ]; then
    echo -e "${RED}Error: SSH key file required${NC}"
    echo "Usage: $0 /path/to/mcp-playwright-key-final.pem"
    exit 1
fi

# Check if SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    echo -e "${RED}Error: SSH key file not found: $SSH_KEY${NC}"
    exit 1
fi

# Set correct permissions for SSH key
chmod 400 "$SSH_KEY"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}AI_CRDC_HUB - EC2 Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Test SSH connection
echo -e "${YELLOW}Step 1: Testing SSH connection...${NC}"
if ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$EC2_USER@$EC2_IP" "echo 'Connection successful'" 2>/dev/null; then
    echo -e "${GREEN}✓ SSH connection successful${NC}"
else
    echo -e "${RED}✗ SSH connection failed${NC}"
    echo "Please check:"
    echo "  - SSH key file path is correct"
    echo "  - EC2 instance is running"
    echo "  - Security group allows SSH (port 22)"
    exit 1
fi

# Create project directory structure on EC2
echo -e "${YELLOW}Step 2: Creating project directory on EC2...${NC}"
ssh -i "$SSH_KEY" "$EC2_USER@$EC2_IP" "sudo mkdir -p $PROJECT_DIR && sudo chown $EC2_USER:$EC2_USER $PROJECT_DIR" || true
echo -e "${GREEN}✓ Directory created${NC}"

# Copy project files to EC2
echo -e "${YELLOW}Step 3: Copying project files to EC2...${NC}"
rsync -avz -e "ssh -i $SSH_KEY" \
    --exclude='.git' \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='screenshots/*' \
    --exclude='reports/*' \
    --exclude='data/*' \
    ./ "$EC2_USER@$EC2_IP:$PROJECT_DIR/"

echo -e "${GREEN}✓ Files copied${NC}"

# Run setup script on EC2
echo -e "${YELLOW}Step 4: Running setup script on EC2...${NC}"
ssh -i "$SSH_KEY" "$EC2_USER@$EC2_IP" << ENDSSH
cd $PROJECT_DIR
chmod +x deployment/install_dependencies.sh
./deployment/install_dependencies.sh
ENDSSH

echo -e "${GREEN}✓ Setup script completed${NC}"

# Create .env file on EC2
echo -e "${YELLOW}Step 5: Configuring environment variables...${NC}"
ssh -i "$SSH_KEY" "$EC2_USER@$EC2_IP" << ENDSSH
cd $PROJECT_DIR
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file - please edit it with your AWS credentials"
fi
ENDSSH

echo -e "${GREEN}✓ Environment file created${NC}"
echo -e "${YELLOW}⚠ IMPORTANT: Edit .env file on EC2 with your AWS credentials${NC}"

# Install Python dependencies
echo -e "${YELLOW}Step 6: Installing Python dependencies...${NC}"
ssh -i "$SSH_KEY" "$EC2_USER@$EC2_IP" << ENDSSH
cd $PROJECT_DIR
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
ENDSSH

echo -e "${GREEN}✓ Python dependencies installed${NC}"

# Install Playwright browsers
echo -e "${YELLOW}Step 7: Installing Playwright browsers...${NC}"
ssh -i "$SSH_KEY" "$EC2_USER@$EC2_IP" << ENDSSH
cd $PROJECT_DIR
npx playwright install --with-deps chromium
ENDSSH

echo -e "${GREEN}✓ Playwright browsers installed${NC}"

# Set up systemd service
echo -e "${YELLOW}Step 8: Setting up systemd service...${NC}"
ssh -i "$SSH_KEY" "$EC2_USER@$EC2_IP" << ENDSSH
cd $PROJECT_DIR
sudo cp deployment/app.service /etc/systemd/system/ai-crdc-hub.service
sudo systemctl daemon-reload
sudo systemctl enable ai-crdc-hub
ENDSSH

echo -e "${GREEN}✓ Systemd service configured${NC}"

# Check if port 5000 is open in security group
echo -e "${YELLOW}Step 9: Checking security group configuration...${NC}"
echo -e "${YELLOW}⚠ Make sure port 5000 is open in EC2 security group${NC}"
echo "   Security Group ID: sg-0da74cf9bd5c6169b"
echo "   Add inbound rule: TCP port 5000 from 0.0.0.0/0"

# Final instructions
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Edit .env file on EC2 with your AWS credentials:"
echo "   ssh -i $SSH_KEY $EC2_USER@$EC2_IP"
echo "   nano $PROJECT_DIR/.env"
echo ""
echo "2. Start the application:"
echo "   ssh -i $SSH_KEY $EC2_USER@$EC2_IP"
echo "   sudo systemctl start ai-crdc-hub"
echo ""
echo "3. Check service status:"
echo "   sudo systemctl status ai-crdc-hub"
echo ""
echo "4. Access the application:"
echo "   http://$EC2_IP:5000"
echo ""
echo -e "${GREEN}========================================${NC}"


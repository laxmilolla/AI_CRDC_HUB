# AI_CRDC_HUB - Deployment Guide

## EC2 Instance Information

- **Instance ID**: `i-0bb2e7c8d94a69d3b`
- **Name**: `AI_CRDC_HUB`
- **Static IP**: `3.221.24.93`
- **SSH Key**: `mcp-playwright-key-final`
- **Region**: `us-east-1`

## Prerequisites

1. SSH access to EC2 instance
2. AWS credentials with Bedrock access
3. TOTP secret key (for 2FA login to application under test)

## Step 1: Connect to EC2 Instance

```bash
ssh -i /path/to/mcp-playwright-key-final.pem ubuntu@3.221.24.93
```

## Step 2: Run Setup Script

Once connected to EC2:

```bash
# Clone the repository (or upload files)
cd /opt
sudo git clone https://github.com/laxmilolla/AI_CRDC_HUB.git
# OR upload files via SCP

# Navigate to project directory
cd AI_CRDC_HUB

# Make setup script executable
chmod +x deployment/install_dependencies.sh

# Run setup script
./deployment/install_dependencies.sh
```

This will install:
- Python 3 and pip
- Node.js
- Playwright and browsers
- AWS CLI
- System dependencies (including xvfb for headless display)
- ExecuteAutomation MCP Playwright server
- MCP Bridge dependencies
- Create project structure

## Step 3: Configure Environment Variables

```bash
cd /opt/AI_CRDCHub

# Copy example env file
cp .env.example .env

# Edit environment variables
nano .env
```

Required environment variables:
```env
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# TOTP Configuration (for 2FA)
TOTP_SECRET_KEY=your_totp_secret

# Application Configuration
FLASK_ENV=production
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
```

## Step 4: Install Python Dependencies

```bash
cd /opt/AI_CRDCHub
source venv/bin/activate
pip install -r requirements.txt
```

## Step 5: Set Up MCP Bridge Service

The MCP Bridge is a Node.js service that connects to the ExecuteAutomation MCP Playwright server.

```bash
# Install MCP Bridge dependencies
cd /opt/AI_CRDC_HUB/mcp-bridge
npm install

# Copy MCP bridge service file
sudo cp /opt/AI_CRDC_HUB/deployment/mcp-bridge.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable MCP bridge service to start on boot
sudo systemctl enable mcp-bridge

# Start MCP bridge service
sudo systemctl start mcp-bridge

# Check status
sudo systemctl status mcp-bridge

# View logs
sudo journalctl -u mcp-bridge -f
```

The MCP bridge runs on port 3001 by default. Verify it's working:
```bash
curl http://localhost:3001/health
```

## Step 6: Set Up Main Application Service

```bash
# Copy service file
sudo cp deployment/app.service /etc/systemd/system/ai-crdc-hub.service

# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable ai-crdc-hub

# Start service
sudo systemctl start ai-crdc-hub

# Check status
sudo systemctl status ai-crdc-hub

# View logs
sudo journalctl -u ai-crdc-hub -f
```

**Note**: The main application depends on the MCP bridge service. Make sure the MCP bridge is running before starting the main application.

## Step 7: Configure IAM Role (if needed)

If the EC2 instance doesn't have an IAM role with Bedrock permissions:

1. Go to AWS Console → EC2 → Select instance → Actions → Security → Modify IAM role
2. Attach/create role with policy:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "bedrock:InvokeModel",
           "bedrock:ListFoundationModels"
         ],
         "Resource": "*"
       }
     ]
   }
   ```

## Step 8: Verify Deployment

1. Check if service is running:
   ```bash
   sudo systemctl status ai-crdc-hub
   ```

2. Check if application is accessible:
   ```bash
   curl http://localhost:5000
   ```

3. Check MCP bridge is running:
   ```bash
   curl http://localhost:3001/health
   sudo systemctl status mcp-bridge
   ```

4. Access web UI:
   - Open browser: `http://3.221.24.93:5000`

## Step 9: Firewall Configuration

Ensure security group allows:
- Port 22 (SSH) - Already open
- Port 5000 (Application) - May need to add
- Port 80 (HTTP) - Already open
- Port 443 (HTTPS) - Already open

To add port 5000:
```bash
# Via AWS Console: EC2 → Security Groups → Add inbound rule
# Or via AWS CLI:
aws ec2 authorize-security-group-ingress \
  --group-id sg-0da74cf9bd5c6169b \
  --protocol tcp \
  --port 5000 \
  --cidr 0.0.0.0/0
```

## Troubleshooting

### Service won't start
```bash
# Check logs
sudo journalctl -u ai-crdc-hub -n 50

# Check if port is in use
sudo netstat -tulpn | grep 5000

# Check Python path
which python3
```

### Application errors
```bash
# Check application logs
tail -f /opt/AI_CRDCHub/logs/app.log

# Check if virtual environment is activated
source /opt/AI_CRDCHub/venv/bin/activate
python --version
```

### Bedrock access issues
```bash
# Test AWS credentials
aws bedrock list-foundation-models --region us-east-1

# Check IAM role
aws sts get-caller-identity
```

## Updating the Application

```bash
cd /opt/AI_CRDCHub

# Pull latest changes
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Install new dependencies (if any)
pip install -r requirements.txt

# Restart service
sudo systemctl restart ai-crdc-hub
```

## Backup

Important files to backup:
- `/opt/AI_CRDCHub/data/` - User stories, test cases, results
- `/opt/AI_CRDCHub/.env` - Configuration
- `/opt/AI_CRDCHub/screenshots/` - Test screenshots
- `/opt/AI_CRDCHub/reports/` - Generated reports

## Monitoring

- Service status: `sudo systemctl status ai-crdc-hub`
- Application logs: `sudo journalctl -u ai-crdc-hub -f`
- System logs: `/opt/AI_CRDCHub/logs/app.log`
- Disk space: `df -h`
- Memory usage: `free -h`

---

**Last Updated**: 2024-01-15


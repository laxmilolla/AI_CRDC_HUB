# Deployment Checklist

## Pre-Deployment

### Local Validation
- [x] Project structure validated
- [x] All required files present
- [ ] Python dependencies installed (`pip install -r requirements.txt`)
- [ ] Playwright browsers installed (`npx playwright install`)
- [ ] Environment variables configured (`.env` file)

### Code Quality
- [x] No linting errors
- [x] All imports resolved
- [x] Git repository initialized and pushed

## EC2 Deployment Steps

### 1. Connect to EC2 Instance
```bash
ssh -i ~/.ssh/your-key.pem ec2-user@3.221.24.93
```

### 2. Run Installation Script
```bash
cd /home/ec2-user
git clone https://github.com/laxmilolla/AI_CRDC_HUB.git
cd AI_CRDC_HUB
chmod +x deployment/install_dependencies.sh
sudo ./deployment/install_dependencies.sh
```

### 3. Configure Environment
```bash
cp .env.example .env
nano .env  # Edit with your AWS credentials and configuration
```

### 4. Install Python Dependencies
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### 5. Install Playwright Browsers
```bash
npx playwright install --with-deps chromium
```

### 6. Install MCP Playwright Server
```bash
npm install -g @modelcontextprotocol/server-playwright
```

### 7. Set Up Systemd Service
```bash
sudo cp deployment/app.service /etc/systemd/system/ai-crdc-hub.service
sudo systemctl daemon-reload
sudo systemctl enable ai-crdc-hub
sudo systemctl start ai-crdc-hub
```

### 8. Verify Service Status
```bash
sudo systemctl status ai-crdc-hub
```

### 9. Check Logs
```bash
sudo journalctl -u ai-crdc-hub -f
```

### 10. Test Application
- Open browser: `http://3.221.24.93:5000`
- Upload a test user story
- Generate test cases
- Select and run tests

## Post-Deployment Verification

- [ ] Application accessible via web browser
- [ ] User story upload works
- [ ] Test case generation works (requires AWS Bedrock access)
- [ ] Test execution works (requires MCP Playwright server)
- [ ] Screenshots are captured
- [ ] Reports are generated
- [ ] Systemd service auto-starts on reboot

## Troubleshooting

### Application won't start
- Check logs: `sudo journalctl -u ai-crdc-hub -n 50`
- Verify environment variables: `cat .env`
- Check Python dependencies: `pip list`
- Verify port availability: `netstat -tulpn | grep 5000`

### AWS Bedrock errors
- Verify AWS credentials in `.env`
- Check IAM permissions for Bedrock access
- Verify region is correct

### MCP Playwright errors
- Verify MCP server is running: `ps aux | grep mcp`
- Check MCP server logs
- Verify Playwright browsers installed: `npx playwright --version`

### Screenshot issues
- Check directory permissions: `ls -la screenshots/`
- Verify disk space: `df -h`
- Check screenshot handler logs

## Security Notes

- Never commit `.env` file to Git
- Use IAM roles instead of access keys when possible
- Keep EC2 security group rules minimal
- Regularly update dependencies
- Monitor application logs for errors

## Maintenance

### Update Application
```bash
cd /home/ec2-user/AI_CRDC_HUB
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart ai-crdc-hub
```

### Backup Data
```bash
# Backup stories, test cases, and results
tar -czf backup-$(date +%Y%m%d).tar.gz data/ screenshots/ reports/
```

### Monitor Resources
```bash
# Check disk usage
df -h

# Check memory usage
free -h

# Check CPU usage
top
```

---

**Last Updated**: 2024-01-15


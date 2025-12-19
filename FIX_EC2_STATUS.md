# Fix EC2 Status Check (2/3 Running)

## Understanding EC2 Status Checks

AWS EC2 has **2 standard status checks**:
1. **System Status Checks** - AWS infrastructure (host hardware, network)
2. **Instance Status Checks** - Your instance software/network

If you see "2/3", it might mean:
- 2 out of 3 custom checks are passing
- Or one of the standard checks is failing

## Step 1: Check Which Status Check is Failing

### Via AWS Console:
1. Go to **EC2 Console** → **Instances**
2. Select instance `i-0bb2e7c8d94a69d3b`
3. Click **Status checks** tab
4. Look for:
   - ⚠️ **System status check** - If failed, AWS infrastructure issue
   - ⚠️ **Instance status check** - If failed, your instance has issues

### Via AWS CLI (if configured):
```bash
aws ec2 describe-instance-status \
  --instance-ids i-0bb2e7c8d94a69d3b \
  --region us-east-1 \
  --include-all-instances
```

## Step 2: Common Causes and Fixes

### If System Status Check Failed:
- **Cause**: AWS infrastructure issue (rare)
- **Fix**: 
  1. Wait 5-10 minutes (AWS usually auto-recovers)
  2. If persists, stop and start the instance
  3. Contact AWS Support if issue continues

### If Instance Status Check Failed:
- **Cause**: Instance software/network issues
- **Common reasons**:
  - Services crashed
  - Out of memory
  - Network configuration issue
  - Disk full

## Step 3: Diagnose Instance Issues

### Option A: Use EC2 Instance Connect (Browser-based)
1. Go to EC2 Console → Select instance
2. Click **Connect** → **EC2 Instance Connect**
3. Run diagnostic commands:

```bash
# Check service status
sudo systemctl status app.service mcp-bridge.service

# Check if services are running
sudo systemctl is-active app.service
sudo systemctl is-active mcp-bridge.service

# Check ports
sudo netstat -tuln | grep -E ':(5000|3001)'

# Check disk space
df -h

# Check memory
free -h

# Check recent logs
sudo journalctl -u app.service -n 50 --no-pager
sudo journalctl -u mcp-bridge.service -n 50 --no-pager
```

### Option B: Use Systems Manager Session Manager
```bash
aws ssm start-session --target i-0bb2e7c8d94a69d3b --region us-east-1
```

## Step 4: Fix Common Issues

### Issue 1: Services Not Running
```bash
# Restart Flask app
sudo systemctl restart app.service
sudo systemctl status app.service

# Restart MCP bridge
sudo systemctl restart mcp-bridge.service
sudo systemctl status mcp-bridge.service

# Enable auto-start on boot
sudo systemctl enable app.service
sudo systemctl enable mcp-bridge.service
```

### Issue 2: Port Not Listening
```bash
# Check what's using the ports
sudo lsof -i :5000
sudo lsof -i :3001

# If something else is using them, kill it or change config
```

### Issue 3: Out of Memory
```bash
# Check memory usage
free -h

# If low, restart services or increase instance size
sudo systemctl restart app.service mcp-bridge.service
```

### Issue 4: Disk Full
```bash
# Check disk usage
df -h

# Clean up if needed
sudo journalctl --vacuum-time=7d  # Clean old logs
sudo apt-get clean  # Clean package cache
```

### Issue 5: Service Crashed
```bash
# Check logs for errors
sudo journalctl -u app.service -n 100 --no-pager | grep -i error
sudo journalctl -u mcp-bridge.service -n 100 --no-pager | grep -i error

# Restart services
sudo systemctl restart app.service mcp-bridge.service
```

## Step 5: Verify Fix

After fixing, wait 2-3 minutes and check:
1. EC2 Console → Status checks should show 2/2 passing
2. Services are running: `sudo systemctl status app.service mcp-bridge.service`
3. Ports are listening: `sudo netstat -tuln | grep -E ':(5000|3001)'`
4. Web UI is accessible: `http://3.221.24.93:5000`

## Quick Recovery Script

If you can access the instance, run:

```bash
# Restart all services
sudo systemctl restart app.service mcp-bridge.service

# Wait a moment
sleep 5

# Check status
sudo systemctl status app.service mcp-bridge.service --no-pager

# Check ports
curl -s http://localhost:5000 > /dev/null && echo "Flask: OK" || echo "Flask: FAILED"
curl -s http://localhost:3001/health > /dev/null && echo "MCP Bridge: OK" || echo "MCP Bridge: FAILED"
```

## If Instance is Completely Unresponsive

1. **Stop the instance** (not terminate!) from AWS Console
2. Wait 1 minute
3. **Start the instance**
4. Wait 2-3 minutes for it to boot
5. Check status checks again

## Next Steps After Fix

Once status checks pass:
1. Deploy the updated screenshot fixes:
   ```bash
   # Copy updated files
   sudo cp /tmp/mcp_client.py /opt/AI_CRDC_HUB/integrations/
   sudo cp /tmp/server.js /opt/AI_CRDC_HUB/mcp-bridge/
   sudo systemctl restart app.service mcp-bridge.service
   ```

2. Verify services are healthy
3. Test the application


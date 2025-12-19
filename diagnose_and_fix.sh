#!/bin/bash
# Comprehensive diagnostic and fix script for Instance Status Check failure
# Run this via EC2 Instance Connect

set -e

echo "=========================================="
echo "Instance Status Check Diagnostic & Fix"
echo "=========================================="
echo ""

# 1. Check system resources
echo "1. SYSTEM RESOURCES:"
echo "   Memory:"
free -h | grep Mem
MEM_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2*100}')
if [ $MEM_USAGE -gt 90 ]; then
    echo "   ⚠ WARNING: Memory usage is ${MEM_USAGE}%"
fi

echo "   Disk:"
df -h / | tail -1
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 90 ]; then
    echo "   ⚠ WARNING: Disk usage is ${DISK_USAGE}%"
fi

echo ""

# 2. Check service files exist
echo "2. SERVICE FILES:"
if [ -f /etc/systemd/system/app.service ]; then
    echo "   ✓ app.service file exists"
else
    echo "   ✗ app.service file MISSING"
    echo "   Creating from deployment file..."
    if [ -f /opt/AI_CRDC_HUB/deployment/app.service ]; then
        sudo cp /opt/AI_CRDC_HUB/deployment/app.service /etc/systemd/system/app.service
        sudo systemctl daemon-reload
        echo "   ✓ Created app.service"
    else
        echo "   ✗ Cannot find deployment/app.service"
    fi
fi

if [ -f /etc/systemd/system/mcp-bridge.service ]; then
    echo "   ✓ mcp-bridge.service file exists"
else
    echo "   ✗ mcp-bridge.service file MISSING"
    echo "   Creating from deployment file..."
    if [ -f /opt/AI_CRDC_HUB/deployment/mcp-bridge.service ]; then
        sudo cp /opt/AI_CRDC_HUB/deployment/mcp-bridge.service /etc/systemd/system/mcp-bridge.service
        sudo systemctl daemon-reload
        echo "   ✓ Created mcp-bridge.service"
    else
        echo "   ✗ Cannot find deployment/mcp-bridge.service"
    fi
fi

echo ""

# 3. Check service status
echo "3. SERVICE STATUS:"
echo "   Flask App (app.service):"
if systemctl is-active --quiet app.service 2>/dev/null; then
    echo "      ✓ Active"
else
    echo "      ✗ INACTIVE"
    echo "      Checking why..."
    sudo systemctl status app.service --no-pager -l | tail -15
    echo ""
    echo "      Attempting to start..."
    sudo systemctl start app.service
    sleep 3
    if systemctl is-active --quiet app.service 2>/dev/null; then
        echo "      ✓ Started successfully"
    else
        echo "      ✗ Failed to start"
        echo "      Recent errors:"
        sudo journalctl -u app.service -n 20 --no-pager | grep -i error || echo "      No recent errors in logs"
    fi
fi

echo ""
echo "   MCP Bridge (mcp-bridge.service):"
if systemctl is-active --quiet mcp-bridge.service 2>/dev/null; then
    echo "      ✓ Active"
else
    echo "      ✗ INACTIVE"
    echo "      Checking why..."
    sudo systemctl status mcp-bridge.service --no-pager -l | tail -15
    echo ""
    echo "      Attempting to start..."
    sudo systemctl start mcp-bridge.service
    sleep 3
    if systemctl is-active --quiet mcp-bridge.service 2>/dev/null; then
        echo "      ✓ Started successfully"
    else
        echo "      ✗ Failed to start"
        echo "      Recent errors:"
        sudo journalctl -u mcp-bridge.service -n 20 --no-pager | grep -i error || echo "      No recent errors in logs"
    fi
fi

echo ""

# 4. Check ports
echo "4. PORT STATUS:"
if netstat -tuln 2>/dev/null | grep -q ':5000.*LISTEN'; then
    echo "   ✓ Port 5000 (Flask) is listening"
    PROCESS=$(sudo lsof -ti:5000 2>/dev/null | head -1)
    if [ -n "$PROCESS" ]; then
        echo "      Process: $(ps -p $PROCESS -o comm= 2>/dev/null || echo 'unknown')"
    fi
else
    echo "   ✗ Port 5000 (Flask) is NOT listening"
fi

if netstat -tuln 2>/dev/null | grep -q ':3001.*LISTEN'; then
    echo "   ✓ Port 3001 (MCP Bridge) is listening"
    PROCESS=$(sudo lsof -ti:3001 2>/dev/null | head -1)
    if [ -n "$PROCESS" ]; then
        echo "      Process: $(ps -p $PROCESS -o comm= 2>/dev/null || echo 'unknown')"
    fi
else
    echo "   ✗ Port 3001 (MCP Bridge) is NOT listening"
fi

echo ""

# 5. Check HTTP endpoints
echo "5. HTTP ENDPOINT TESTS:"
if curl -s --max-time 3 http://localhost:5000 > /dev/null 2>&1; then
    echo "   ✓ Flask app responding on localhost:5000"
else
    echo "   ✗ Flask app NOT responding on localhost:5000"
fi

if curl -s --max-time 3 http://127.0.0.1:5000 > /dev/null 2>&1; then
    echo "   ✓ Flask app responding on 127.0.0.1:5000"
else
    echo "   ✗ Flask app NOT responding on 127.0.0.1:5000"
fi

if curl -s --max-time 3 http://localhost:3001/health > /dev/null 2>&1; then
    echo "   ✓ MCP Bridge responding on localhost:3001"
    HEALTH_RESPONSE=$(curl -s http://localhost:3001/health 2>/dev/null)
    echo "      Response: $HEALTH_RESPONSE"
else
    echo "   ✗ MCP Bridge NOT responding on localhost:3001"
fi

echo ""

# 6. Check file permissions and paths
echo "6. FILE PERMISSIONS & PATHS:"
if [ -f /opt/AI_CRDC_HUB/app.py ]; then
    echo "   ✓ app.py exists"
    ls -lh /opt/AI_CRDC_HUB/app.py | awk '{print "      Permissions: " $1 " Owner: " $3 ":" $4}'
else
    echo "   ✗ app.py MISSING at /opt/AI_CRDC_HUB/app.py"
fi

if [ -f /opt/AI_CRDC_HUB/mcp-bridge/server.js ]; then
    echo "   ✓ server.js exists"
    ls -lh /opt/AI_CRDC_HUB/mcp-bridge/server.js | awk '{print "      Permissions: " $1 " Owner: " $3 ":" $4}'
else
    echo "   ✗ server.js MISSING at /opt/AI_CRDC_HUB/mcp-bridge/server.js"
fi

if [ -d /opt/AI_CRDC_HUB/venv ]; then
    echo "   ✓ Python venv exists"
    if [ -f /opt/AI_CRDC_HUB/venv/bin/python ]; then
        echo "      Python: $(/opt/AI_CRDC_HUB/venv/bin/python --version 2>&1)"
    fi
else
    echo "   ✗ Python venv MISSING"
fi

if [ -f /usr/bin/node ]; then
    echo "   ✓ Node.js exists: $(/usr/bin/node --version 2>&1)"
else
    echo "   ✗ Node.js MISSING"
fi

echo ""

# 7. Fix common issues
echo "7. APPLYING FIXES:"
echo "   Enabling services to start on boot..."
sudo systemctl enable app.service 2>/dev/null || echo "      ⚠ Could not enable app.service"
sudo systemctl enable mcp-bridge.service 2>/dev/null || echo "      ⚠ Could not enable mcp-bridge.service"

echo "   Restarting services..."
sudo systemctl restart app.service
sleep 2
sudo systemctl restart mcp-bridge.service
sleep 2

echo "   Checking final status..."
if systemctl is-active --quiet app.service 2>/dev/null; then
    echo "      ✓ app.service is now active"
else
    echo "      ✗ app.service is still inactive"
    echo "      Last 10 lines of log:"
    sudo journalctl -u app.service -n 10 --no-pager | tail -5
fi

if systemctl is-active --quiet mcp-bridge.service 2>/dev/null; then
    echo "      ✓ mcp-bridge.service is now active"
else
    echo "      ✗ mcp-bridge.service is still inactive"
    echo "      Last 10 lines of log:"
    sudo journalctl -u mcp-bridge.service -n 10 --no-pager | tail -5
fi

echo ""

# 8. Final verification
echo "8. FINAL VERIFICATION:"
echo "   Waiting 5 seconds for services to stabilize..."
sleep 5

FLASK_OK=false
MCP_OK=false

if curl -s --max-time 3 http://localhost:5000 > /dev/null 2>&1; then
    FLASK_OK=true
    echo "   ✓ Flask app is responding"
else
    echo "   ✗ Flask app is NOT responding"
fi

if curl -s --max-time 3 http://localhost:3001/health > /dev/null 2>&1; then
    MCP_OK=true
    echo "   ✓ MCP Bridge is responding"
else
    echo "   ✗ MCP Bridge is NOT responding"
fi

echo ""
echo "=========================================="
if [ "$FLASK_OK" = true ] && [ "$MCP_OK" = true ]; then
    echo "✓ ALL SERVICES ARE RUNNING"
    echo ""
    echo "Next steps:"
    echo "1. Wait 2-3 minutes for AWS to re-run status checks"
    echo "2. Refresh EC2 Console → Status checks tab"
    echo "3. Instance status check should pass"
else
    echo "⚠ SOME SERVICES ARE NOT RUNNING"
    echo ""
    echo "Please check the errors above and:"
    echo "1. Review service logs: sudo journalctl -u app.service -n 50"
    echo "2. Review MCP logs: sudo journalctl -u mcp-bridge.service -n 50"
    echo "3. Check for missing dependencies or configuration issues"
fi
echo "=========================================="


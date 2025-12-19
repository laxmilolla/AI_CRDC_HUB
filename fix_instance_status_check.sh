#!/bin/bash
# Fix Instance Status Check Failure
# Run this via EC2 Instance Connect or Systems Manager

echo "=== Diagnosing Instance Status Check Failure ==="
echo ""

# 1. Check if services are running
echo "1. Checking Services:"
echo "   Flask App (app.service):"
if systemctl is-active --quiet app.service 2>/dev/null; then
    echo "      ✓ Running"
else
    echo "      ✗ NOT Running - This is likely the issue!"
    echo "      Attempting to start..."
    sudo systemctl start app.service
    sleep 2
    if systemctl is-active --quiet app.service 2>/dev/null; then
        echo "      ✓ Started successfully"
    else
        echo "      ✗ Failed to start - Check logs below"
        sudo journalctl -u app.service -n 20 --no-pager | tail -10
    fi
fi

echo ""
echo "   MCP Bridge (mcp-bridge.service):"
if systemctl is-active --quiet mcp-bridge.service 2>/dev/null; then
    echo "      ✓ Running"
else
    echo "      ✗ NOT Running"
    echo "      Attempting to start..."
    sudo systemctl start mcp-bridge.service
    sleep 2
    if systemctl is-active --quiet mcp-bridge.service 2>/dev/null; then
        echo "      ✓ Started successfully"
    else
        echo "      ✗ Failed to start - Check logs below"
        sudo journalctl -u mcp-bridge.service -n 20 --no-pager | tail -10
    fi
fi

echo ""

# 2. Check ports
echo "2. Checking Ports:"
if netstat -tuln 2>/dev/null | grep -q ':5000.*LISTEN'; then
    echo "   ✓ Port 5000 (Flask) is listening"
else
    echo "   ✗ Port 5000 (Flask) is NOT listening"
fi

if netstat -tuln 2>/dev/null | grep -q ':3001.*LISTEN'; then
    echo "   ✓ Port 3001 (MCP Bridge) is listening"
else
    echo "   ✗ Port 3001 (MCP Bridge) is NOT listening"
fi

echo ""

# 3. Check HTTP responses
echo "3. Checking HTTP Endpoints:"
if curl -s --max-time 3 http://localhost:5000 > /dev/null 2>&1; then
    echo "   ✓ Flask app responding"
else
    echo "   ✗ Flask app NOT responding"
fi

if curl -s --max-time 3 http://localhost:3001/health > /dev/null 2>&1; then
    echo "   ✓ MCP Bridge responding"
else
    echo "   ✗ MCP Bridge NOT responding"
fi

echo ""

# 4. Check system resources
echo "4. Checking System Resources:"
echo "   Memory:"
free -h | grep Mem | awk '{print "      Used: " $3 " / " $2 " (" int($3/$2*100) "%)"}'

echo "   Disk:"
df -h / | tail -1 | awk '{print "      Used: " $3 " / " $2 " (" $5 ")"}'

echo ""

# 5. Check for common issues
echo "5. Common Issues:"
if [ $(free | grep Mem | awk '{print int($3/$2*100)}') -gt 90 ]; then
    echo "   ⚠ WARNING: Memory usage > 90%"
fi

if [ $(df / | tail -1 | awk '{print $5}' | sed 's/%//') -gt 90 ]; then
    echo "   ⚠ WARNING: Disk usage > 90%"
fi

echo ""

# 6. Restart services if needed
echo "6. Ensuring Services are Enabled and Running:"
sudo systemctl enable app.service 2>/dev/null
sudo systemctl enable mcp-bridge.service 2>/dev/null

sudo systemctl restart app.service
sudo systemctl restart mcp-bridge.service

sleep 3

echo ""
echo "=== Final Status ==="
echo "Flask App: $(systemctl is-active app.service 2>/dev/null || echo 'inactive')"
echo "MCP Bridge: $(systemctl is-active mcp-bridge.service 2>/dev/null || echo 'inactive')"

echo ""
echo "=== Next Steps ==="
echo "1. Wait 2-3 minutes for AWS to re-run status checks"
echo "2. Refresh the EC2 Console status checks page"
echo "3. If still failing, check logs:"
echo "   sudo journalctl -u app.service -n 50"
echo "   sudo journalctl -u mcp-bridge.service -n 50"


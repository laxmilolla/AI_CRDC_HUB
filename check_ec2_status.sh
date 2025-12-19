#!/bin/bash
# Check EC2 instance status and services

echo "=== EC2 Instance Status ==="
echo ""

# Check if we can get instance metadata
echo "1. Instance Metadata:"
if curl -s --max-time 2 http://169.254.169.254/latest/meta-data/instance-id > /dev/null 2>&1; then
    INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
    echo "   ✓ Instance ID: $INSTANCE_ID"
else
    echo "   ✗ Cannot reach instance metadata"
fi

echo ""

# Check systemd services
echo "2. System Services:"
echo "   Flask App (app.service):"
if systemctl is-active --quiet app.service 2>/dev/null; then
    echo "      ✓ Active"
else
    echo "      ✗ Inactive"
    echo "      Status: $(systemctl is-active app.service 2>/dev/null || echo 'failed')"
fi

echo "   MCP Bridge (mcp-bridge.service):"
if systemctl is-active --quiet mcp-bridge.service 2>/dev/null; then
    echo "      ✓ Active"
else
    echo "      ✗ Inactive"
    echo "      Status: $(systemctl is-active mcp-bridge.service 2>/dev/null || echo 'failed')"
fi

echo ""

# Check ports
echo "3. Port Status:"
if netstat -tuln 2>/dev/null | grep -q ':5000'; then
    echo "   ✓ Port 5000 (Flask) is listening"
else
    echo "   ✗ Port 5000 (Flask) is NOT listening"
fi

if netstat -tuln 2>/dev/null | grep -q ':3001'; then
    echo "   ✓ Port 3001 (MCP Bridge) is listening"
else
    echo "   ✗ Port 3001 (MCP Bridge) is NOT listening"
fi

echo ""

# Check HTTP endpoints
echo "4. HTTP Endpoints:"
if curl -s --max-time 2 http://localhost:5000 > /dev/null 2>&1; then
    echo "   ✓ Flask app responding on port 5000"
else
    echo "   ✗ Flask app NOT responding on port 5000"
fi

if curl -s --max-time 2 http://localhost:3001/health > /dev/null 2>&1; then
    echo "   ✓ MCP Bridge responding on port 3001"
    HEALTH=$(curl -s http://localhost:3001/health 2>/dev/null | python3 -c "import sys, json; print(json.load(sys.stdin).get('connected', False))" 2>/dev/null)
    if [ "$HEALTH" = "True" ]; then
        echo "   ✓ MCP Bridge connected to MCP server"
    else
        echo "   ⚠ MCP Bridge running but NOT connected to MCP server"
    fi
else
    echo "   ✗ MCP Bridge NOT responding on port 3001"
fi

echo ""

# Summary
echo "=== Summary ==="
HEALTHY=0
TOTAL=3

[ "$(systemctl is-active app.service 2>/dev/null)" = "active" ] && [ "$(curl -s --max-time 2 http://localhost:5000 > /dev/null 2>&1; echo $?)" = "0" ] && HEALTHY=$((HEALTHY+1))
[ "$(systemctl is-active mcp-bridge.service 2>/dev/null)" = "active" ] && [ "$(curl -s --max-time 2 http://localhost:3001/health > /dev/null 2>&1; echo $?)" = "0" ] && HEALTHY=$((HEALTHY+1))
[ "$(curl -s --max-time 2 http://169.254.169.254/latest/meta-data/instance-id > /dev/null 2>&1; echo $?)" = "0" ] && HEALTHY=$((HEALTHY+1))

echo "Services healthy: $HEALTHY/$TOTAL"


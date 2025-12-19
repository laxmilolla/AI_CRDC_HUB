#!/bin/bash
# Service health check script for EC2 instance

echo "=== Service Health Check ==="
echo ""

# Check Flask app service
echo "1. Flask App (app.service):"
sudo systemctl is-active app.service > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✓ Running"
    curl -s http://localhost:5000 > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "   ✓ Port 5000 responding"
    else
        echo "   ✗ Port 5000 not responding"
    fi
else
    echo "   ✗ Not running"
    echo "   Status: $(sudo systemctl status app.service --no-pager | grep Active | head -1)"
fi

echo ""

# Check MCP bridge service
echo "2. MCP Bridge (mcp-bridge.service):"
sudo systemctl is-active mcp-bridge.service > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✓ Running"
    curl -s http://localhost:3001/health > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "   ✓ Port 3001 responding"
        HEALTH=$(curl -s http://localhost:3001/health | python3 -c "import sys, json; print(json.load(sys.stdin).get('connected', False))" 2>/dev/null)
        if [ "$HEALTH" = "True" ]; then
            echo "   ✓ MCP connected"
        else
            echo "   ⚠ MCP not connected"
        fi
    else
        echo "   ✗ Port 3001 not responding"
    fi
else
    echo "   ✗ Not running"
    echo "   Status: $(sudo systemctl status mcp-bridge.service --no-pager | grep Active | head -1)"
fi

echo ""

# Check AWS Bedrock access
echo "3. AWS Bedrock Connection:"
aws bedrock list-foundation-models --region us-east-1 > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✓ Bedrock accessible"
else
    echo "   ✗ Bedrock not accessible"
    echo "   Check IAM role and permissions"
fi

echo ""
echo "=== Summary ==="
ACTIVE_SERVICES=0
[ "$(sudo systemctl is-active app.service)" = "active" ] && ACTIVE_SERVICES=$((ACTIVE_SERVICES+1))
[ "$(sudo systemctl is-active mcp-bridge.service)" = "active" ] && ACTIVE_SERVICES=$((ACTIVE_SERVICES+1))
[ "$(aws bedrock list-foundation-models --region us-east-1 > /dev/null 2>&1; echo $?)" = "0" ] && ACTIVE_SERVICES=$((ACTIVE_SERVICES+1))

echo "Services healthy: $ACTIVE_SERVICES/3"


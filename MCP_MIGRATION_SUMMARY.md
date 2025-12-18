# MCP Migration Summary

## Problem
The original MCP setup using `@playwright/mcp` (Microsoft's official package) was timing out during initialization. The Python MCP SDK couldn't establish a connection with the server.

## Solution
Switched to `@executeautomation/playwright-mcp-server` which is working on the `agent_llm` EC2 instance. Created a Node.js bridge service to connect Python backend to the JavaScript MCP SDK.

## Architecture

### Before (Not Working)
```
Python Backend → Python MCP SDK → @playwright/mcp (Microsoft)
                                    ❌ Timeout during initialization
```

### After (Working)
```
Python Backend → HTTP API → Node.js Bridge → JavaScript MCP SDK → @executeautomation/playwright-mcp-server
                ✅ Working ✅ Working      ✅ Working              ✅ Working
```

## Components

### 1. MCP Bridge Service (`mcp-bridge/`)
- **Location**: `/opt/AI_CRDC_HUB/mcp-bridge/`
- **Technology**: Node.js with Express
- **Port**: 3001 (default)
- **Service**: `mcp-bridge.service` (systemd)
- **Purpose**: Bridges Python backend to JavaScript MCP SDK

### 2. Updated Python MCP Client (`integrations/mcp_client.py`)
- **Changed**: Now uses HTTP API to call bridge service instead of direct MCP connection
- **Dependencies**: Added `aiohttp>=3.9.0`
- **Interface**: Same interface, different implementation

### 3. MCP Server
- **Package**: `@executeautomation/playwright-mcp-server`
- **Display**: Uses `xvfb-run` for headless execution
- **Tools**: 33 tools available (playwright_navigate, playwright_click, playwright_fill, etc.)

## Tool Name Mapping

The ExecuteAutomation server uses `playwright_` prefixed tool names:

| Our Method | ExecuteAutomation Tool |
|------------|------------------------|
| navigate | playwright_navigate |
| click | playwright_click |
| fill | playwright_fill |
| screenshot | playwright_screenshot |
| get_text | playwright_get_visible_text |
| snapshot | playwright_get_visible_html |

## Installation

### On EC2 Instance

1. **Install xvfb** (for headless display):
   ```bash
   sudo apt install -y xvfb
   ```

2. **Install ExecuteAutomation MCP server**:
   ```bash
   sudo npm install -g @executeautomation/playwright-mcp-server
   ```

3. **Install MCP Bridge dependencies**:
   ```bash
   cd /opt/AI_CRDC_HUB/mcp-bridge
   npm install
   ```

4. **Install Python dependencies**:
   ```bash
   source venv/bin/activate
   pip install aiohttp>=3.9.0
   ```

5. **Start MCP Bridge service**:
   ```bash
   sudo systemctl start mcp-bridge
   sudo systemctl enable mcp-bridge
   ```

6. **Restart main application**:
   ```bash
   sudo systemctl restart ai-crdc-hub
   ```

## Verification

### Check MCP Bridge Status
```bash
sudo systemctl status mcp-bridge
curl http://localhost:3001/health
```

### Test Connection
```bash
curl -X POST http://localhost:3001/connect
```

### List Available Tools
```bash
curl http://localhost:3001/tools
```

## Benefits

1. **Reliable Connection**: No more initialization timeouts
2. **33 Tools Available**: Full Playwright functionality
3. **Headless Support**: xvfb-run enables browser automation on headless servers
4. **Same Interface**: Python backend code doesn't need major changes
5. **Better Error Handling**: HTTP API provides clearer error messages

## Files Changed

- `integrations/mcp_client.py` - Updated to use HTTP bridge
- `requirements.txt` - Added aiohttp
- `deployment/install_dependencies.sh` - Added xvfb and MCP server installation
- `deployment/mcp-bridge.service` - New systemd service file
- `deployment/DEPLOYMENT_GUIDE.md` - Updated with MCP bridge setup
- `mcp-bridge/` - New directory with Node.js bridge service

## Next Steps

1. Test full test execution flow
2. Verify screenshots are captured correctly
3. Test with actual user stories and test cases
4. Monitor performance and adjust timeouts if needed

## Rollback

If needed, can revert to direct Playwright execution (fallback already implemented in `execution_manager.py`).


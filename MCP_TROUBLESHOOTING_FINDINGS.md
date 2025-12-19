# MCP Troubleshooting Findings and Fixes

## Investigation Summary

After investigating the working MCP setup on the `agent_llm` EC2 instance (34.232.241.105), I identified several key differences and implemented fixes to resolve the MCP action execution issues.

## Key Findings

### 1. Working Implementation Analysis
- **Location**: `/home/ubuntu/playwright-chatbot` on `agent_llm` instance
- **MCP Server**: `@executeautomation/playwright-mcp-server` (same as ours)
- **MCP SDK**: `@modelcontextprotocol/sdk` version 1.11.1 (same as ours)
- **Transport**: Uses `xvfb-run -a npx @executeautomation/playwright-mcp-server` (same as ours)

### 2. Available Tools
Confirmed all tool names are correct:
- `playwright_navigate` ✓
- `playwright_click` ✓
- `playwright_fill` ✓
- `playwright_screenshot` ✓
- `playwright_get_visible_text` ✓
- `playwright_get_visible_html` ✓

### 3. Key Differences Identified

#### A. Logging and Debugging
- **Working**: Extensive `console.log('DEBUG: ...')` statements throughout
- **Ours**: Minimal logging
- **Fix**: Added comprehensive logging to bridge client and server

#### B. Error Handling
- **Working**: Detailed error messages with stack traces
- **Ours**: Basic error messages
- **Fix**: Enhanced error handling with stack traces and detailed error information

#### C. Timeout Configuration
- **Working**: No explicit timeouts on tool calls (lets MCP SDK handle naturally)
- **Ours**: 60-second timeout (too short for browser operations)
- **Fix**: Increased timeout to 180 seconds (3 minutes) for browser operations

#### D. Response Handling
- **Working**: Proper JSON parsing with fallback error handling
- **Ours**: Basic JSON parsing
- **Fix**: Enhanced response parsing with better error messages

## Implemented Fixes

### 1. Enhanced Logging (`mcp-bridge/mcp-client.js`)
- Added detailed logging for connection process
- Added logging for tool calls with parameters
- Added error stack traces
- Added tool listing on connection

### 2. Improved Error Handling (`mcp-bridge/mcp-client.js`)
- Enhanced error messages with stack traces
- Better error propagation
- Proper cleanup on connection failure

### 3. Increased Timeouts (`integrations/mcp_client.py`)
- Changed timeout from 60 seconds to 180 seconds (3 minutes)
- Added specific timeout error handling
- Better error messages for timeout scenarios

### 4. Enhanced Response Parsing (`integrations/mcp_client.py`)
- Better JSON parsing with error handling
- Detailed error messages when parsing fails
- Logging of successful and failed operations

### 5. Server-Side Logging (`mcp-bridge/server.js`)
- Added logging for all endpoint calls
- Added logging for tool call results
- Enhanced error logging with stack traces

## Files Modified

1. `mcp-bridge/mcp-client.js`
   - Enhanced `connect()` method with detailed logging
   - Enhanced `callTool()` method with better error handling
   - Added stack traces to error responses

2. `mcp-bridge/server.js`
   - Added logging to `/navigate` endpoint
   - Added logging to `/call_tool` endpoint
   - Enhanced error responses with stack traces

3. `integrations/mcp_client.py`
   - Increased timeout from 60 to 180 seconds
   - Enhanced `_call_bridge()` with better error handling
   - Added detailed logging for bridge calls
   - Added timeout-specific error handling

## Next Steps

1. **Deploy the fixes** to the EC2 instance
2. **Restart the MCP bridge service**:
   ```bash
   sudo systemctl restart mcp-bridge.service
   sudo systemctl status mcp-bridge.service
   ```
3. **Monitor logs** during test execution:
   ```bash
   sudo journalctl -u mcp-bridge.service -f
   ```
4. **Test with a simple navigation** to verify the fixes work

## Expected Improvements

- **Better visibility**: Comprehensive logging will help identify where issues occur
- **More reliable**: Increased timeouts should prevent premature timeouts
- **Better debugging**: Stack traces and detailed error messages will help diagnose issues
- **Consistent behavior**: Aligned with the working implementation patterns

## Potential Remaining Issues

If issues persist after these fixes, consider:

1. **Browser initialization**: The browser might not be initializing properly
2. **xvfb-run configuration**: There might be display issues with xvfb
3. **Network connectivity**: The target URLs might be unreachable
4. **Playwright browser installation**: Browsers might not be properly installed
5. **Resource constraints**: The EC2 instance might be running out of memory/CPU

## Testing Checklist

- [ ] Deploy updated code to EC2
- [ ] Restart MCP bridge service
- [ ] Test simple navigation (e.g., `playwright_navigate` to `https://example.com`)
- [ ] Test screenshot capture
- [ ] Test click action
- [ ] Test fill action
- [ ] Monitor logs for any errors
- [ ] Verify screenshots are saved correctly


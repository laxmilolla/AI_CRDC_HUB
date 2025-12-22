/**
 * HTTP API Server for MCP Bridge
 * Exposes MCP Playwright methods as HTTP endpoints for Python backend
 */

const express = require('express');
const cors = require('cors');
const MCPPlaywrightBridge = require('./mcp-client');

const app = express();
app.use(cors());
app.use(express.json());

const PORT = process.env.MCP_BRIDGE_PORT || 3001;
const mcpBridge = new MCPPlaywrightBridge();

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', connected: mcpBridge.connected });
});

// Connect to MCP server
app.post('/connect', async (req, res) => {
  try {
    // If already connected, return success
    if (mcpBridge.connected) {
      return res.json({ success: true, message: 'Already connected' });
    }
    
    const result = await mcpBridge.connect();
    res.json(result);
  } catch (error) {
    console.error('[MCP Bridge] Connect endpoint error:', error);
    res.status(500).json({ 
      success: false, 
      error: error.message || String(error)
    });
  }
});

// Navigate to URL
app.post('/navigate', async (req, res) => {
  try {
    const { url } = req.body;
    if (!url) {
      return res.status(400).json({ error: 'url is required' });
    }
    console.log(`[MCP Bridge] Navigate endpoint called with URL: ${url}`);
    const result = await mcpBridge.navigate(url);
    console.log(`[MCP Bridge] Navigate result:`, JSON.stringify(result));
    res.json(result);
  } catch (error) {
    console.error('[MCP Bridge] Navigate endpoint error:', error);
    res.status(500).json({ 
      success: false, 
      error: error.message || String(error),
      errorStack: error.stack
    });
  }
});

// Click element
app.post('/click', async (req, res) => {
  try {
    const { selector } = req.body;
    if (!selector) {
      return res.status(400).json({ error: 'selector is required' });
    }
    const result = await mcpBridge.click(selector);
    res.json(result);
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error.message 
    });
  }
});

// Fill input
app.post('/fill', async (req, res) => {
  try {
    const { selector, text } = req.body;
    if (!selector || !text) {
      return res.status(400).json({ error: 'selector and text are required' });
    }
    const result = await mcpBridge.fill(selector, text);
    res.json(result);
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error.message 
    });
  }
});

// Type text character by character (for problematic input fields)
app.post('/type', async (req, res) => {
  try {
    const { selector, text } = req.body;
    if (!selector || !text) {
      return res.status(400).json({ error: 'selector and text are required' });
    }
    const result = await mcpBridge.type(selector, text);
    res.json(result);
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error.message 
    });
  }
});

// Take screenshot
app.post('/screenshot', async (req, res) => {
  try {
    const { path, name, savePng, fullPage } = req.body;
    
    // Support both old (path) and new (name, savePng, fullPage) parameter formats
    if (path) {
      // Legacy format: extract name from path
      const result = await mcpBridge.screenshot(path);
      res.json(result);
    } else if (name) {
      // New format: use name, savePng, fullPage
      const result = await mcpBridge.screenshotWithOptions({ name, savePng, fullPage });
      res.json(result);
    } else {
      return res.status(400).json({ error: 'Either "path" or "name" is required' });
    }
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error.message 
    });
  }
});

// Get text
app.post('/get_text', async (req, res) => {
  try {
    const { selector } = req.body;
    if (!selector) {
      return res.status(400).json({ error: 'selector is required' });
    }
    const result = await mcpBridge.getText(selector);
    res.json(result);
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error.message 
    });
  }
});

// Wait for element
app.post('/wait_for', async (req, res) => {
  try {
    const { selector, timeout } = req.body;
    if (!selector) {
      return res.status(400).json({ error: 'selector is required' });
    }
    const result = await mcpBridge.waitFor(selector, timeout || 30000);
    res.json(result);
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error.message 
    });
  }
});

// Evaluate JavaScript in page context
app.post('/evaluate', async (req, res) => {
  try {
    const { code } = req.body;
    if (!code) {
      return res.status(400).json({ error: 'code is required' });
    }
    const result = await mcpBridge.evaluate(code);
    res.json(result);
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error.message 
    });
  }
});

// Get page snapshot
app.post('/snapshot', async (req, res) => {
  try {
    const result = await mcpBridge.snapshot();
    res.json(result);
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error.message 
    });
  }
});

// Generic tool call
app.post('/call_tool', async (req, res) => {
  try {
    const { name, arguments: args } = req.body;
    if (!name) {
      return res.status(400).json({ error: 'tool name is required' });
    }
    console.log(`[MCP Bridge] Generic tool call endpoint: ${name}`);
    const result = await mcpBridge.callTool(name, args || {});
    console.log(`[MCP Bridge] Tool call result:`, JSON.stringify(result));
    res.json(result);
  } catch (error) {
    console.error('[MCP Bridge] Generic tool call endpoint error:', error);
    res.status(500).json({ 
      success: false, 
      error: error.message || String(error),
      errorStack: error.stack
    });
  }
});

// List available tools
app.get('/tools', async (req, res) => {
  try {
    if (!mcpBridge.connected) {
      await mcpBridge.connect();
    }
    const tools = mcpBridge.getTools();
    res.json({ success: true, tools: tools.map(t => ({ name: t.name, description: t.description })) });
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error.message 
    });
  }
});

// Get tool schema/details
app.get('/tools/:toolName', async (req, res) => {
  try {
    const { toolName } = req.params;
    if (!mcpBridge.connected) {
      await mcpBridge.connect();
    }
    const tools = mcpBridge.getTools();
    const tool = tools.find(t => t.name === toolName);
    if (tool) {
      res.json({ success: true, tool: tool });
    } else {
      res.status(404).json({ success: false, error: 'Tool not found' });
    }
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error.message 
    });
  }
});

// Disconnect
app.post('/disconnect', async (req, res) => {
  try {
    await mcpBridge.disconnect();
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error.message 
    });
  }
});

// Graceful shutdown
process.on('SIGTERM', async () => {
  console.log('[MCP Bridge] SIGTERM received, shutting down...');
  await mcpBridge.disconnect();
  process.exit(0);
});

process.on('SIGINT', async () => {
  console.log('[MCP Bridge] SIGINT received, shutting down...');
  await mcpBridge.disconnect();
  process.exit(0);
});

app.listen(PORT, () => {
  console.log(`[MCP Bridge] Server running on port ${PORT}`);
});


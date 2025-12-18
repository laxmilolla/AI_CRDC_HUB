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
    const result = await mcpBridge.navigate(url);
    res.json(result);
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error.message 
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

// Take screenshot
app.post('/screenshot', async (req, res) => {
  try {
    const { path } = req.body;
    if (!path) {
      return res.status(400).json({ error: 'path is required' });
    }
    const result = await mcpBridge.screenshot(path);
    res.json(result);
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
    const result = await mcpBridge.callTool(name, args || {});
    res.json(result);
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error.message 
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


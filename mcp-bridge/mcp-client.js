/**
 * MCP Client for ExecuteAutomation Playwright MCP Server
 * Bridges between Python backend and JavaScript MCP SDK
 */

const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');

class MCPPlaywrightBridge {
  constructor() {
    this.client = null;
    this.transport = null;
    this.connected = false;
  }

  async connect() {
    if (this.connected) {
      return;
    }

    try {
      console.log('[MCP Bridge] Connecting to ExecuteAutomation MCP server...');
      
      this.transport = new StdioClientTransport({
        command: 'xvfb-run',
        args: ['-a', 'npx', '@executeautomation/playwright-mcp-server']
      });

      this.client = new Client(
        {
          name: 'ai-crdc-hub',
          version: '1.0.0'
        },
        {
          capabilities: {
            tools: {}
          }
        }
      );

      await this.client.connect(this.transport);
      this.connected = true;
      console.log('[MCP Bridge] Connected successfully');

      // List available tools
      const toolsResponse = await this.client.listTools();
      this.tools = toolsResponse.tools;
      console.log(`[MCP Bridge] Available tools: ${this.tools.length}`);
      
      return { success: true, tools: this.tools.length, toolNames: this.tools.map(t => t.name) };
    } catch (error) {
      console.error('[MCP Bridge] Connection failed:', error);
      this.connected = false;
      throw error;
    }
  }

  async callTool(name, arguments_) {
    if (!this.connected || !this.client) {
      await this.connect();
    }

    try {
      const result = await this.client.callTool({
        name: name,
        arguments: arguments_
      });

      return {
        success: true,
        content: result.content
      };
    } catch (error) {
      console.error(`[MCP Bridge] Tool call failed (${name}):`, error);
      return {
        success: false,
        error: error.message
      };
    }
  }

  async navigate(url) {
    return await this.callTool('navigate', { url });
  }

  async click(selector) {
    return await this.callTool('click', { selector });
  }

  async fill(selector, text) {
    return await this.callTool('fill', { selector, text });
  }

  async screenshot(path) {
    return await this.callTool('screenshot', { path });
  }

  async getText(selector) {
    return await this.callTool('get_text', { selector });
  }

  async waitFor(selector, timeout = 30000) {
    return await this.callTool('wait_for', { selector, timeout });
  }

  async snapshot() {
    return await this.callTool('snapshot', {});
  }

  getTools() {
    return this.tools || [];
  }

  async disconnect() {
    if (this.client) {
      try {
        this.client.close();
      } catch (e) {
        // Ignore errors on close
      }
      this.client = null;
    }
    this.connected = false;
    this.tools = null;
    console.log('[MCP Bridge] Disconnected');
  }
}

module.exports = MCPPlaywrightBridge;


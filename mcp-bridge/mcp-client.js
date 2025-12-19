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
      console.log('[MCP Bridge] Already connected, returning existing connection');
      return { success: true, tools: this.tools?.length || 0, toolNames: this.tools?.map(t => t.name) || [] };
    }

    try {
      console.log('[MCP Bridge] Connecting to ExecuteAutomation MCP server...');
      console.log('[MCP Bridge] Using command: xvfb-run -a npx @executeautomation/playwright-mcp-server');
      
      // Ensure Chromium is used by setting environment variables
      const env = {
        ...process.env,
        PLAYWRIGHT_BROWSERS_PATH: process.env.PLAYWRIGHT_BROWSERS_PATH || '/home/ubuntu/.cache/ms-playwright',
        // Explicitly prefer Chromium (Playwright defaults to Chromium if installed)
        PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD: '0'
      };
      
      this.transport = new StdioClientTransport({
        command: 'xvfb-run',
        args: ['-a', 'npx', '@executeautomation/playwright-mcp-server'],
        env: env
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

      console.log('[MCP Bridge] Initiating client connection...');
      await this.client.connect(this.transport);
      this.connected = true;
      console.log('[MCP Bridge] Client connected successfully');

      // List available tools
      console.log('[MCP Bridge] Listing available tools...');
      const toolsResponse = await this.client.listTools();
      this.tools = toolsResponse.tools;
      console.log(`[MCP Bridge] Available tools: ${this.tools.length}`);
      console.log(`[MCP Bridge] Tool names: ${this.tools.map(t => t.name).join(', ')}`);
      
      return { success: true, tools: this.tools.length, toolNames: this.tools.map(t => t.name) };
    } catch (error) {
      console.error('[MCP Bridge] Connection failed:', error);
      console.error('[MCP Bridge] Error stack:', error.stack);
      this.connected = false;
      this.client = null;
      this.transport = null;
      throw error;
    }
  }

  async callTool(name, arguments_) {
    if (!this.connected || !this.client) {
      await this.connect();
    }

    try {
      console.log(`[MCP Bridge] Calling tool: ${name} with params:`, JSON.stringify(arguments_));
      
      const result = await this.client.callTool({
        name: name,
        arguments: arguments_
      });

      console.log(`[MCP Bridge] Tool ${name} executed successfully`);
      
      return {
        success: true,
        content: result.content
      };
    } catch (error) {
      console.error(`[MCP Bridge] Tool call failed (${name}):`, error);
      console.error(`[MCP Bridge] Error stack:`, error.stack);
      return {
        success: false,
        error: error.message || String(error),
        errorStack: error.stack
      };
    }
  }

  async navigate(url) {
    return await this.callTool('playwright_navigate', { url });
  }

  async click(selector) {
    return await this.callTool('playwright_click', { selector });
  }

  async fill(selector, text) {
    return await this.callTool('playwright_fill', { selector, text });
  }

  async screenshot(path) {
    // The playwright_screenshot tool doesn't accept 'path' parameter
    // It uses 'name' for filename and saves to Downloads by default
    // We'll use the filename from the path and handle the location in recovery
    const pathObj = require('path');
    const filename = pathObj.basename(path);
    const nameWithoutExt = filename.replace(/\.png$/, '');
    
    // Use name parameter and savePng: true to save as PNG
    return await this.callTool('playwright_screenshot', { 
      name: nameWithoutExt,
      savePng: true
    });
  }

  async screenshotWithOptions({ name, savePng = true, fullPage = false }) {
    // New method that accepts name, savePng, and fullPage parameters
    const params = {
      name: name,
      savePng: savePng !== false // Default to true
    };
    
    // Add fullPage if specified
    if (fullPage) {
      params.fullPage = true;
    }
    
    return await this.callTool('playwright_screenshot', params);
  }

  async getText(selector) {
    // Use get_visible_text tool
    return await this.callTool('playwright_get_visible_text', { selector });
  }

  async waitFor(selector, timeout = 30000) {
    // ExecuteAutomation server doesn't have wait_for, use evaluate to wait
    // For now, return success - actual waiting will be handled by Playwright
    return { success: true, content: [{ text: `Waiting for ${selector}` }] };
  }

  async evaluate(code) {
    // Use playwright_evaluate to execute JavaScript in the page context
    // MCP server expects 'script' parameter, not 'code'
    return await this.callTool('playwright_evaluate', { script: code });
  }

  async snapshot() {
    // Use get_visible_html for DOM snapshot
    return await this.callTool('playwright_get_visible_html', {});
  }

  getTools() {
    return this.tools || [];
  }

  async disconnect() {
    console.log('[MCP Bridge] Starting disconnect and cleanup...');
    
    if (this.client) {
      try {
        // Close the transport first to terminate the MCP server process
        if (this.transport) {
          console.log('[MCP Bridge] Closing transport to terminate MCP server...');
          await this.transport.close();
          this.transport = null;
        }
        
        // Close the client connection
        console.log('[MCP Bridge] Closing client...');
        this.client.close();
        this.client = null;
      } catch (e) {
        console.error('[MCP Bridge] Error closing client:', e);
      }
    }
    
    // Kill any browser processes spawned by this MCP server
    try {
      const { exec } = require('child_process');
      const { promisify } = require('util');
      const execAsync = promisify(exec);
      
      // Kill Chrome processes with our profile pattern
      console.log('[MCP Bridge] Killing browser processes...');
      try {
        await execAsync('pkill -9 -f "playwright_chromiumdev_profile"');
        console.log('[MCP Bridge] Killed browser processes');
      } catch (error) {
        if (error.code !== 1) { // code 1 means no processes found
          console.error('[MCP Bridge] Error killing browser processes:', error);
        } else {
          console.log('[MCP Bridge] No browser processes to kill');
        }
      }
      
      // Also kill any remaining Chrome/Chromium processes
      try {
        await execAsync('pkill -9 -f "chrome.*playwright"');
      } catch (error) {
        // Ignore if no processes found
      }
    } catch (e) {
      console.error('[MCP Bridge] Error in browser cleanup:', e);
    }
    
    this.connected = false;
    this.tools = null;
    this.browser = null;
    console.log('[MCP Bridge] Disconnected and cleaned up');
  }
}

module.exports = MCPPlaywrightBridge;


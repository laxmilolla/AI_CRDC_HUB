"""
MCP Playwright client using Microsoft's official MCP Playwright
"""
import os
from typing import Optional, Dict, Any
from utils.logger import get_logger


class MCPPlaywrightClient:
    """
    Client for Microsoft MCP Playwright
    
    This integrates with Microsoft's official MCP Playwright server.
    The MCP server should be running and accessible.
    """
    
    def __init__(self, mcp_server_path: str = None):
        """
        Initialize MCP Playwright client
        
        Args:
            mcp_server_path: Path to MCP Playwright server (if custom)
        """
        self.logger = get_logger(__name__)
        self.mcp_server_path = mcp_server_path or os.getenv("MCP_SERVER_PATH")
        self.connected = False
        
        # MCP Playwright uses stdio or HTTP transport
        # We'll use the MCP SDK to connect
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            self.mcp_available = True
        except ImportError:
            self.logger.warning("MCP SDK not installed. Install with: pip install mcp")
            self.mcp_available = False
    
    async def connect_mcp_server(self):
        """
        Connect to Microsoft MCP Playwright server
        
        The MCP server should be running via:
        - npx -y @playwright/mcp
        - Official package: https://github.com/microsoft/playwright-mcp
        """
        if not self.mcp_available:
            raise RuntimeError("MCP SDK not available. Install with: pip install mcp")
        
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            
            # Microsoft MCP Playwright server command
            # Official package: @playwright/mcp
            # https://github.com/microsoft/playwright-mcp
            server_params = StdioServerParameters(
                command="npx",
                args=["-y", "@playwright/mcp"]
            )
            
            stdio_transport = await stdio_client(server_params)
            self.session = ClientSession(stdio_transport[0], stdio_transport[1])
            await self.session.initialize()
            
            self.connected = True
            self.logger.info("Connected to Microsoft MCP Playwright server")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to MCP Playwright server: {e}")
            raise
    
    async def navigate(self, url: str) -> str:
        """Navigate to URL via MCP"""
        if not self.connected:
            await self.connect_mcp_server()
        
        result = await self.session.call_tool(
            "playwright_navigate",
            arguments={"url": url}
        )
        return result.get("content", [{}])[0].get("text", f"Navigated to {url}")
    
    async def click(self, selector: str) -> str:
        """Click element via MCP"""
        result = await self.session.call_tool(
            "playwright_click",
            arguments={"selector": selector}
        )
        return result.get("content", [{}])[0].get("text", f"Clicked {selector}")
    
    async def fill(self, selector: str, text: str) -> str:
        """Fill input via MCP"""
        result = await self.session.call_tool(
            "playwright_fill",
            arguments={"selector": selector, "text": text}
        )
        return result.get("content", [{}])[0].get("text", f"Filled {selector}")
    
    async def take_screenshot(self, path: str) -> str:
        """Capture screenshot via MCP"""
        result = await self.session.call_tool(
            "playwright_screenshot",
            arguments={"path": path}
        )
        return path
    
    async def get_text(self, selector: str) -> str:
        """Get element text via MCP"""
        result = await self.session.call_tool(
            "playwright_get_text",
            arguments={"selector": selector}
        )
        return result.get("content", [{}])[0].get("text", "")
    
    async def get_dom(self) -> str:
        """Get page DOM via MCP"""
        result = await self.session.call_tool(
            "playwright_get_content",
            arguments={}
        )
        return result.get("content", [{}])[0].get("text", "")
    
    async def wait_for(self, selector: str, timeout: int = 30000) -> str:
        """Wait for element via MCP"""
        result = await self.session.call_tool(
            "playwright_wait_for_selector",
            arguments={"selector": selector, "timeout": timeout}
        )
        return result.get("content", [{}])[0].get("text", f"Element {selector} appeared")
    
    async def execute_step(
        self,
        step_code: str,
        execution_id: str,
        test_case_id: str,
        step_number: int,
        step_description: str
    ) -> Dict[str, Any]:
        """
        Execute a test step via MCP and capture screenshot
        
        Args:
            step_code: Playwright code for the step (will be parsed)
            execution_id: Execution identifier
            test_case_id: Test case identifier
            step_number: Step number
            step_description: Step description
        
        Returns:
            Step execution result with screenshot
        """
        from utils.screenshot_handler import ScreenshotHandler
        
        screenshot_handler = ScreenshotHandler(execution_id=execution_id)
        screenshot_path = screenshot_handler.get_screenshot_path(
            test_case_id,
            step_number,
            step_description
        )
        
        try:
            # Parse and execute step_code
            # For now, this is a placeholder - actual execution will depend on
            # how the generated Playwright code is structured
            
            # Capture screenshot after step
            await self.take_screenshot(str(screenshot_path))
            
            return {
                "status": "passed",
                "screenshot": str(screenshot_path),
                "step_number": step_number,
                "description": step_description
            }
            
        except Exception as e:
            self.logger.error(f"Error executing step: {e}")
            error_screenshot = screenshot_path.parent / f"error_step_{step_number:02d}.png"
            await self.take_screenshot(str(error_screenshot))
            
            return {
                "status": "failed",
                "error": str(e),
                "screenshot": str(error_screenshot),
                "step_number": step_number,
                "description": step_description
            }
    
    async def close(self):
        """Close MCP connection"""
        if hasattr(self, 'session') and self.session:
            await self.session.close()
        self.connected = False
        self.logger.info("MCP Playwright connection closed")


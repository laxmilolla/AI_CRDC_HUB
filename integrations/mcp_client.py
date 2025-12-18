"""
MCP Playwright client using ExecuteAutomation's MCP Playwright server
Uses Node.js bridge service for reliable connection
"""
import os
import requests
from typing import Optional, Dict, Any
from utils.logger import get_logger


class MCPPlaywrightClient:
    """
    Client for ExecuteAutomation MCP Playwright
    
    This integrates with @executeautomation/playwright-mcp-server via Node.js bridge.
    The bridge service runs on localhost:3001 by default.
    """
    
    def __init__(self, mcp_server_path: str = None, bridge_url: str = None):
        """
        Initialize MCP Playwright client
        
        Args:
            mcp_server_path: Path to MCP Playwright server (deprecated, using bridge)
            bridge_url: URL of the MCP bridge service (default: http://localhost:3001)
        """
        self.logger = get_logger(__name__)
        self.bridge_url = bridge_url or os.getenv("MCP_BRIDGE_URL", "http://localhost:3001")
        self.connected = False
    
    async def connect_mcp_server(self):
        """
        Connect to ExecuteAutomation MCP Playwright server via Node.js bridge
        
        The bridge service should be running (see mcp-bridge/server.js)
        """
        if self.connected:
            return
        
        try:
            import asyncio
            import aiohttp
            
            self.logger.info(f"Connecting to MCP bridge at {self.bridge_url}...")
            
            # Check if bridge is running
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(f"{self.bridge_url}/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        if resp.status != 200:
                            raise RuntimeError(f"MCP bridge health check failed: {resp.status}")
                except aiohttp.ClientError as e:
                    raise RuntimeError(f"Cannot reach MCP bridge at {self.bridge_url}. Is it running? Error: {e}")
            
            # Connect via bridge
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.bridge_url}/connect", timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        raise RuntimeError(f"MCP bridge connection failed: {error_text}")
                    
                    result = await resp.json()
                    if not result.get('success'):
                        raise RuntimeError(f"MCP connection failed: {result.get('error', 'Unknown error')}")
            
            self.connected = True
            self.logger.info("Connected to ExecuteAutomation MCP Playwright server via bridge")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to MCP Playwright server: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            raise
    
    async def _call_bridge(self, endpoint: str, data: dict = None) -> dict:
        """Call MCP bridge HTTP endpoint"""
        if not self.connected:
            await self.connect_mcp_server()
        
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.bridge_url}/{endpoint}",
                json=data or {},
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise RuntimeError(f"Bridge call failed ({endpoint}): {error_text}")
                return await resp.json()
    
    async def navigate(self, url: str) -> str:
        """Navigate to URL via MCP bridge"""
        result = await self._call_bridge("navigate", {"url": url})
        if result.get("success"):
            return f"Navigated to {url}"
        else:
            raise RuntimeError(result.get("error", "Navigation failed"))
    
    async def click(self, selector: str) -> str:
        """Click element via MCP bridge"""
        result = await self._call_bridge("click", {"selector": selector})
        if result.get("success"):
            return f"Clicked {selector}"
        else:
            raise RuntimeError(result.get("error", "Click failed"))
    
    async def fill(self, selector: str, text: str) -> str:
        """Fill input via MCP bridge"""
        result = await self._call_bridge("fill", {"selector": selector, "text": text})
        if result.get("success"):
            return f"Filled {selector}"
        else:
            raise RuntimeError(result.get("error", "Fill failed"))
    
    async def take_screenshot(self, path: str) -> str:
        """Capture screenshot via MCP bridge"""
        result = await self._call_bridge("screenshot", {"path": path})
        if result.get("success"):
            return path
        else:
            raise RuntimeError(result.get("error", "Screenshot failed"))
    
    async def get_text(self, selector: str) -> str:
        """Get element text via MCP bridge"""
        result = await self._call_bridge("get_text", {"selector": selector})
        if result.get("success"):
            content = result.get("content", [])
            if content and len(content) > 0:
                return content[0].get("text", "")
            return ""
        else:
            raise RuntimeError(result.get("error", "Get text failed"))
    
    async def get_dom(self) -> str:
        """Get page DOM via MCP bridge"""
        result = await self._call_bridge("snapshot", {})
        if result.get("success"):
            content = result.get("content", [])
            if content and len(content) > 0:
                return content[0].get("text", "")
            return ""
        else:
            raise RuntimeError(result.get("error", "Get DOM failed"))
    
    async def wait_for(self, selector: str, timeout: int = 30000) -> str:
        """Wait for element via MCP bridge"""
        result = await self._call_bridge("wait_for", {"selector": selector, "timeout": timeout})
        if result.get("success"):
            return f"Element {selector} appeared"
        else:
            raise RuntimeError(result.get("error", "Wait for failed"))
    
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
        """Close MCP connection via bridge"""
        if self.connected:
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.bridge_url}/disconnect",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as resp:
                        # Ignore errors on disconnect
                        pass
            except:
                pass
        
        self.connected = False
        self.logger.info("MCP Playwright connection closed")


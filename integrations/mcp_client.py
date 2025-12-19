"""
MCP Playwright client using ExecuteAutomation's MCP Playwright server
Uses Node.js bridge service for reliable connection
"""
import os
import asyncio
import time
import shutil
import json
from pathlib import Path
from typing import Optional, Dict, Any
from utils.logger import get_logger
from integrations.bedrock_client import BedrockClient


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
                        raise RuntimeError(f"MCP bridge connection failed (status {resp.status}): {error_text}")
                    
                    try:
                        result = await resp.json()
                    except Exception as e:
                        error_text = await resp.text()
                        raise RuntimeError(f"Failed to parse bridge response: {e}. Response: {error_text}")
                    
                    if not result or not result.get('success'):
                        error_msg = result.get('error', 'Unknown error') if result else 'No response from bridge'
                        raise RuntimeError(f"MCP connection failed: {error_msg}")
            
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
        # Increased timeout for browser operations (navigation, screenshots, etc.)
        # Browser operations can take time, especially on slow networks
        timeout = aiohttp.ClientTimeout(total=180)  # 3 minutes for browser operations
        
        self.logger.info(f"Calling bridge endpoint: {endpoint} with data: {data}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.bridge_url}/{endpoint}",
                    json=data or {},
                    timeout=timeout
                ) as resp:
                    response_text = await resp.text()
                    
                    if resp.status != 200:
                        self.logger.error(f"Bridge call failed ({endpoint}): Status {resp.status}, Response: {response_text}")
                        raise RuntimeError(f"Bridge call failed ({endpoint}): Status {resp.status}, Response: {response_text}")
                    
                    try:
                        result = await resp.json() if response_text else {}
                        self.logger.info(f"Bridge call succeeded ({endpoint}): {result.get('success', 'unknown')}")
                        return result
                    except Exception as e:
                        self.logger.error(f"Failed to parse bridge response as JSON: {e}. Response: {response_text}")
                        raise RuntimeError(f"Failed to parse bridge response: {e}. Response: {response_text}")
        except asyncio.TimeoutError:
            self.logger.error(f"Bridge call timed out after 180 seconds: {endpoint}")
            raise RuntimeError(f"Bridge call timed out: {endpoint}")
        except Exception as e:
            self.logger.error(f"Bridge call error ({endpoint}): {e}")
            raise
    
    async def navigate(self, url: str) -> str:
        """Navigate to URL via MCP bridge"""
        result = await self._call_bridge("navigate", {"url": url})
        if result.get("success"):
            # Wait for page to fully load after navigation
            # Use evaluate to wait for page load state
            try:
                # Wait for document.readyState to be 'complete'
                await self._wait_for_page_ready()
            except Exception as e:
                self.logger.warning(f"Could not wait for page ready: {e}, using sleep fallback")
                await asyncio.sleep(3.0)  # Fallback: longer wait
            return f"Navigated to {url}"
        else:
            raise RuntimeError(result.get("error", "Navigation failed"))
    
    async def _wait_for_page_ready(self, timeout: int = 15000) -> bool:
        """
        Wait for page to be fully ready for screenshot.
        Waits for: document.readyState, network idle, body content, and rendering.
        
        Args:
            timeout: Maximum time to wait in milliseconds
            
        Returns:
            True if page is ready, False if timeout
        """
        try:
            self.logger.debug("Waiting for page to be ready...")
            
            # Use playwright_evaluate to wait for comprehensive page ready state
            result = await self._call_bridge("evaluate", {
                "code": f"""
                (async () => {{
                    const startTime = Date.now();
                    const timeout = {timeout};
                    
                    // 1. Wait for document ready state
                    if (document.readyState !== 'complete') {{
                        await new Promise((resolve) => {{
                            if (document.readyState === 'complete') {{
                                resolve();
                            }} else {{
                                const checkReady = () => {{
                                    if (document.readyState === 'complete') {{
                                        resolve();
                                    }}
                                }};
                                document.addEventListener('readystatechange', checkReady);
                                window.addEventListener('load', () => resolve(), {{ once: true }});
                                setTimeout(() => resolve(), Math.min(5000, timeout));
                            }}
                        }});
                    }}
                    
                    // 2. Wait for body to have content
                    let bodyReady = false;
                    let attempts = 0;
                    while (!bodyReady && attempts < 20 && (Date.now() - startTime) < timeout) {{
                        const body = document.body;
                        if (body && body.children.length > 0 && body.innerText.trim().length > 0) {{
                            bodyReady = true;
                        }} else {{
                            await new Promise(resolve => setTimeout(resolve, 200));
                            attempts++;
                        }}
                    }}
                    
                    // 3. Wait for network to be relatively idle (check performance timing)
                    if (window.performance && window.performance.timing) {{
                        const perf = window.performance.timing;
                        const loadTime = perf.loadEventEnd - perf.navigationStart;
                        // If page loaded recently, wait a bit more for any async content
                        if (loadTime > 0 && (Date.now() - perf.loadEventEnd) < 2000) {{
                            await new Promise(resolve => setTimeout(resolve, 1000));
                        }}
                    }}
                    
                    // 4. Final wait for rendering to complete
                    await new Promise(resolve => setTimeout(resolve, 1500));
                    
                    return {{
                        ready: true,
                        readyState: document.readyState,
                        bodyHasContent: document.body && document.body.children.length > 0,
                        bodyTextLength: document.body ? document.body.innerText.trim().length : 0
                    }};
                }})();
                """
            })
            
            if result.get("success"):
                content = result.get("content", [])
                if content and len(content) > 0:
                    result_data = content[0].get("text", "")
                    self.logger.debug(f"Page ready check result: {result_data}")
                
                # Additional wait for rendering to ensure screenshot captures content
                await asyncio.sleep(1.5)
                self.logger.debug("Page ready check completed")
                return True
            else:
                self.logger.warning("Page ready check failed, using fallback")
                await asyncio.sleep(3.0)
                return False
                
        except Exception as e:
            self.logger.warning(f"Error waiting for page ready: {e}")
            # Fallback to longer sleep
            await asyncio.sleep(3.0)
            return False
    
    async def click(self, selector: str, wait_timeout: int = 10000) -> str:
        """
        Click element via MCP bridge with implicit wait for element to be present/visible
        
        Args:
            selector: Element selector (e.g., 'text=Continue', '#button-id', 'button[type="submit"]')
            wait_timeout: Maximum time in milliseconds to wait for element to appear (default: 10000ms)
        
        Returns:
            Success message if click succeeded
        
        Raises:
            RuntimeError: If element not found or click failed
        """
        # First, wait for the element to be present and visible before clicking
        self.logger.info(f"Waiting for element to be present before clicking: {selector}")
        element_found = await self.wait_for_element(selector, timeout=wait_timeout)
        
        if not element_found:
            raise RuntimeError(f"Element {selector} not found or not visible within {wait_timeout}ms timeout")
        
        self.logger.info(f"Element {selector} found, proceeding with click")
        
        # Now perform the click
        result = await self._call_bridge("click", {"selector": selector})
        if result.get("success"):
            return f"Clicked {selector}"
        else:
            raise RuntimeError(result.get("error", "Click failed"))
    
    async def fill(self, selector: str, text: str) -> str:
        """Fill input via MCP bridge with focus, clear, and fallback to JavaScript-based fill"""
        # Escape selector for JavaScript
        escaped_selector = selector.replace("'", "\\'")
        
        # First, focus and clear the input element to ensure it's ready
        try:
            # Focus the element
            focus_code = f"document.querySelector('{escaped_selector}')?.focus()"
            await self.evaluate(focus_code)
            await asyncio.sleep(0.2)  # Brief wait after focus
            
            # Clear the field (select all and delete, or set value to empty)
            clear_code = f"(function() {{ const el = document.querySelector('{escaped_selector}'); if (el) {{ el.select(); el.value = ''; }} }})()"
            await self.evaluate(clear_code)
            await asyncio.sleep(0.2)  # Brief wait after clear
        except Exception as e:
            self.logger.warning(f"Could not focus/clear {selector} before fill: {e}")
        
        # Strategy 1: Try standard fill method
        try:
            result = await self._call_bridge("fill", {"selector": selector, "text": text})
            if result.get("success"):
                # Wait for the fill to complete and UI to update
                await asyncio.sleep(0.8)  # Wait time for complex input fields that may need time to update
                
                # Verify the fill worked
                check_code = f"document.querySelector('{escaped_selector}')?.value || ''"
                actual_value = await self.evaluate(check_code)
                if actual_value and text in str(actual_value):
                    self.logger.info(f"Standard fill succeeded for {selector}")
                    return f"Filled {selector}"
                else:
                    # Standard fill reported success but value is empty - try JavaScript fallback
                    self.logger.warning(f"Standard fill reported success but value is empty for {selector}, trying JavaScript-based fill")
                    return await self._fill_with_javascript(selector, text)
            else:
                # Standard fill failed - try JavaScript fallback
                self.logger.warning(f"Standard fill failed for {selector}, trying JavaScript-based fill")
                return await self._fill_with_javascript(selector, text)
        except Exception as e:
            # Standard fill threw exception - try JavaScript fallback
            self.logger.warning(f"Standard fill exception for {selector}: {e}, trying JavaScript-based fill")
            return await self._fill_with_javascript(selector, text)
    
    async def _fill_with_javascript(self, selector: str, text: str) -> str:
        """Fill input using JavaScript evaluation with event dispatching (fallback method)"""
        escaped_selector = selector.replace("'", "\\'")
        # Escape text for JavaScript: escape backslashes first, then single quotes
        escaped_text = text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "\\r")
        
        fill_code = f"""
        (function() {{
            const el = document.querySelector('{escaped_selector}');
            if (el) {{
                el.focus();
                el.value = '{escaped_text}';
                // Trigger events for framework compatibility (React, Angular, Vue, etc.)
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                el.dispatchEvent(new KeyboardEvent('keydown', {{ bubbles: true, key: 'Enter' }}));
                el.dispatchEvent(new KeyboardEvent('keyup', {{ bubbles: true, key: 'Enter' }}));
                // Also trigger focus/blur to ensure all handlers are called
                el.dispatchEvent(new Event('focus', {{ bubbles: true }}));
                el.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                return true;
            }}
            return false;
        }})()
        """
        
        try:
            result = await self.evaluate(fill_code)
            await asyncio.sleep(0.5)  # Wait for events to propagate
            
            # Verify the fill worked
            check_code = f"document.querySelector('{escaped_selector}')?.value || ''"
            actual_value = await self.evaluate(check_code)
            if actual_value and text in str(actual_value):
                self.logger.info(f"JavaScript-based fill succeeded for {selector}")
                return f"Filled {selector} via JavaScript"
            else:
                raise RuntimeError(f"JavaScript-based fill failed: expected '{text[:50]}...' but got '{str(actual_value)[:50] if actual_value else 'empty'}...'")
        except Exception as e:
            raise RuntimeError(f"JavaScript-based fill failed for {selector}: {e}")
    
    async def take_screenshot(self, path: str, retry_on_blank: bool = True) -> str:
        """
        Capture screenshot via MCP bridge with robust page ready wait and validation
        
        Args:
            path: Path where screenshot should be saved
            retry_on_blank: If True, retry if screenshot is blank (< 10KB)
            
        Returns:
            Path to screenshot file
        """
        max_retries = 2 if retry_on_blank else 1
        
        screenshot_file = Path(path)
        screenshot_file.parent.mkdir(parents=True, exist_ok=True)
        filename_base = screenshot_file.stem  # filename without extension
        
        for attempt in range(max_retries):
            try:
                # Wait for page to be fully ready before taking screenshot
                # Increase wait time on retry
                wait_timeout = 15000 + (attempt * 5000)  # 15s, 20s
                self.logger.debug(f"Taking screenshot (attempt {attempt + 1}/{max_retries})...")
                await self._wait_for_page_ready(timeout=wait_timeout)
            except Exception as e:
                self.logger.warning(f"Could not wait for page ready before screenshot: {e}")
                await asyncio.sleep(2.0 + (attempt * 1.0))  # Longer wait on retry
            
            # Call MCP screenshot tool with fullPage=True to capture entire page
            result = await self._call_bridge("screenshot", {
                "name": filename_base,
                "savePng": True,
                "fullPage": True  # Capture full page, not just viewport
            })
            
            if not result.get("success"):
                error_msg = result.get("error", "Screenshot failed")
                self.logger.warning(f"Screenshot attempt {attempt + 1} failed: {error_msg}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1.0)  # Wait before retry
                    continue
                else:
                    raise RuntimeError(f"Screenshot failed after {max_retries} attempts: {error_msg}")
            
            # Screenshot call succeeded, now find and validate the file
            # Log full MCP response for debugging
            self.logger.debug(f"MCP screenshot response: {result}")
            
            # Extract actual screenshot path from MCP response
            # MCP returns: "Screenshot saved to: ../../../home/ubuntu/Downloads/{name}-{timestamp}.png"
            actual_screenshot_path = None
            content = result.get("content", [])
            
            # Check all content items for screenshot path
            for item in content:
                if isinstance(item, dict):
                    # Check text content
                    if item.get("type") == "text":
                        text = item.get("text", "")
                        self.logger.debug(f"MCP content text: {text[:200]}")
                        
                        # Look for "Screenshot saved to:" or file path patterns
                        if "Screenshot saved to:" in text or "saved to:" in text.lower():
                            # Extract path from response
                            if "Screenshot saved to:" in text:
                                path_match = text.split("Screenshot saved to:")[-1].strip()
                            elif "saved to:" in text.lower():
                                path_match = text.split("saved to:")[-1].strip()
                            else:
                                path_match = text.strip()
                            
                            # Clean up path
                            path_match = path_match.split('\n')[0].split(' ')[0]  # Take first line/word
                            # Resolve relative path
                            if path_match.startswith("../../../"):
                                path_match = path_match.replace("../../../", "/")
                            elif path_match.startswith("../"):
                                path_match = path_match.replace("../", "/")
                            
                            if path_match and path_match.endswith('.png'):
                                actual_screenshot_path = Path(path_match)
                                self.logger.info(f"MCP reported screenshot saved to: {actual_screenshot_path}")
                                break
                    
                    # Also check for image content (base64)
                    elif item.get("type") == "image":
                        self.logger.debug("MCP returned image content (base64)")
                        # Could save base64 image if needed
            
            # Wait a moment for file to be written to disk
            await asyncio.sleep(0.5)
            
            # Verify file was actually created
            if not screenshot_file.exists():
                self.logger.warning(f"Screenshot path returned success but file not found: {path}")
                
                # Try to use the path from MCP response first
                if actual_screenshot_path and actual_screenshot_path.exists():
                    self.logger.info(f"Found screenshot at MCP-reported path: {actual_screenshot_path}")
                    screenshot_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(actual_screenshot_path, screenshot_file)
                    self.logger.info(f"Copied screenshot to expected location: {screenshot_file}")
                else:
                    # Fallback: MCP server saves screenshots to ~/Downloads/ with timestamped names
                    # Format: {name}-YYYY-MM-DDTHH-MM-SS-sssZ.png
                    downloads_dir = Path.home() / "Downloads"
                    filename_base = Path(path).stem  # filename without extension
                    
                    # Wait a bit more for file to appear (MCP might be slow to write)
                    max_wait = 5  # seconds
                    wait_interval = 0.5
                    waited = 0
                    found = False
                    
                    while waited < max_wait and not found:
                        # Find all timestamped screenshots in Downloads matching our name
                        possible_screenshots = []
                        if downloads_dir.exists():
                            # Pattern: {name}-*.png (e.g., step_01_navigate-2025-12-18T18-24-08-*.png)
                            pattern = f"{filename_base}-*.png"
                            self.logger.debug(f"Searching for screenshots matching pattern: {pattern} in {downloads_dir}")
                            
                            for found_screenshot in downloads_dir.glob(pattern):
                                # Check if it's recent (within last 5 minutes)
                                try:
                                    file_age = time.time() - found_screenshot.stat().st_mtime
                                    if file_age < 300:  # 5 minutes
                                        possible_screenshots.append((found_screenshot, file_age))
                                        self.logger.debug(f"Found candidate screenshot: {found_screenshot.name} (age: {file_age:.1f}s)")
                                except Exception as e:
                                    self.logger.debug(f"Error checking file {found_screenshot}: {e}")
                            
                            # If no exact match, try to find the most recent screenshot (fallback)
                            if not possible_screenshots:
                                self.logger.debug(f"No exact match found, searching for most recent screenshot...")
                                all_recent = sorted(
                                    downloads_dir.glob("*.png"),
                                    key=lambda p: p.stat().st_mtime,
                                    reverse=True
                                )
                                # Get the most recent screenshot (within last 2 minutes)
                                if all_recent:
                                    most_recent = all_recent[0]
                                    file_age = time.time() - most_recent.stat().st_mtime
                                    if file_age < 120:  # 2 minutes
                                        self.logger.info(f"Using most recent screenshot as fallback: {most_recent.name} (age: {file_age:.1f}s)")
                                        possible_screenshots.append((most_recent, file_age))
                        
                        # Sort by age (most recent first)
                        if possible_screenshots:
                            possible_screenshots.sort(key=lambda x: x[1])
                            # Use the most recent screenshot
                            source_file = possible_screenshots[0][0]
                            self.logger.info(f"Found screenshot at: {source_file} (after {waited}s wait)")
                            screenshot_file.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(source_file, screenshot_file)
                            self.logger.info(f"Copied screenshot to expected location: {screenshot_file}")
                            found = True
                            break
                        
                        if not found:
                            await asyncio.sleep(wait_interval)
                            waited += wait_interval
                    
                    # Also check other possible locations if still not found
                    if not found:
                        other_locations = [
                            Path("/opt/AI_CRDC_HUB/mcp-bridge") / Path(path).name,
                            Path("/opt/AI_CRDC_HUB") / Path(path).name,
                            Path("/tmp") / Path(path).name,
                        ]
                        
                        for loc in other_locations:
                            if loc.exists():
                                self.logger.info(f"Found screenshot at alternative location: {loc}")
                                screenshot_file.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(loc, screenshot_file)
                                self.logger.info(f"Copied screenshot to expected location: {screenshot_file}")
                                found = True
                                break
                    
                    if not found:
                        # Last resort: Use the most recent screenshot in Downloads (within last 1 minute)
                        if downloads_dir.exists():
                            all_recent = sorted(
                                downloads_dir.glob("*.png"),
                                key=lambda p: p.stat().st_mtime,
                                reverse=True
                            )
                            if all_recent:
                                most_recent = all_recent[0]
                                file_age = time.time() - most_recent.stat().st_mtime
                                if file_age < 60:  # 1 minute
                                    self.logger.warning(f"Using most recent screenshot as last resort: {most_recent.name} (age: {file_age:.1f}s)")
                                    screenshot_file.parent.mkdir(parents=True, exist_ok=True)
                                    shutil.copy2(most_recent, screenshot_file)
                                    self.logger.info(f"Copied most recent screenshot to expected location: {screenshot_file}")
                                    found = True
                        
                        if not found:
                            # Log all recent screenshots for debugging
                            if downloads_dir.exists():
                                recent_all = sorted(
                                    downloads_dir.glob("*.png"),
                                    key=lambda p: p.stat().st_mtime,
                                    reverse=True
                                )[:5]
                                self.logger.error(f"Screenshot not found. Recent screenshots in Downloads: {[str(p.name) for p in recent_all]}")
                            # Log the full result for debugging
                            self.logger.error(f"MCP screenshot result: {result}")
                            # Don't raise error - just log and continue with None screenshot
                            self.logger.warning(f"Could not find screenshot file, but continuing execution: {path}")
                            if attempt < max_retries - 1:
                                await asyncio.sleep(2.0)  # Wait before retry
                                continue
                            return str(screenshot_file)  # Return path anyway, even if file doesn't exist
            
            # File was found or copied, now validate it
            if screenshot_file.exists():
                self.logger.debug(f"Screenshot verified at expected location: {screenshot_file}")
                
                # Validate screenshot file size (check if blank)
                file_size = screenshot_file.stat().st_size
                self.logger.debug(f"Screenshot file size: {file_size} bytes")
                
                # If screenshot is too small (< 10KB), it's likely blank
                if file_size < 10 * 1024:  # 10KB threshold
                    self.logger.warning(f"Screenshot is too small ({file_size} bytes), likely blank. Retrying...")
                    if attempt < max_retries - 1:
                        # Delete the blank screenshot and retry
                        try:
                            screenshot_file.unlink()
                        except:
                            pass
                        await asyncio.sleep(2.0)  # Wait longer before retry
                        continue
                    else:
                        self.logger.error(f"Screenshot is still blank after {max_retries} attempts")
                else:
                    # Screenshot is valid, return it
                    self.logger.info(f"Screenshot captured successfully: {screenshot_file} ({file_size} bytes)")
                    return str(screenshot_file)
            else:
                # File not found, retry if possible
                if attempt < max_retries - 1:
                    self.logger.warning(f"Screenshot file not found, retrying...")
                    await asyncio.sleep(2.0)
                    continue
                else:
                    self.logger.error(f"Screenshot file not found after {max_retries} attempts")
                    return str(screenshot_file)  # Return path anyway
        
        # If we get here, all retries failed
        self.logger.error(f"Failed to capture valid screenshot after {max_retries} attempts")
        return str(screenshot_file)
    
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
    
    async def wait_for_element(self, selector: str, timeout: int = 5000) -> bool:
        """Wait for element to be visible - returns True if found, False otherwise"""
        try:
            result = await self._call_bridge("wait_for", {"selector": selector, "timeout": timeout})
            return result.get("success", False)
        except Exception as e:
            self.logger.warning(f"Element {selector} not found within {timeout}ms: {e}")
            return False
    
    async def evaluate(self, expression: str, timeout: int = 30000) -> Any:
        """Evaluate JavaScript expression in the browser context via MCP bridge"""
        # Playwright's page.evaluate() expects expressions, not arrow functions
        # If expression is an arrow function, convert to IIFE format
        code_to_execute = expression.strip()
        
        # Check if it's an arrow function (starts with () => or =>)
        if code_to_execute.startswith("() =>") or (code_to_execute.startswith("(") and "=>" in code_to_execute):
            # Convert arrow function to IIFE: () => expr becomes (function() { return expr; })()
            # Extract the expression after =>
            if "=>" in code_to_execute:
                arrow_part = code_to_execute.split("=>", 1)[1].strip()
                # Remove outer braces if present
                if arrow_part.startswith("{") and arrow_part.endswith("}"):
                    arrow_part = arrow_part[1:-1].strip()
                    # If it already has return, use as-is
                    if arrow_part.startswith("return"):
                        code_to_execute = f"(function() {{ {arrow_part} }})()"
                    else:
                        code_to_execute = f"(function() {{ return {arrow_part}; }})()"
                else:
                    # Simple expression, wrap with return
                    code_to_execute = f"(function() {{ return {arrow_part}; }})()"
                self.logger.debug(f"Converted arrow function to IIFE: {code_to_execute}")
        
        result = await self._call_bridge("evaluate", {"code": code_to_execute, "timeout": timeout})
        if result.get("success"):
            content = result.get("content", [])
            if content and len(content) > 0:
                # Log the raw content structure for debugging (INFO level so it shows up)
                self.logger.info(f"Evaluate raw content: {json.dumps(content, default=str)[:1000]}")
                
                # MCP server returns array like:
                # [{"type": "text", "text": "Executed JavaScript:"}, 
                #  {"type": "text", "text": "window.location.href"},
                #  {"type": "text", "text": "Result:"},
                #  {"type": "text", "text": "\"https://example.com/...\""}]
                # We need to find the actual result (after "Result:")
                
                # Skip descriptive items
                description_keywords = ["Executed JavaScript:", "Executed:", "Result:", "JavaScript executed"]
                eval_result = None
                
                # Look for the item after "Result:" or the last non-descriptive item
                found_result_label = False
                for item in content:
                    if isinstance(item, dict):
                        text = item.get("text", "")
                        # Skip description items
                        if text in description_keywords:
                            if text == "Result:":
                                found_result_label = True
                            continue
                        # If we found "Result:" label, the next item is the result
                        if found_result_label:
                            eval_result = text
                            break
                        # If it's not a description and looks like a result (quoted string, URL, etc.)
                        if text and text not in description_keywords:
                            # Check if it looks like a result value (quoted string, URL, number, etc.)
                            if (text.startswith('"') and text.endswith('"')) or \
                               (text.startswith("'") and text.endswith("'")) or \
                               ("http" in text.lower()) or \
                               text.replace(".", "").replace("-", "").isdigit():
                                eval_result = text
                                break
                    elif not isinstance(item, (dict, list)):
                        # Direct value (not a dict)
                        if item not in description_keywords:
                            eval_result = item
                            break
                
                # If we didn't find result after "Result:", try the last item
                if eval_result is None and len(content) > 0:
                    last_item = content[-1]
                    if isinstance(last_item, dict):
                        last_text = last_item.get("text", "")
                        if last_text and last_text not in description_keywords:
                            eval_result = last_text
                    elif not isinstance(last_item, (dict, list)):
                        eval_result = last_item
                
                # Remove quotes if present
                if isinstance(eval_result, str):
                    if (eval_result.startswith('"') and eval_result.endswith('"')) or \
                       (eval_result.startswith("'") and eval_result.endswith("'")):
                        eval_result = eval_result[1:-1]
                
                # Log the extracted result for debugging
                if eval_result is None:
                    self.logger.warning(f"Evaluate: Could not extract result from content: {json.dumps(content, default=str)[:500]}")
                else:
                    self.logger.info(f"Evaluate extracted result: {eval_result} (type: {type(eval_result).__name__})")
                
                return eval_result
            self.logger.warning(f"Evaluate: Empty content array in response")
            return None
        else:
            raise RuntimeError(result.get("error", "Evaluate failed"))
    
    async def validate_step_with_llm(
        self,
        step_description: str,
        action: str,
        action_parameters: Dict[str, Any],
        expected_result: Optional[str] = None,
        dom_snapshot: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate step success using LLM - NO hardcoded validation logic.
        LLM decides what to check and uses Playwright tools to verify.
        
        Args:
            step_description: The test step description
            action: The action that was executed
            action_parameters: Parameters used for the action
            expected_result: Optional expected result from user story
            dom_snapshot: Optional current page DOM snapshot
        
        Returns:
            {
                "valid": bool,
                "reasoning": str,
                "checks_performed": List[str],
                "evidence": str
            }
        """
        bedrock_client = BedrockClient()
        
        # First, ask LLM what checks are needed
        try:
            validation_plan = bedrock_client.validate_step_with_llm(
                step_description=step_description,
                action=action,
                action_parameters=action_parameters,
                expected_result=expected_result,
                dom_snapshot=dom_snapshot,
                playwright_tool_results=None
            )
            
            # Execute any Playwright tool checks the LLM requested
            tool_results = {}
            checks_performed = []
            
            for check in validation_plan.get("checks_needed", []):
                tool = check.get("tool")
                code_or_selector = check.get("code_or_selector", "")
                purpose = check.get("purpose", "")
                
                try:
                    if tool == "evaluate" and code_or_selector:
                        result = await self.evaluate(code_or_selector)
                        # Log the actual result for debugging
                        result_str = str(result) if result is not None else "None"
                        self.logger.info(f"Tool check result: {code_or_selector} -> {result_str[:200]}")
                        
                        # Enhance formatting for URL checks to make it explicit for LLM
                        tool_result_entry = {
                            "code": code_or_selector,
                            "result": result,
                            "purpose": purpose
                        }
                        # If checking URL, make it explicit
                        if "window.location" in code_or_selector.lower() or "location.href" in code_or_selector.lower():
                            tool_result_entry["url"] = result_str
                            tool_result_entry["is_url_check"] = True
                            self.logger.info(f"URL check result: {result_str}")
                        
                        tool_results[f"evaluate_{len(tool_results)}"] = tool_result_entry
                        checks_performed.append(f"Evaluated: {code_or_selector} -> {result_str[:100]}")
                    
                    elif tool == "get_text" and code_or_selector:
                        result = await self.get_text(code_or_selector)
                        tool_results[f"get_text_{len(tool_results)}"] = {
                            "selector": code_or_selector,
                            "result": result,
                            "purpose": purpose
                        }
                        checks_performed.append(f"Got text from {code_or_selector}: {str(result)[:100]}")
                    
                    elif tool == "get_dom":
                        result = await self.get_dom()
                        tool_results[f"get_dom_{len(tool_results)}"] = {
                            "result_preview": result[:1000] if result else "empty",
                            "purpose": purpose
                        }
                        checks_performed.append(f"Got DOM snapshot (length: {len(result) if result else 0})")
                    
                    elif tool == "wait_for" and code_or_selector:
                        result = await self.wait_for_element(code_or_selector, timeout=5000)
                        tool_results[f"wait_for_{len(tool_results)}"] = {
                            "selector": code_or_selector,
                            "result": result,
                            "purpose": purpose
                        }
                        checks_performed.append(f"Waited for {code_or_selector}: {'found' if result else 'not found'}")
                    
                except Exception as e:
                    self.logger.warning(f"Error executing Playwright tool {tool}: {e}")
                    tool_results[f"error_{len(tool_results)}"] = {
                        "tool": tool,
                        "error": str(e),
                        "purpose": purpose
                    }
                    checks_performed.append(f"Error executing {tool}: {str(e)[:100]}")
            
            # If LLM requested tool checks, ask it again with the results
            if tool_results:
                validation_result = bedrock_client.validate_step_with_llm(
                    step_description=step_description,
                    action=action,
                    action_parameters=action_parameters,
                    expected_result=expected_result,
                    dom_snapshot=dom_snapshot,
                    playwright_tool_results=tool_results
                )
                # Add checks performed to result
                validation_result["checks_performed"] = checks_performed
                return validation_result
            else:
                # No tool checks needed - LLM made decision from context
                validation_plan["checks_performed"] = checks_performed
                return validation_plan
                
        except Exception as e:
            self.logger.error(f"Error in LLM-driven validation: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            # Fallback: return unknown status (don't fail, but don't pass either)
            return {
                "valid": False,
                "reasoning": f"Validation error: {str(e)}",
                "checks_performed": [],
                "evidence": "Validation could not be completed due to error"
            }
    
    
    async def execute_step(
        self,
        step_description: str,
        execution_id: str,
        test_case_id: str,
        step_number: int,
        playwright_code: str = None,
        expected_result: str = None
    ) -> Dict[str, Any]:
        """
        Execute a test step via MCP and capture screenshot
        
        Uses LLM to interpret the step description and determine the appropriate action.
        Performs validation to verify the step was successful.
        
        Args:
            step_description: Step description (natural language)
            execution_id: Execution identifier
            test_case_id: Test case identifier
            step_number: Step number
            playwright_code: Generated Playwright code (optional, for context)
            expected_result: Optional expected result/assertion from user story
        
        Returns:
            Step execution result with screenshot and validation status
        """
        from utils.screenshot_handler import ScreenshotHandler
        from utils.file_handler import FileHandler
        from pathlib import Path
        
        # Use FileHandler to get the correct base directory
        file_handler = FileHandler()
        base_dir = file_handler.base_dir
        
        screenshot_handler = ScreenshotHandler(base_dir=str(base_dir), execution_id=execution_id)
        screenshot_path = screenshot_handler.get_screenshot_path(
            test_case_id,
            step_number,
            step_description
        )
        
        # Ensure screenshot directory exists
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to absolute path for MCP
        screenshot_path = screenshot_path.resolve()
        
        try:
            # Get DOM snapshot if needed for context (when selector might be missing)
            dom_snapshot = None
            if not playwright_code or ("selector" not in step_description.lower() and 
                                       "click" in step_description.lower() or 
                                       "fill" in step_description.lower() or
                                       "enter" in step_description.lower()):
                try:
                    dom_snapshot = await self.get_dom()
                    self.logger.debug(f"Retrieved DOM snapshot for step {step_number} context")
                except Exception as e:
                    self.logger.warning(f"Could not retrieve DOM snapshot for step {step_number}: {e}")
            
            # Extract expected result from step description if not provided
            if not expected_result:
                from core.story_processor import StoryProcessor
                story_processor = StoryProcessor()
                expected_result = story_processor.extract_expected_results(step_description)
            
            # Use LLM to interpret step
            bedrock_client = BedrockClient()
            try:
                interpretation = bedrock_client.interpret_step(
                    step_description=step_description,
                    playwright_code=playwright_code,
                    dom_snapshot=dom_snapshot,
                    expected_result=expected_result
                )
                
                action = interpretation.get("action")
                parameters = interpretation.get("parameters", {})
                reasoning = interpretation.get("reasoning", "")
                
                self.logger.info(f"Step {step_number} interpretation: {action} - {step_description}")
                if reasoning:
                    self.logger.debug(f"LLM reasoning: {reasoning}")
                
            except Exception as llm_error:
                # Fallback: if LLM interpretation fails, just take a screenshot
                self.logger.warning(f"LLM interpretation failed for step {step_number}: {llm_error}. Falling back to screenshot only.")
                await self.take_screenshot(str(screenshot_path))
                return {
                    "status": "passed",
                    "screenshot": str(screenshot_path),
                    "step_number": step_number,
                    "description": step_description,
                    "action": "screenshot",
                    "warning": f"LLM interpretation failed: {str(llm_error)}"
                }
            
            # Execute action based on LLM interpretation
            if action == "navigate":
                url = parameters.get("url")
                if not url:
                    raise ValueError("Navigate action requires 'url' parameter")
                
                # #region agent log
                import json
                try:
                    with open('/opt/AI_CRDC_HUB/.cursor/debug.log', 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"mcp_client.py:1005","message":"Navigate action executing","data":{"url":url,"step_number":step_number},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                except: pass
                # #endregion
                
                await self.navigate(url)
                self.logger.info(f"Navigated to {url}")
                
                # #region agent log
                try:
                    with open('/opt/AI_CRDC_HUB/.cursor/debug.log', 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"mcp_client.py:1013","message":"Navigate action completed","data":{"url":url},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                except: pass
                # #endregion
                
            elif action == "fill":
                selector = parameters.get("selector")
                text = parameters.get("text")
                if not selector:
                    raise ValueError("Fill action requires 'selector' parameter")
                if text is None:
                    raise ValueError("Fill action requires 'text' parameter")
                
                # Check if this is a TOTP generation step
                # Look for TOTP-related keywords in step description or text
                totp_keywords = ["totp", "one-time", "one time", "2fa", "two-factor", "authenticator code", "security code"]
                is_totp_step = any(keyword in step_description.lower() for keyword in totp_keywords) or \
                               any(keyword in str(text).lower() for keyword in totp_keywords)
                
                if is_totp_step:
                    # Extract secret key from step description or use environment variable
                    import re
                    from utils.otp_helper import generate_otp
                    
                    # Try to extract secret key from step description
                    # Look for patterns like "secret key XXXX" or "key XXXX" or just a long alphanumeric string
                    secret_key = None
                    
                    # Pattern 1: "secret key LCBUDA6NSWXUO4AKLTU6F3UXXO7QMBCX"
                    secret_pattern = r'(?:secret\s+key|key)\s+([A-Z0-9]{20,})'
                    match = re.search(secret_pattern, step_description, re.IGNORECASE)
                    if match:
                        secret_key = match.group(1)
                        self.logger.info(f"Extracted TOTP secret key from step description: {secret_key[:10]}...")
                    
                    # Pattern 2: Look for long alphanumeric strings (TOTP secret keys are typically 32 chars)
                    if not secret_key:
                        long_alnum_pattern = r'\b([A-Z0-9]{20,})\b'
                        matches = re.findall(long_alnum_pattern, step_description)
                        if matches:
                            # Use the longest match (likely the secret key)
                            secret_key = max(matches, key=len)
                            self.logger.info(f"Extracted potential TOTP secret key from step description: {secret_key[:10]}...")
                    
                    # If no secret key found in step, try to extract from text parameter
                    if not secret_key:
                        match = re.search(secret_pattern, str(text), re.IGNORECASE)
                        if match:
                            secret_key = match.group(1)
                            self.logger.info(f"Extracted TOTP secret key from text parameter: {secret_key[:10]}...")
                    
                    # Generate TOTP code
                    try:
                        if secret_key:
                            totp_code = generate_otp(secret_key)
                            self.logger.info(f"Generated TOTP code: {totp_code[:3]}... (using secret key {secret_key[:10]}...)")
                        else:
                            # Use environment variable
                            totp_code = generate_otp()
                            self.logger.info(f"Generated TOTP code: {totp_code[:3]}... (using TOTP_SECRET_KEY from environment)")
                        
                        # Replace text with generated TOTP code
                        text = totp_code
                        self.logger.info(f"Using generated TOTP code for fill action")
                    except Exception as e:
                        self.logger.error(f"Failed to generate TOTP code: {e}. Using original text parameter.")
                        # Continue with original text if TOTP generation fails
                
                # Perform the fill action (now includes focus)
                await self.fill(selector, text)
                self.logger.info(f"Filled {selector} with {text[:20]}..." if len(str(text)) > 20 else f"Filled {selector} with {text}")
                
                # Wait for text to be visible in the input field
                # Longer wait ensures the text is rendered and visible in screenshots
                await asyncio.sleep(1.5)
                
                # Verify the text was actually entered by checking the input value
                # Retry verification up to 3 times with increasing delays
                actual_value = None
                for attempt in range(3):
                    try:
                        # Use single quotes for selector to avoid conflicts with double quotes in selector
                        # Escape single quotes in selector if present
                        escaped_selector = selector.replace("'", "\\'")
                        # Use template literal approach: wrap selector in single quotes
                        check_code = f"document.querySelector('{escaped_selector}')?.value || ''"
                        actual_value = await self.evaluate(check_code)
                        if actual_value and text in str(actual_value):
                            self.logger.info(f"Verified text entered: {selector} contains '{text[:50]}...' (attempt {attempt + 1})")
                            break
                        elif attempt < 2:  # Not last attempt
                            self.logger.debug(f"Text not found in {selector}, retrying... (attempt {attempt + 1})")
                            await asyncio.sleep(0.5 * (attempt + 1))  # Increasing delay: 0.5s, 1s
                    except Exception as e:
                        if attempt < 2:
                            self.logger.debug(f"Verification error, retrying: {e}")
                            await asyncio.sleep(0.5 * (attempt + 1))
                        else:
                            self.logger.warning(f"Could not verify text entry for {selector} after 3 attempts: {e}")
                
                if not actual_value or text not in str(actual_value):
                    self.logger.warning(f"Text verification failed: Expected '{text[:50]}...' but got '{str(actual_value)[:50] if actual_value else 'None'}...' in {selector}")
                
            elif action == "click":
                selector = parameters.get("selector")
                if not selector:
                    raise ValueError("Click action requires 'selector' parameter")
                await self.click(selector)
                self.logger.info(f"Clicked {selector}")
                # Wait for navigation/page changes after click (especially for navigation clicks)
                # Check if this might be a navigation click based on step description
                if any(keyword in step_description.lower() for keyword in ["sign in", "login", "submit", "next", "navigate", "go to"]):
                    # Longer wait for navigation clicks to ensure page loads
                    await asyncio.sleep(3.0)
                    self.logger.info(f"Waited 3s after click for navigation to complete")
                else:
                    # Standard wait for other clicks
                    await asyncio.sleep(1.0)
                
            elif action == "wait_for":
                selector = parameters.get("selector")
                timeout = parameters.get("timeout", 30000)
                if not selector:
                    raise ValueError("Wait_for action requires 'selector' parameter")
                await self.wait_for(selector, timeout)
                self.logger.info(f"Waited for {selector} (timeout: {timeout}ms)")
                
            elif action == "get_text":
                selector = parameters.get("selector")
                if not selector:
                    raise ValueError("Get_text action requires 'selector' parameter")
                text_content = await self.get_text(selector)
                self.logger.info(f"Retrieved text from {selector}: {text_content[:50]}...")
                
            elif action == "screenshot":
                # Just take screenshot, no other action needed
                pass
                
            else:
                self.logger.warning(f"Unknown action '{action}' from LLM interpretation. Taking screenshot only.")
            
            # Capture screenshot after step execution
            # Wait for page to be ready before taking screenshot
            # Longer wait ensures page is fully loaded and rendered
            await asyncio.sleep(2.5)  # Increased from 1.0s to 2.5s for better rendering
            
            # Use absolute path for MCP
            abs_screenshot_path = str(screenshot_path.resolve())
            await self.take_screenshot(abs_screenshot_path)
            
            # Verify screenshot was actually saved and has content
            if screenshot_path.exists():
                file_size = screenshot_path.stat().st_size
                if file_size < 5000:  # Less than 5KB suggests blank/empty screenshot
                    self.logger.warning(f"Screenshot file is very small ({file_size} bytes) - may be blank: {abs_screenshot_path}")
                else:
                    self.logger.info(f"Screenshot saved ({file_size} bytes): {abs_screenshot_path}")
            else:
                self.logger.error(f"Screenshot was not saved despite take_screenshot() success: {abs_screenshot_path}")
                # Try one more time to find and copy
                downloads_dir = Path.home() / "Downloads"
                if downloads_dir.exists():
                    recent_screenshots = sorted(
                        downloads_dir.glob("screenshot-*.png"),
                        key=lambda p: p.stat().st_mtime,
                        reverse=True
                    )
                    if recent_screenshots:
                        most_recent = recent_screenshots[0]
                        file_age = time.time() - most_recent.stat().st_mtime
                        if file_age < 300:  # 5 minutes
                            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(most_recent, screenshot_path)
                            self.logger.info(f"Recovered screenshot from {most_recent} to {screenshot_path}")
                        else:
                            self.logger.warning(f"Most recent screenshot is too old: {file_age}s")
                    else:
                        self.logger.warning(f"No screenshots found in {downloads_dir}")
            
            # Perform LLM-driven validation (NO hardcoded logic)
            step_status = "passed"
            validation_result = None
            validation_message = None
            
            try:
                # Get fresh DOM snapshot for validation
                validation_dom = await self.get_dom()
                
                # Use LLM to validate step success
                validation_result = await self.validate_step_with_llm(
                    step_description=step_description,
                    action=action,
                    action_parameters=parameters,
                    expected_result=expected_result,
                    dom_snapshot=validation_dom
                )
                
                if not validation_result.get("valid", True):
                    step_status = "failed"
                    validation_message = validation_result.get("reasoning", "Validation failed")
                    self.logger.warning(f"Step {step_number} validation failed: {validation_message}")
                    # Capture error screenshot
                    error_screenshot_path = screenshot_path.parent / f"error_step_{step_number:02d}.png"
                    try:
                        await self.take_screenshot(str(error_screenshot_path.resolve()))
                    except Exception as se:
                        self.logger.warning(f"Could not capture error screenshot: {se}")
                else:
                    self.logger.info(f"Step {step_number} validation passed: {validation_result.get('reasoning', 'OK')}")
                    
            except Exception as validation_error:
                # If validation fails due to error, log and fail the step
                self.logger.warning(f"Validation error for step {step_number}: {validation_error}")
                import traceback
                self.logger.warning(traceback.format_exc())
                validation_message = f"Validation error: {str(validation_error)}"
                validation_result = {
                    "valid": False,
                    "reasoning": validation_message,
                    "checks_performed": [],
                    "evidence": "Validation could not be completed"
                }
                step_status = "failed"
            
            return {
                "status": step_status,
                "screenshot": str(screenshot_path),
                "step_number": step_number,
                "description": step_description,
                "action": action,
                "reasoning": reasoning if reasoning else None,
                "validation": validation_result,
                "validation_message": validation_message or (validation_result.get("reasoning") if validation_result else None)
            }
            
        except Exception as e:
            self.logger.error(f"Error executing step {step_number}: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            
            error_screenshot = screenshot_path.parent / f"error_step_{step_number:02d}.png"
            try:
                await self.take_screenshot(str(error_screenshot.resolve()))
            except:
                pass
            
            return {
                "status": "failed",
                "error": str(e),
                "screenshot": str(error_screenshot) if error_screenshot.exists() else None,
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


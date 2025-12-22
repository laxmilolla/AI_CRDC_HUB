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
import aiohttp
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
    
    async def fill(self, selector: str, text: str, is_totp: bool = False) -> str:
        """
        Fill input via MCP bridge with multiple fallback strategies:
        1. Standard Playwright fill
        2. Enhanced JavaScript fill with comprehensive event dispatching
        3. Character-by-character typing
        4. Playwright type() method
        
        Args:
            selector: Element selector
            text: Text to fill
            is_totp: If True, use character-by-character typing directly (more realistic for TOTP)
        """
        # Wait for element to be ready before attempting fill
        try:
            await self.wait_for_element(selector, timeout=10000)
        except Exception as e:
            self.logger.warning(f"Element {selector} not ready, proceeding anyway: {e}")
        
        # Escape selector for JavaScript
        escaped_selector = selector.replace("'", "\\'")
        
        # For TOTP fields, use Playwright type() FIRST (fastest and most reliable)
        # Then fallback to JavaScript methods if needed
        if is_totp:
            self.logger.info(f"[FILL] TOTP field detected, trying Playwright type() first for {selector} (fastest method)")
            self.logger.info(f"[FILL] TOTP code to enter: '{text}' (length: {len(str(text))})")
            
            # DIAGNOSTIC: Check field state and properties BEFORE any action
            escaped_selector = selector.replace("'", "\\'")
            diag_code = f"""
            (function() {{
                const el = document.querySelector('{escaped_selector}');
                if (!el) return {{ found: false }};
                return {{
                    found: true,
                    value: el.value || '',
                    disabled: el.disabled,
                    readOnly: el.readOnly,
                    type: el.type,
                    className: el.className,
                    id: el.id,
                    name: el.name
                }};
            }})()
            """
            field_state = await self.evaluate(diag_code)
            self.logger.info(f"[FILL] Field state BEFORE fill: {field_state}")
            
            try:
                result = await self.type(selector, text, is_totp=True)
                self.logger.info(f"[FILL] Playwright type() succeeded for TOTP field {selector}")
                
                # CRITICAL: Double-check that value was actually entered (defense in depth)
                await asyncio.sleep(0.1)  # Reduced from 0.2s for speed
                check_code = f"document.querySelector('{escaped_selector}')?.value || ''"
                final_check = await self.evaluate(check_code)
                self.logger.info(f"[FILL] Final TOTP verification after type(): '{final_check}' (length: {len(str(final_check)) if final_check else 0})")
                
                if not final_check or len(str(final_check).strip()) != 6 or not str(final_check).strip().isdigit():
                    self.logger.error(f"[FILL] CRITICAL: Playwright type() reported success but field is empty or invalid! Value: '{final_check}'. Trying JavaScript fallback.")
                    # Force fallback to JavaScript methods
                    raise RuntimeError(f"Type() verification failed: field value is '{final_check}'")
                
                return result
            except Exception as e:
                self.logger.warning(f"[FILL] Playwright type() failed for TOTP field {selector}: {e}, trying JavaScript fallback")
                # Fallback to JavaScript methods - use faster typing for TOTP
                return await self._fill_with_typing(selector, text, is_totp=True)
        
        # First, focus and clear the input element to ensure it's ready
        try:
            # Focus the element
            focus_code = f"document.querySelector('{escaped_selector}')?.focus()"
            await self.evaluate(focus_code)
            await asyncio.sleep(0.3)  # Brief wait after focus
            
            # Clear the field (select all and delete, or set value to empty)
            clear_code = f"(function() {{ const el = document.querySelector('{escaped_selector}'); if (el) {{ el.select(); el.value = ''; }} }})()"
            await self.evaluate(clear_code)
            await asyncio.sleep(0.3)  # Brief wait after clear
        except Exception as e:
            self.logger.warning(f"Could not focus/clear {selector} before fill: {e}")
        
        # Strategy 1: Try standard fill method
        try:
            result = await self._call_bridge("fill", {"selector": selector, "text": text})
            if result.get("success"):
                # Wait for the fill to complete and UI to update
                await asyncio.sleep(1.0)  # Wait time for complex input fields
                
                # Verify the fill worked
                check_code = f"document.querySelector('{escaped_selector}')?.value || ''"
                actual_value = await self.evaluate(check_code)
                if actual_value and text in str(actual_value):
                    self.logger.info(f"Standard fill succeeded for {selector}")
                    return f"Filled {selector}"
                else:
                    # Standard fill reported success but value is empty - try enhanced JavaScript fill
                    self.logger.warning(f"Standard fill reported success but value is empty for {selector}, trying enhanced JavaScript fill")
                    return await self._fill_with_enhanced_javascript(selector, text)
            else:
                # Standard fill failed - try enhanced JavaScript fill
                self.logger.warning(f"Standard fill failed for {selector}, trying enhanced JavaScript fill")
                return await self._fill_with_enhanced_javascript(selector, text)
        except Exception as e:
            # Standard fill threw exception - try enhanced JavaScript fill
            self.logger.warning(f"Standard fill exception for {selector}: {e}, trying enhanced JavaScript fill")
            return await self._fill_with_enhanced_javascript(selector, text)
    
    async def _fill_with_enhanced_javascript(self, selector: str, text: str) -> str:
        """
        Enhanced JavaScript fill with comprehensive event dispatching and Object.defineProperty bypass
        Uses JSON.stringify for safe text escaping to handle all special characters correctly
        """
        escaped_selector = selector.replace("'", "\\'")
        # Use JSON.stringify to properly escape the text for JavaScript (handles all special characters safely)
        escaped_text_js = json.dumps(text)  # This produces a JSON string that's safe to use in JavaScript
        
        # Enhanced fill with comprehensive event dispatching
        # Use the JSON-escaped text variable in JavaScript
        fill_code = f"""
        (function() {{
            const el = document.querySelector('{escaped_selector}');
            if (!el) return false;
            
            // Parse the JSON-escaped text to get the actual text value
            const text = {escaped_text_js};
            
            // Focus first
            el.focus();
            
            // Try to bypass value setter restrictions using Object.defineProperty
            try {{
                const nativeValue = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el), 'value');
                if (nativeValue && nativeValue.set) {{
                    nativeValue.set.call(el, text);
                }} else {{
                    el.value = text;
                }}
            }} catch (e) {{
                el.value = text;
            }}
            
            // Trigger comprehensive event sequence for framework compatibility
            // 1. Focus events
            el.dispatchEvent(new Event('focus', {{ bubbles: true, cancelable: true }}));
            
            // 2. Before input (for modern frameworks)
            el.dispatchEvent(new Event('beforeinput', {{ bubbles: true, cancelable: true }}));
            
            // 3. Composition events (for input methods) - use Event if CompositionEvent not available
            try {{
                el.dispatchEvent(new CompositionEvent('compositionstart', {{ bubbles: true }}));
                el.dispatchEvent(new CompositionEvent('compositionupdate', {{ bubbles: true, data: text }}));
                el.dispatchEvent(new CompositionEvent('compositionend', {{ bubbles: true, data: text }}));
            }} catch (e) {{
                // CompositionEvent not available, skip
            }}
            
            // 4. Input event (most important for React/Vue/Angular)
            try {{
                el.dispatchEvent(new InputEvent('input', {{
                    bubbles: true,
                    cancelable: true,
                    inputType: 'insertText',
                    data: text
                }}));
            }} catch (e) {{
                // InputEvent not available, use regular Event
                el.dispatchEvent(new Event('input', {{ bubbles: true, cancelable: true }}));
            }}
            
            // 5. Key events (simulate typing)
            for (let i = 0; i < text.length; i++) {{
                const char = text[i];
                el.dispatchEvent(new KeyboardEvent('keydown', {{ bubbles: true, key: char, code: `Key${{char.toUpperCase()}}` }}));
                el.dispatchEvent(new KeyboardEvent('keypress', {{ bubbles: true, key: char, charCode: char.charCodeAt(0) }}));
                el.dispatchEvent(new KeyboardEvent('keyup', {{ bubbles: true, key: char, code: `Key${{char.toUpperCase()}}` }}));
            }}
            
            // 6. Change event
            el.dispatchEvent(new Event('change', {{ bubbles: true, cancelable: true }}));
            
            // 7. Blur event (some frameworks validate on blur)
            el.dispatchEvent(new Event('blur', {{ bubbles: true, cancelable: true }}));
            
            // 8. React-specific: trigger onChange manually if React is present
            if (el._valueTracker) {{
                el._valueTracker.setValue('');
            }}
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            nativeInputValueSetter.call(el, text);
            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
            
            return true;
        }})()
        """
        
        try:
            result = await self.evaluate(fill_code)
            self.logger.info(f"Enhanced JavaScript fill evaluate result: {result} (type: {type(result).__name__})")
            
            # Check if element was found (result should be True if successful)
            # Handle both boolean False and string "false" from evaluate
            if result is False or result == "false" or (isinstance(result, str) and result.lower() == "false"):
                self.logger.warning(f"Enhanced JavaScript fill: Element not found or returned false for {selector}")
                return await self._fill_with_typing(selector, text)
            
            await asyncio.sleep(0.8)  # Wait for events to propagate
            
            # Verify the fill worked
            check_code = f"document.querySelector('{escaped_selector}')?.value || ''"
            actual_value = await self.evaluate(check_code)
            self.logger.info(f"Enhanced JavaScript fill verification: expected '{text[:50]}...', got '{str(actual_value)[:50] if actual_value else 'empty'}...'")
            
            if actual_value and text in str(actual_value):
                self.logger.info(f"Enhanced JavaScript fill succeeded for {selector}")
                return f"Filled {selector} via enhanced JavaScript"
            else:
                # Try character-by-character typing
                self.logger.warning(f"Enhanced JavaScript fill verification failed for {selector}: expected '{text[:50]}...', got '{str(actual_value)[:50] if actual_value else 'empty'}...'. Trying character-by-character typing")
                return await self._fill_with_typing(selector, text)
        except Exception as e:
            self.logger.warning(f"Enhanced JavaScript fill exception for {selector}: {e}, trying character-by-character typing")
            import traceback
            self.logger.debug(traceback.format_exc())
            return await self._fill_with_typing(selector, text)
    
    async def _fill_with_typing(self, selector: str, text: str, is_totp: bool = False) -> str:
        """
        Fill input by typing character-by-character (simulates real user typing)
        
        Args:
            selector: Element selector
            text: Text to type
            is_totp: If True, optimize for TOTP codes (faster typing, shorter delays)
        """
        escaped_selector = selector.replace("'", "\\'")
        # Use JSON.stringify to properly escape the text for JavaScript
        import json
        escaped_text = json.dumps(text)
        
        # For TOTP codes, use faster typing (10ms delay vs 20ms)
        # For regular text, use normal typing speed
        delay_ms = 10 if is_totp else 20
        
        # Type character by character with delays
        # Build code in parts to avoid f-string escaping issues
        typing_code_parts = [
            "(async function() {",
            f"const el = document.querySelector('{escaped_selector}');",
            "if (!el) return false;",
            "el.focus();",
            "el.value = '';",
            f"await new Promise(resolve => setTimeout(resolve, {50 if is_totp else 100}));",
            f"const text = {escaped_text};",
            "for (let i = 0; i < text.length; i++) {",
            "el.value += text[i];",
            "el.dispatchEvent(new Event('input', { bubbles: true }));",
            "el.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, key: text[i] }));",
            "el.dispatchEvent(new KeyboardEvent('keypress', { bubbles: true, key: text[i] }));",
            "el.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true, key: text[i] }));",
            f"await new Promise(resolve => setTimeout(resolve, {delay_ms}));",
            "}",
            "el.dispatchEvent(new Event('change', { bubbles: true }));",
            "return true;",
            "})()"
        ]
        typing_code = " ".join(typing_code_parts)
        
        try:
            result = await self.evaluate(typing_code)
            # For TOTP codes, use shorter wait to minimize expiration risk
            wait_time = 0.2 if is_totp else (0.3 if len(text) <= 8 else 1.0)
            await asyncio.sleep(wait_time)  # Wait for typing to complete
            
            # Verify the fill worked
            check_code = f"document.querySelector('{escaped_selector}')?.value || ''"
            actual_value = await self.evaluate(check_code)
            
            # For TOTP codes, be more lenient - check length and that it's numeric
            if is_totp:
                if actual_value and len(str(actual_value).strip()) == len(str(text).strip()) and str(actual_value).strip().isdigit():
                    self.logger.info(f"Character-by-character typing succeeded for TOTP field {selector}: entered {len(str(actual_value).strip())} digits")
                    return f"Filled {selector} via typing"
                elif actual_value and str(text).strip() in str(actual_value).strip():
                    self.logger.info(f"Character-by-character typing succeeded for TOTP field {selector} (lenient check)")
                    return f"Filled {selector} via typing"
                else:
                    self.logger.warning(f"Character-by-character typing failed for TOTP: expected '{text}' but got '{str(actual_value) if actual_value else 'empty'}'")
                    # Last resort: try Playwright type() method
                    return await self.type(selector, text, is_totp=True)
            else:
                if actual_value and text in str(actual_value):
                    self.logger.info(f"Character-by-character typing succeeded for {selector}")
                    return f"Filled {selector} via typing"
                else:
                    # Last resort: try Playwright type() method
                    self.logger.warning(f"Character-by-character typing failed, trying Playwright type() method")
                    return await self.type(selector, text)
        except Exception as e:
            self.logger.warning(f"Character-by-character typing exception: {e}, trying Playwright type() method")
            return await self.type(selector, text)
    
    async def type(self, selector: str, text: str, is_totp: bool = False) -> str:
        """
        Use Playwright type() method (character-by-character typing via Playwright)
        
        Args:
            selector: Element selector
            text: Text to type
            is_totp: If True, optimize for TOTP codes (faster, more lenient verification)
        """
        try:
            self.logger.info(f"[TYPE] Attempting to type into {selector} with text length={len(str(text))}, is_totp={is_totp}")
            self.logger.info(f"[TYPE] Text to enter: '{text}'")
            
            # DIAGNOSTIC: Check field state BEFORE typing
            escaped_selector = selector.replace("'", "\\'")
            before_code = f"document.querySelector('{escaped_selector}')?.value || ''"
            before_value = await self.evaluate(before_code)
            self.logger.info(f"[TYPE] Field value BEFORE typing: '{before_value}'")
            
            result = await self._call_bridge("type", {"selector": selector, "text": text})
            self.logger.info(f"[TYPE] Bridge call result: success={result.get('success')}, error={result.get('error', 'None')}")
            self.logger.info(f"[TYPE] Full bridge response: {result}")
            
            # DIAGNOSTIC: Check field state IMMEDIATELY after bridge call
            immediate_code = f"document.querySelector('{escaped_selector}')?.value || ''"
            immediate_value = await self.evaluate(immediate_code)
            self.logger.info(f"[TYPE] Field value IMMEDIATELY after bridge call: '{immediate_value}'")
            
            if result.get("success"):
                # For TOTP codes, use shorter wait to minimize expiration risk, but ensure enough time for value to be entered
                wait_time = 0.5 if is_totp else 1.0  # Increased from 0.3s to 0.5s for TOTP
                await asyncio.sleep(wait_time)
                
                # Verify the fill worked - retry verification up to 3 times for TOTP
                escaped_selector = selector.replace("'", "\\'")
                check_code = f"document.querySelector('{escaped_selector}')?.value || ''"
                
                actual_value = None
                for verify_attempt in range(3 if is_totp else 1):
                    actual_value = await self.evaluate(check_code)
                    self.logger.info(f"[TYPE] Verification attempt {verify_attempt + 1}: actual_value='{actual_value}' (length: {len(str(actual_value)) if actual_value else 0})")
                    
                    # For TOTP codes, be more lenient - check length and that it's numeric
                    if is_totp:
                        # TOTP codes are typically 6 digits
                        if actual_value and len(str(actual_value).strip()) == len(str(text).strip()) and str(actual_value).strip().isdigit():
                            self.logger.info(f"[TYPE] Playwright type() method succeeded for TOTP field {selector}: entered {len(str(actual_value).strip())} digits")
                            return f"Filled {selector} via Playwright type()"
                        elif actual_value and str(text).strip() in str(actual_value).strip():
                            # Fallback: check if the text is contained in the actual value
                            self.logger.info(f"[TYPE] Playwright type() method succeeded for TOTP field {selector} (lenient check)")
                            return f"Filled {selector} via Playwright type()"
                        elif verify_attempt < 2:  # Not last attempt
                            self.logger.warning(f"[TYPE] TOTP verification failed, retrying... (attempt {verify_attempt + 1}/3)")
                            await asyncio.sleep(0.3)  # Wait a bit more before retry
                        else:
                            # Last attempt failed - raise error
                            raise RuntimeError(f"Playwright type() failed for TOTP after 3 attempts: expected '{text}' but got '{str(actual_value) if actual_value else 'empty'}'")
                else:
                    # Standard verification for non-TOTP fields
                    if actual_value and text in str(actual_value):
                        self.logger.info(f"Playwright type() method succeeded for {selector}")
                        return f"Filled {selector} via Playwright type()"
                    else:
                        raise RuntimeError(f"Playwright type() failed: expected '{text[:50]}...' but got '{str(actual_value)[:50] if actual_value else 'empty'}...'")
            else:
                raise RuntimeError(f"Playwright type() failed: {result.get('error', 'Unknown error')}")
        except Exception as e:
            raise RuntimeError(f"Playwright type() method failed for {selector}: {e}")
    
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
        # DIAGNOSTIC: Write to file to verify new code is executing (bypasses logging/caching)
        try:
            with open('/tmp/execute_step_diagnostic.log', 'a') as f:
                import time
                f.write(f"[{time.time()}] execute_step called: step_number={step_number}, step_description={step_description[:50]}\n")
                f.flush()
        except:
            pass
        
        # Ensure logger is initialized FIRST before any logging
        if not hasattr(self, 'logger') or self.logger is None:
            from utils.logger import get_logger
            self.logger = get_logger(__name__)
        
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
        
        # DIAGNOSTIC: Write to file right before [EXECUTE_STEP] log
        try:
            with open('/tmp/execute_step_diagnostic.log', 'a') as f:
                import time
                f.write(f"[{time.time()}] About to log [EXECUTE_STEP] for step {step_number}\n")
                f.flush()
        except:
            pass
        
        self.logger.info(f"[EXECUTE_STEP] Step {step_number} starting execution: {step_description[:100]}")
        
        # DIAGNOSTIC: Write to file right after [EXECUTE_STEP] log
        try:
            with open('/tmp/execute_step_diagnostic.log', 'a') as f:
                import time
                f.write(f"[{time.time()}] After [EXECUTE_STEP] log for step {step_number}\n")
                f.flush()
        except:
            pass
        
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
            
            # Get current URL for selector registry lookup
            current_url = None
            try:
                url_result = await self.evaluate("window.location.href", timeout=5000)
                if url_result:
                    current_url = str(url_result).strip('"\'')
                    self.logger.info(f"Current URL for step {step_number}: {current_url}")
                else:
                    self.logger.warning(f"Could not get current URL for step {step_number}: url_result is None")
            except Exception as e:
                self.logger.warning(f"Could not get current URL for step {step_number}: {e}")
            
            # Use LLM to interpret step (will check registry first if URL available)
            bedrock_client = BedrockClient()
            try:
                interpretation = bedrock_client.interpret_step(
                    step_description=step_description,
                    playwright_code=playwright_code,
                    dom_snapshot=dom_snapshot,
                    expected_result=expected_result,
                    current_url=current_url
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
            self.logger.info(f"[EXECUTE_STEP] Step {step_number} Executing action: {action}, parameters keys: {list(parameters.keys()) if parameters else 'None'}")
            self.logger.info(f"[EXECUTE_STEP] Step {step_number} Full parameters: {parameters}")
            
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
                # DIAGNOSTIC: Write to file when fill action block is entered
                try:
                    with open('/tmp/execute_step_diagnostic.log', 'a') as f:
                        import time
                        f.write(f"[{time.time()}] FILL action block ENTERED for step {step_number}\n")
                        f.flush()
                except:
                    pass
                
                # Logger should already be initialized at start of execute_step
                # But ensure it's available as a safety check
                if not hasattr(self, 'logger') or self.logger is None:
                    from utils.logger import get_logger
                    self.logger = get_logger(__name__)
                
                self.logger.info(f"[FILL] Step {step_number} Fill action block ENTERED - step_description: {step_description[:100]}")
                self.logger.info(f"[FILL] Step {step_number} Parameters received: {parameters}")
                self.logger.info(f"[FILL] Step {step_number} Fill action started - step_description: {step_description[:100]}")
                
                try:
                    selector = parameters.get("selector")
                    text = parameters.get("text")
                    
                    self.logger.info(f"[FILL] Step {step_number} Extracted parameters - selector: {selector}, text type: {type(text)}, text length: {len(str(text)) if text else 0}")
                    
                    if not selector:
                        raise ValueError("Fill action requires 'selector' parameter")
                    if text is None:
                        raise ValueError("Fill action requires 'text' parameter")
                    
                    # Check if this is a TOTP generation step
                    # Look for TOTP-related keywords in step description or text
                    totp_keywords = ["totp", "one-time", "one time", "2fa", "two-factor", "authenticator code", "security code"]
                    step_has_totp = any(keyword in step_description.lower() for keyword in totp_keywords)
                    text_has_totp = any(keyword in str(text).lower() for keyword in totp_keywords)
                    is_totp_step = step_has_totp or text_has_totp
                    
                    self.logger.info(f"[TOTP] Step {step_number} TOTP detection: is_totp_step={is_totp_step}, step_desc_has_totp={step_has_totp}, text_has_totp={text_has_totp}")
                    self.logger.info(f"[TOTP] Step {step_number} step_description (first 100 chars): {step_description[:100]}")
                    self.logger.info(f"[TOTP] Step {step_number} text parameter (first 100 chars): {str(text)[:100]}")
                    
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
                            self.logger.info(f"[TOTP] Step {step_number} Extracted TOTP secret key from step description: {secret_key[:10]}... (full length: {len(secret_key)})")
                        
                        # Pattern 2: Look for long alphanumeric strings (TOTP secret keys are typically 32 chars)
                        if not secret_key:
                            long_alnum_pattern = r'\b([A-Z0-9]{20,})\b'
                            matches = re.findall(long_alnum_pattern, step_description)
                            if matches:
                                # Use the longest match (likely the secret key)
                                secret_key = max(matches, key=len)
                                self.logger.info(f"[TOTP] Step {step_number} Extracted potential TOTP secret key from step description: {secret_key[:10]}... (full length: {len(secret_key)})")
                        
                        # If no secret key found in step, try to extract from text parameter
                        if not secret_key:
                            match = re.search(secret_pattern, str(text), re.IGNORECASE)
                            if match:
                                secret_key = match.group(1)
                                self.logger.info(f"[TOTP] Step {step_number} Extracted TOTP secret key from text parameter: {secret_key[:10]}... (full length: {len(secret_key)})")
                        
                        # Generate TOTP code RIGHT BEFORE filling (to minimize expiration risk)
                        # Removed static test value - now using real TOTP generation
                        try:
                            if secret_key:
                                self.logger.info(f"[TOTP] Step {step_number} Generating TOTP code using secret key: {secret_key[:10]}...")
                                totp_code = generate_otp(secret_key)
                                self.logger.info(f"[TOTP] Step {step_number} Generated TOTP code: {totp_code} (using secret key {secret_key[:10]}..., length: {len(totp_code)})")
                            else:
                                # Use environment variable
                                self.logger.info(f"[TOTP] Step {step_number} Generating TOTP code using TOTP_SECRET_KEY from environment")
                                totp_code = generate_otp()
                                self.logger.info(f"[TOTP] Step {step_number} Generated TOTP code: {totp_code} (using TOTP_SECRET_KEY from environment, length: {len(totp_code)})")
                            
                            # Replace text with generated TOTP code
                            original_text = text
                            text = totp_code
                            self.logger.info(f"[TOTP] Step {step_number} Replaced text parameter '{original_text[:50]}...' with generated TOTP code: {totp_code}")
                        except Exception as e:
                            import traceback
                            self.logger.error(f"[TOTP] Step {step_number} Failed to generate TOTP code: {e}")
                            self.logger.error(f"[TOTP] Step {step_number} Traceback: {traceback.format_exc()}")
                            # Continue with original text if TOTP generation fails
                    
                    # Perform the fill action (pass is_totp=True for TOTP fields to use character-by-character typing)
                    self.logger.info(f"[FILL] Step {step_number} About to fill selector='{selector}' with text length={len(str(text))}, is_totp={is_totp_step}, text preview: {str(text)[:50]}...")
                    await self.fill(selector, text, is_totp=is_totp_step)
                    self.logger.info(f"[FILL] Step {step_number} Filled selector='{selector}' with text: {text[:20]}..." if len(str(text)) > 20 else f"[FILL] Step {step_number} Filled selector='{selector}' with text: {text}")
                    
                    # For TOTP fields, minimize all waits to prevent expiration
                    if is_totp_step:
                        # Minimal wait for TOTP - just enough for DOM to update
                        await asyncio.sleep(0.3)  # Increased from 0.2s to 0.3s to ensure value is set
                        
                        # Critical verification for TOTP - must verify value was entered
                        try:
                            escaped_selector = selector.replace("'", "\\'")
                            check_code = f"document.querySelector('{escaped_selector}')?.value || ''"
                            actual_value = await self.evaluate(check_code)
                            self.logger.info(f"[VERIFY] Step {step_number} TOTP verification: '{actual_value}' (length: {len(str(actual_value)) if actual_value else 0}, expected: '{text}')")
                            
                            # For TOTP, CRITICAL: must have a 6-digit code, otherwise fail the step
                            if actual_value and len(str(actual_value).strip()) == 6 and str(actual_value).strip().isdigit():
                                self.logger.info(f"[VERIFY] Step {step_number} TOTP code verified: {len(str(actual_value).strip())} digits entered")
                            else:
                                # This is a critical failure - the TOTP code was not entered
                                error_msg = f"[VERIFY] Step {step_number} TOTP verification FAILED: Expected 6 digits but got '{actual_value}' (length: {len(str(actual_value)) if actual_value else 0})"
                                self.logger.error(error_msg)
                                # Raise exception to fail the step
                                raise ValueError(f"TOTP code was not entered. Field value: '{actual_value}'")
                        except ValueError:
                            # Re-raise ValueError (our critical failure)
                            raise
                        except Exception as e:
                            # Other exceptions - log but don't fail (might be transient)
                            self.logger.warning(f"[VERIFY] Step {step_number} TOTP verification error: {e}")
                    else:
                        # Standard wait for non-TOTP fields
                        await asyncio.sleep(1.5)  # Longer wait ensures the text is rendered and visible in screenshots
                        
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
                                self.logger.info(f"[VERIFY] Step {step_number} Checking actual value in {selector}: '{actual_value}' (expected: '{text[:50]}...')")
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
                        else:
                            # Log what was actually entered for verification
                            self.logger.info(f"[VERIFY] Step {step_number} Verified actual value in {selector}: '{actual_value}' (length: {len(str(actual_value))})")
                
                except Exception as fill_error:
                    import traceback
                    self.logger.error(f"[FILL] Step {step_number} Fill action failed with error: {fill_error}")
                    self.logger.error(f"[FILL] Step {step_number} Traceback: {traceback.format_exc()}")
                    raise  # Re-raise to let caller handle it
                
            elif action == "click":
                selector = parameters.get("selector")
                if not selector:
                    raise ValueError("Click action requires 'selector' parameter")
                
                # Check if this is a TOTP submission click (clicking Submit after entering TOTP)
                is_totp_submission = any(keyword in step_description.lower() for keyword in ["submit", "complete login", "complete sign in"]) and \
                                    any(keyword in step_description.lower() for keyword in ["totp", "one-time", "2fa", "two-factor", "authenticator"])
                
                # Also check if previous step was TOTP entry (by checking if we're on TOTP page)
                try:
                    current_url = await self.evaluate("window.location.href")
                    is_on_totp_page = "two_factor" in current_url.lower() or "authenticator" in current_url.lower()
                    if is_on_totp_page and "submit" in step_description.lower():
                        is_totp_submission = True
                except:
                    pass
                
                if is_totp_submission:
                    # CRITICAL: Regenerate TOTP code RIGHT BEFORE clicking Submit to ensure it's fresh
                    # This prevents expiration issues where code was generated too early
                    self.logger.info(f"[TOTP_SUBMIT] Step {step_number} Detected TOTP submission - regenerating TOTP code before clicking Submit")
                    
                    # Extract TOTP secret key from step description or environment
                    import re
                    import os
                    from utils.otp_helper import generate_otp
                    
                    secret_key = None
                    
                    # Try to extract from step description first
                    secret_pattern = r'(?:secret\s+key|key)\s+([A-Z0-9]{20,})'
                    match = re.search(secret_pattern, step_description, re.IGNORECASE)
                    if match:
                        secret_key = match.group(1)
                        self.logger.info(f"[TOTP_SUBMIT] Step {step_number} Extracted secret key from step description: {secret_key[:10]}...")
                    
                    # If not found, try to find long alphanumeric string (TOTP secret keys are typically 32 chars)
                    if not secret_key:
                        long_alnum_pattern = r'\b([A-Z0-9]{20,})\b'
                        matches = re.findall(long_alnum_pattern, step_description)
                        if matches:
                            secret_key = max(matches, key=len)
                            self.logger.info(f"[TOTP_SUBMIT] Step {step_number} Extracted potential secret key from step description: {secret_key[:10]}...")
                    
                    # If still not found, use environment variable
                    if not secret_key:
                        secret_key = os.getenv("TOTP_SECRET_KEY")
                        if secret_key:
                            self.logger.info(f"[TOTP_SUBMIT] Step {step_number} Using TOTP_SECRET_KEY from environment")
                    
                    if secret_key:
                        try:
                            # Generate fresh TOTP code RIGHT BEFORE submission
                            fresh_totp_code = generate_otp(secret_key)
                            self.logger.info(f"[TOTP_SUBMIT] Step {step_number} Generated fresh TOTP code: {fresh_totp_code} (right before Submit click)")
                            
                            # Update the TOTP field with the fresh code
                            # CRITICAL: Check for both visible and hidden input fields
                            # login.gov may have multiple input[name='code'] fields
                            try:
                                import json
                                # Initialize default selector
                                totp_field_selector = "input[name='code']"
                                
                                # CRITICAL: Find the ACTUAL visible TOTP input field
                                # login.gov may have multiple fields - we need the visible one that the form validates
                                # Try multiple selectors to find the visible TOTP input
                                find_visible_totp_code = """(function(){const s=['input[name="code"]','input[type="text"][name*="code"]','input[type="tel"][name*="code"]','input.one-time-code','input#one-time-code','input[autocomplete="one-time-code"]'];for(const sel of s){const el=document.querySelector(sel);if(el&&el.offsetWidth>0&&el.offsetHeight>0&&el.type!=='hidden'){return{found:true,selector:sel,value:el.value||'',type:el.type,id:el.id||'',name:el.name||''};}}return{found:false};})()"""
                                
                                visible_totp_info = await self.evaluate(find_visible_totp_code)
                                if isinstance(visible_totp_info, str):
                                    try:
                                        visible_totp_info = json.loads(visible_totp_info)
                                    except:
                                        visible_totp_info = None
                                
                                if visible_totp_info and visible_totp_info.get('found'):
                                    # Found visible field - use it!
                                    if visible_totp_info.get('id'):
                                        totp_field_selector = f"input#{visible_totp_info['id']}"
                                    elif visible_totp_info.get('name'):
                                        totp_field_selector = f"input[name='{visible_totp_info['name']}']"
                                    else:
                                        totp_field_selector = visible_totp_info.get('selector', "input[name='code']")
                                    self.logger.info(f"[TOTP_SUBMIT] Step {step_number} ✅ Found VISIBLE TOTP field: {totp_field_selector} (type: {visible_totp_info.get('type')}, current value: {visible_totp_info.get('value')})")
                                else:
                                    # Fallback: find ALL input fields with name='code' and identify visible ones
                                    # Use simpler code to avoid syntax errors
                                    find_fields_code = """(function(){const f=Array.from(document.querySelectorAll('input[name="code"]'));return f.map((e,i)=>({i:i,v:e.value||'',t:e.type,vis:e.offsetWidth>0&&e.offsetHeight>0,d:window.getComputedStyle(e).display,vs:window.getComputedStyle(e).visibility,id:e.id||'',cls:e.className||''}));})()"""
                                    
                                    try:
                                        fields_info = await self.evaluate(find_fields_code)
                                        # Parse JSON if it's a string
                                        if isinstance(fields_info, str):
                                            try:
                                                fields_info = json.loads(fields_info)
                                            except:
                                                # If parsing fails, try to extract JSON from error message
                                                self.logger.warning(f"[TOTP_SUBMIT] Step {step_number} Could not parse fields_info as JSON: {fields_info[:200]}")
                                                fields_info = None
                                        
                                        if fields_info and isinstance(fields_info, list):
                                            self.logger.info(f"[TOTP_SUBMIT] Step {step_number} Found {len(fields_info)} input[name='code'] field(s)")
                                            for idx, field in enumerate(fields_info):
                                                self.logger.info(f"[TOTP_SUBMIT] Step {step_number} Field {idx}: type={field.get('t')}, visible={field.get('vis')}, value={field.get('v')}, id={field.get('id')}")
                                            
                                            # Find visible field (not hidden, has width/height)
                                            visible_field = next((f for f in fields_info if f.get('vis', False) and f.get('t') != 'hidden'), None)
                                            if visible_field:
                                                # Use visible field - try ID first, then index
                                                if visible_field.get('id'):
                                                    totp_field_selector = f"input#{visible_field['id']}[name='code']"
                                                else:
                                                    # Use :nth-of-type to target specific visible field
                                                    visible_idx = fields_info.index(visible_field)
                                                    totp_field_selector = f"input[name='code']:nth-of-type({visible_idx + 1})"
                                                self.logger.info(f"[TOTP_SUBMIT] Step {step_number} ✅ Using VISIBLE TOTP field: {totp_field_selector}")
                                            else:
                                                # No visible field found - try to find text input (not hidden)
                                                text_field = next((f for f in fields_info if f.get('t') == 'text'), None)
                                                if text_field:
                                                    if text_field.get('id'):
                                                        totp_field_selector = f"input#{text_field['id']}[name='code']"
                                                    self.logger.warning(f"[TOTP_SUBMIT] Step {step_number} No visible field, using text field: {totp_field_selector}")
                                                else:
                                                    self.logger.warning(f"[TOTP_SUBMIT] Step {step_number} ⚠️ No visible field found! All fields are hidden. Using first field.")
                                                    totp_field_selector = "input[name='code']"
                                        else:
                                            self.logger.warning(f"[TOTP_SUBMIT] Step {step_number} Could not parse field info, using default selector")
                                            totp_field_selector = "input[name='code']"
                                    except Exception as field_detect_error:
                                        self.logger.error(f"[TOTP_SUBMIT] Step {step_number} Error detecting fields: {field_detect_error}")
                                        import traceback
                                        self.logger.debug(f"[TOTP_SUBMIT] Step {step_number} Field detection traceback: {traceback.format_exc()}")
                                        # Fallback to default
                                        totp_field_selector = "input[name='code']"
                                
                                # CRITICAL: Fill the field using enhanced method that triggers all validation events
                                # The validated-field__input class requires proper event sequence for validation
                                # Use fill with is_totp=True to ensure proper event handling
                                await self.fill(totp_field_selector, fresh_totp_code, is_totp=True)
                                self.logger.info(f"[TOTP_SUBMIT] Step {step_number} Updated TOTP field with fresh code: {fresh_totp_code}")
                                
                                # CRITICAL: For React components, we need to update React's internal state
                                # login.gov uses React, and just setting el.value doesn't update React state
                                await asyncio.sleep(0.1)  # Small delay
                                try:
                                    react_update_code = f"""
                                    (function() {{
                                        const el = document.querySelector({json.dumps(totp_field_selector)});
                                        if (!el) return {{ success: false, error: 'Element not found' }};
                                        
                                        // Try to access React internal state (for React 16+)
                                        const reactKey = Object.keys(el).find(key => key.startsWith('__reactInternalInstance') || key.startsWith('__reactFiber'));
                                        if (reactKey) {{
                                            const reactInstance = el[reactKey];
                                            if (reactInstance) {{
                                                // Try to find the component that owns this input
                                                let fiber = reactInstance;
                                                while (fiber) {{
                                                    if (fiber.memoizedProps && fiber.memoizedProps.onChange) {{
                                                        // Found the component, trigger onChange with the new value
                                                        const syntheticEvent = {{
                                                            target: el,
                                                            currentTarget: el,
                                                            bubbles: true,
                                                            cancelable: true,
                                                            defaultPrevented: false,
                                                            eventPhase: 2,
                                                            isTrusted: false,
                                                            nativeEvent: new Event('input', {{ bubbles: true }}),
                                                            preventDefault: function() {{}},
                                                            stopPropagation: function() {{}},
                                                            timeStamp: Date.now(),
                                                            type: 'change'
                                                        }};
                                                        try {{
                                                            fiber.memoizedProps.onChange(syntheticEvent);
                                                        }} catch (e) {{
                                                            console.log('React onChange error:', e);
                                                        }}
                                                        break;
                                                    }}
                                                    fiber = fiber.return;
                                                }}
                                            }}
                                        }}
                                        
                                        // Also trigger native events for non-React handlers
                                        el.focus();
                                        el.dispatchEvent(new Event('input', {{ bubbles: true, cancelable: true }}));
                                        el.dispatchEvent(new Event('change', {{ bubbles: true, cancelable: true }}));
                                        el.blur();
                                        
                                        return {{
                                            success: true,
                                            value: el.value,
                                            hasReact: !!reactKey,
                                            valid: el.validity.valid,
                                            validationMessage: el.validationMessage || ''
                                        }};
                                    }})()
                                    """
                                    react_result = await self.evaluate(react_update_code)
                                    if isinstance(react_result, str):
                                        try:
                                            react_result = json.loads(react_result)
                                        except:
                                            pass
                                    
                                    if react_result and isinstance(react_result, dict):
                                        has_react = react_result.get('hasReact', False)
                                        is_valid = react_result.get('valid', False)
                                        if has_react:
                                            self.logger.info(f"[TOTP_SUBMIT] Step {step_number} ✅ React component detected and updated: {react_result.get('value')}")
                                        if is_valid:
                                            self.logger.info(f"[TOTP_SUBMIT] Step {step_number} ✅ Field validation passed: {react_result.get('value')}")
                                        else:
                                            self.logger.warning(f"[TOTP_SUBMIT] Step {step_number} ⚠️ Field validation failed: {react_result.get('validationMessage')}")
                                except Exception as react_error:
                                    self.logger.warning(f"[TOTP_SUBMIT] Step {step_number} Could not update React state: {react_error}")
                                
                                # CRITICAL: Wait a moment and trigger blur event to activate validation
                                # login.gov's validated-field component validates on blur
                                await asyncio.sleep(0.2)  # Small delay for validation to process
                                try:
                                    trigger_validation_code = f"""
                                    (function() {{
                                        const el = document.querySelector({json.dumps(totp_field_selector)});
                                        if (el) {{
                                            // Focus then blur to trigger validation
                                            el.focus();
                                            el.blur();
                                            // Also trigger input event to ensure validation runs
                                            el.dispatchEvent(new Event('input', {{ bubbles: true, cancelable: true }}));
                                            // Check validation state
                                            const isValid = el.validity.valid;
                                            const validationMessage = el.validationMessage || '';
                                            return {{
                                                success: true,
                                                value: el.value,
                                                valid: isValid,
                                                validationMessage: validationMessage,
                                                ariaInvalid: el.getAttribute('aria-invalid')
                                            }};
                                        }}
                                        return {{ success: false }};
                                    }})()
                                    """
                                    validation_result = await self.evaluate(trigger_validation_code)
                                    if isinstance(validation_result, str):
                                        try:
                                            import json
                                            validation_result = json.loads(validation_result)
                                        except:
                                            pass
                                    
                                    if validation_result and isinstance(validation_result, dict):
                                        is_valid = validation_result.get('valid', False)
                                        validation_msg = validation_result.get('validationMessage', '')
                                        if is_valid:
                                            self.logger.info(f"[TOTP_SUBMIT] Step {step_number} ✅ Field validation passed: {validation_result.get('value')}")
                                        else:
                                            self.logger.warning(f"[TOTP_SUBMIT] Step {step_number} ⚠️ Field validation failed: {validation_msg}")
                                    else:
                                        self.logger.info(f"[TOTP_SUBMIT] Step {step_number} Triggered validation events: {validation_result}")
                                except Exception as validation_error:
                                    self.logger.warning(f"[TOTP_SUBMIT] Step {step_number} Could not trigger validation events: {validation_error}")
                                
                                # Verify the field was updated
                                verify_code = f"document.querySelector({json.dumps(totp_field_selector)})?.value || ''"
                                verify_result = await self.evaluate(verify_code)
                                if verify_result == fresh_totp_code:
                                    self.logger.info(f"[TOTP_SUBMIT] Step {step_number} ✅ Verified TOTP code in field: {fresh_totp_code}")
                                else:
                                    self.logger.error(f"[TOTP_SUBMIT] Step {step_number} ❌ Field verification failed! Expected: {fresh_totp_code}, Got: {verify_result}")
                            except Exception as field_error:
                                self.logger.warning(f"[TOTP_SUBMIT] Step {step_number} Could not update TOTP field: {field_error}")
                                import traceback
                                self.logger.debug(f"[TOTP_SUBMIT] Step {step_number} Field update traceback: {traceback.format_exc()}")
                        except Exception as totp_error:
                            self.logger.error(f"[TOTP_SUBMIT] Step {step_number} Failed to generate fresh TOTP code: {totp_error}")
                            # Continue anyway - might still work with existing code
                    else:
                        self.logger.warning(f"[TOTP_SUBMIT] Step {step_number} Could not find TOTP secret key - proceeding with existing code in field")
                    
                    # Now click Submit with fresh TOTP code
                    # CRITICAL: Verify the correct code is in the field RIGHT BEFORE clicking Submit
                    try:
                        import json
                        selector_json = json.dumps(totp_field_selector)
                        final_verify = await self.evaluate(f"document.querySelector({selector_json})?.value || ''")
                        if secret_key and fresh_totp_code:
                            if final_verify == fresh_totp_code:
                                self.logger.info(f"[TOTP_SUBMIT] Step {step_number} ✅ VERIFIED: Correct TOTP code '{fresh_totp_code}' is in field before Submit click")
                            else:
                                self.logger.error(f"[TOTP_SUBMIT] Step {step_number} ❌ CRITICAL: Field has wrong code! Expected: '{fresh_totp_code}', Got: '{final_verify}'")
                                # Try to fix it one more time
                                self.logger.warning(f"[TOTP_SUBMIT] Step {step_number} Attempting to fix field value...")
                                await self.fill(totp_field_selector, fresh_totp_code, is_totp=True)
                                await asyncio.sleep(0.2)
                                final_verify_retry = await self.evaluate(f"document.querySelector({selector_json})?.value || ''")
                                if final_verify_retry == fresh_totp_code:
                                    self.logger.info(f"[TOTP_SUBMIT] Step {step_number} ✅ Field fixed, correct code now in field: '{fresh_totp_code}'")
                                else:
                                    self.logger.error(f"[TOTP_SUBMIT] Step {step_number} ❌ Field fix failed! Still has: '{final_verify_retry}'")
                    except Exception as verify_error:
                        self.logger.warning(f"[TOTP_SUBMIT] Step {step_number} Could not verify field value before Submit: {verify_error}")
                    
                    # For TOTP submission, try multiple times if it fails (code might expire)
                    max_retries = 2
                    for retry_attempt in range(max_retries):
                        try:
                            # CRITICAL: Verify field value RIGHT BEFORE clicking Submit
                            # The value might be getting cleared or lost
                            try:
                                import json
                                selector_json = json.dumps(totp_field_selector)
                                pre_click_value = await self.evaluate(f"document.querySelector({selector_json})?.value || ''")
                                self.logger.info(f"[TOTP_SUBMIT] Step {step_number} Field value RIGHT BEFORE click: '{pre_click_value}'")
                                
                                if pre_click_value != fresh_totp_code:
                                    self.logger.error(f"[TOTP_SUBMIT] Step {step_number} ❌ CRITICAL: Field value changed before click! Expected: '{fresh_totp_code}', Got: '{pre_click_value}'")
                                    # Try to fix it one more time
                                    self.logger.warning(f"[TOTP_SUBMIT] Step {step_number} Attempting to restore field value...")
                                    await self.fill(totp_field_selector, fresh_totp_code, is_totp=True)
                                    await asyncio.sleep(0.2)
                                    # Verify again
                                    post_fix_value = await self.evaluate(f"document.querySelector({selector_json})?.value || ''")
                                    if post_fix_value == fresh_totp_code:
                                        self.logger.info(f"[TOTP_SUBMIT] Step {step_number} ✅ Field value restored: '{fresh_totp_code}'")
                                    else:
                                        self.logger.error(f"[TOTP_SUBMIT] Step {step_number} ❌ Failed to restore field value! Still: '{post_fix_value}'")
                            except Exception as pre_click_check_error:
                                self.logger.warning(f"[TOTP_SUBMIT] Step {step_number} Could not check field value before click: {pre_click_check_error}")
                            
                            # CRITICAL: Try form submission instead of button click to prevent field clearing
                            # The field might be getting cleared by the button's click handler
                            try:
                                # First, try to submit the form programmatically
                                form_submit_code = f"""
                                (function() {{
                                    const el = document.querySelector({json.dumps(totp_field_selector)});
                                    if (!el || !el.form) return {{ success: false, error: 'No form found' }};
                                    
                                    // Ensure value is set right before submission
                                    el.value = {json.dumps(fresh_totp_code)};
                                    el.dispatchEvent(new Event('input', {{ bubbles: true, cancelable: true }}));
                                    el.dispatchEvent(new Event('change', {{ bubbles: true, cancelable: true }}));
                                    
                                    // Submit the form programmatically
                                    el.form.submit();
                                    return {{ success: true, value: el.value }};
                                }})()
                                """
                                form_submit_result = await self.evaluate(form_submit_code)
                                if isinstance(form_submit_result, str):
                                    try:
                                        form_submit_result = json.loads(form_submit_result)
                                    except:
                                        pass
                                
                                if form_submit_result and isinstance(form_submit_result, dict) and form_submit_result.get('success'):
                                    self.logger.info(f"[TOTP_SUBMIT] Step {step_number} ✅ Form submitted programmatically with value: {form_submit_result.get('value')}")
                                    # Wait for navigation
                                    await asyncio.sleep(2.0)
                                else:
                                    # Fallback to button click
                                    self.logger.warning(f"[TOTP_SUBMIT] Step {step_number} Form submission failed, falling back to button click: {form_submit_result}")
                                    await self.click(selector)
                                    self.logger.info(f"[TOTP_SUBMIT] Step {step_number} Clicked {selector} (attempt {retry_attempt + 1}/{max_retries})")
                            except Exception as form_submit_error:
                                # Fallback to button click if form submission fails
                                self.logger.warning(f"[TOTP_SUBMIT] Step {step_number} Form submission error, using button click: {form_submit_error}")
                                await self.click(selector)
                                self.logger.info(f"[TOTP_SUBMIT] Step {step_number} Clicked {selector} (attempt {retry_attempt + 1}/{max_retries})")
                            
                            # CRITICAL: Check field value IMMEDIATELY after click/submit to see if it's still there
                            try:
                                import json
                                selector_json = json.dumps(totp_field_selector)
                                post_click_value = await self.evaluate(f"document.querySelector({selector_json})?.value || ''")
                                self.logger.info(f"[TOTP_SUBMIT] Step {step_number} Field value IMMEDIATELY after click: '{post_click_value}'")
                                
                                if post_click_value != fresh_totp_code:
                                    self.logger.error(f"[TOTP_SUBMIT] Step {step_number} ❌ CRITICAL: Field value lost after click! Expected: '{fresh_totp_code}', Got: '{post_click_value}'")
                                    # Try to restore it immediately
                                    if post_click_value == '':
                                        self.logger.warning(f"[TOTP_SUBMIT] Step {step_number} Field was cleared! Attempting emergency restore...")
                                        restore_code = f"""
                                        (function() {{
                                            const el = document.querySelector({json.dumps(totp_field_selector)});
                                            if (el) {{
                                                el.value = {json.dumps(fresh_totp_code)};
                                                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                                return {{ success: true, value: el.value }};
                                            }}
                                            return {{ success: false }};
                                        }})()
                                        """
                                        restore_result = await self.evaluate(restore_code)
                                        self.logger.info(f"[TOTP_SUBMIT] Step {step_number} Emergency restore result: {restore_result}")
                            except Exception as post_click_check_error:
                                self.logger.warning(f"[TOTP_SUBMIT] Step {step_number} Could not check field value after click: {post_click_check_error}")
                            
                            # Wait briefly for navigation
                            await asyncio.sleep(2.0)  # Reduced wait for TOTP submission
                            
                            # Check if we successfully navigated away from TOTP page
                            try:
                                new_url = await self.evaluate("window.location.href")
                                
                                # CRITICAL: Check for error messages on the page
                                try:
                                    error_check_code = """
                                    (function() {
                                        // Check for common error message selectors
                                        const errorSelectors = [
                                            '.error', '.alert', '.alert-danger', '.alert-error',
                                            '[role="alert"]', '.invalid-feedback', '.text-danger',
                                            '.error-message', '.validation-error', '#error',
                                            '[class*="error"]', '[class*="invalid"]',
                                            '.usa-alert--error', '.usa-alert-body'
                                        ];
                                        
                                        for (const selector of errorSelectors) {
                                            const el = document.querySelector(selector);
                                            if (el && el.textContent && el.textContent.trim()) {
                                                return {
                                                    found: true,
                                                    selector: selector,
                                                    text: el.textContent.trim(),
                                                    visible: el.offsetWidth > 0 && el.offsetHeight > 0
                                                };
                                            }
                                        }
                                        
                                        // Also check for error text in common locations
                                        const bodyText = document.body.textContent || '';
                                        const errorKeywords = ['invalid', 'incorrect', 'wrong', 'error', 'failed', 'expired', 'try again'];
                                        for (const keyword of errorKeywords) {
                                            if (bodyText.toLowerCase().includes(keyword)) {
                                                // Find the element containing this keyword
                                                const walker = document.createTreeWalker(
                                                    document.body,
                                                    NodeFilter.SHOW_TEXT,
                                                    null
                                                );
                                                let node;
                                                while (node = walker.nextNode()) {
                                                    if (node.textContent.toLowerCase().includes(keyword)) {
                                                        const parent = node.parentElement;
                                                        if (parent && (parent.offsetWidth > 0 && parent.offsetHeight > 0)) {
                                                            return {
                                                                found: true,
                                                                selector: 'text-content',
                                                                text: parent.textContent.trim().substring(0, 200),
                                                                visible: true
                                                            };
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                        
                                        return { found: false };
                                    })()
                                    """
                                    error_result = await self.evaluate(error_check_code)
                                    # Evaluate returns a string, so parse JSON if it's a JSON object
                                    if isinstance(error_result, str):
                                        try:
                                            error_result = json.loads(error_result)
                                        except (json.JSONDecodeError, ValueError):
                                            # If it's not JSON, check if it contains error info
                                            if 'found' in error_result.lower() or 'error' in error_result.lower():
                                                self.logger.error(f"[TOTP_SUBMIT] Step {step_number} ERROR MESSAGE DETECTED (raw): {error_result}")
                                    
                                    if error_result and isinstance(error_result, dict) and error_result.get('found'):
                                        error_text = error_result.get('text', '')
                                        error_selector = error_result.get('selector', 'unknown')
                                        self.logger.error(f"[TOTP_SUBMIT] Step {step_number} ERROR MESSAGE DETECTED ON PAGE!")
                                        self.logger.error(f"[TOTP_SUBMIT] Step {step_number} Error selector: {error_selector}")
                                        self.logger.error(f"[TOTP_SUBMIT] Step {step_number} Error text: {error_text}")
                                        
                                        # Parse error text if it's JSON (login.gov sometimes returns JSON error messages)
                                        if error_text and error_text.startswith('{'):
                                            try:
                                                error_json = json.loads(error_text)
                                                for key, value in error_json.items():
                                                    self.logger.error(f"[TOTP_SUBMIT] Step {step_number} Error detail - {key}: {value}")
                                            except:
                                                pass
                                except Exception as error_check_ex:
                                    self.logger.warning(f"[TOTP_SUBMIT] Step {step_number} Could not check for error messages: {error_check_ex}")
                                    import traceback
                                    self.logger.debug(f"[TOTP_SUBMIT] Step {step_number} Error check traceback: {traceback.format_exc()}")
                                
                                if "two_factor" not in new_url.lower() and "authenticator" not in new_url.lower():
                                    self.logger.info(f"[TOTP_SUBMIT] Step {step_number} Successfully navigated away from TOTP page: {new_url}")
                                    break  # Success, exit retry loop
                                elif retry_attempt < max_retries - 1:
                                    self.logger.warning(f"[TOTP_SUBMIT] Step {step_number} Still on TOTP page after click, will retry. Current URL: {new_url}")
                                    # If still on TOTP page and we have retries left, regenerate TOTP and retry
                                    if secret_key:
                                        try:
                                            fresh_totp_code = generate_otp(secret_key)
                                            self.logger.info(f"[TOTP_SUBMIT] Step {step_number} Regenerating TOTP for retry: {fresh_totp_code}")
                                            await self.fill("input[name='code']", fresh_totp_code, is_totp=True)
                                            await asyncio.sleep(0.2)
                                        except Exception as retry_totp_error:
                                            self.logger.warning(f"[TOTP_SUBMIT] Step {step_number} Could not regenerate TOTP for retry: {retry_totp_error}")
                                    await asyncio.sleep(1.0)
                            except:
                                pass
                        except Exception as e:
                            if retry_attempt < max_retries - 1:
                                self.logger.warning(f"[TOTP_SUBMIT] Step {step_number} Click failed, retrying: {e}")
                                await asyncio.sleep(1.0)
                            else:
                                raise
                else:
                    # Standard click handling
                    # Check if this is Step 11 (Grant consent button) - needs special wait for URL change
                    # Detection: Step 11 OR step description contains "grant" AND "consent" OR selector contains "Grant"
                    is_grant_consent_click = (action == "click" and 
                                            (step_number == 11 or 
                                             ("grant" in step_description.lower() and "consent" in step_description.lower()) or
                                             "grant" in str(selector).lower()))
                    
                    await self.click(selector)
                    self.logger.info(f"Clicked {selector}")
                    
                    if is_grant_consent_click:
                        # CRITICAL: Step 11 (Grant consent) - actively wait for URL to change from consent page to hub
                        # The redirect to hub-stage.datacommons.cancer.gov may take several seconds
                        self.logger.info(f"[GRANT_CONSENT] Step {step_number} Clicked Grant button - waiting for URL to change to hub")
                        
                        # Actively poll for URL change (up to 20 seconds total)
                        max_wait_time = 20.0  # Total maximum wait time
                        check_interval = 1.0  # Check every 1 second
                        max_checks = int(max_wait_time / check_interval)
                        redirect_completed = False
                        
                        for check_num in range(max_checks):
                            try:
                                current_url = await self.evaluate("window.location.href")
                                self.logger.info(f"[GRANT_CONSENT] Step {step_number} Check {check_num + 1}/{max_checks}: Current URL: {current_url}")
                                
                                if "hub-stage.datacommons.cancer.gov" in current_url.lower():
                                    self.logger.info(f"[GRANT_CONSENT] Step {step_number} ✅ Successfully redirected to hub: {current_url}")
                                    redirect_completed = True
                                    break
                                elif "sts.nih.gov/auth/oauth/v2/authorize/consent" not in current_url.lower():
                                    # URL changed but not to hub yet - might be intermediate redirect
                                    self.logger.info(f"[GRANT_CONSENT] Step {step_number} URL changed to: {current_url} (waiting for hub redirect)")
                            except Exception as url_check_error:
                                self.logger.warning(f"[GRANT_CONSENT] Step {step_number} Could not check URL (check {check_num + 1}): {url_check_error}")
                            
                            if check_num < max_checks - 1:  # Don't wait after last check
                                await asyncio.sleep(check_interval)
                        
                        if not redirect_completed:
                            try:
                                final_url = await self.evaluate("window.location.href")
                                self.logger.warning(f"[GRANT_CONSENT] Step {step_number} ⚠️ Redirect not completed after {max_wait_time}s. Final URL: {final_url}")
                            except:
                                pass
                    else:
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
            # For TOTP steps, minimize wait to prevent code expiration
            # Check if this was a TOTP fill step
            is_totp_step = action == "fill" and any(keyword in step_description.lower() for keyword in ["totp", "one-time", "one time", "2fa", "two-factor", "authenticator code", "security code"])
            
            # Check if this is a TOTP submission click (for minimizing delays)
            # Detect if this is clicking Submit after TOTP entry (Step 10 scenario)
            is_totp_submission_click = (action == "click" and 
                                      any(keyword in step_description.lower() for keyword in ["submit", "complete login", "complete sign in"]) and
                                      (any(keyword in step_description.lower() for keyword in ["totp", "one-time", "2fa", "two-factor", "authenticator"]) or
                                       step_number == 10))  # Step 10 is always TOTP submission
            
            # DIAGNOSTIC: Write to file to confirm we reached screenshot section
            try:
                with open('/tmp/screenshot_diagnostic.log', 'a') as f:
                    import time
                    f.write(f"[{time.time()}] Step {step_number} reached screenshot section - action={action}, is_totp_step={is_totp_step}, step_desc={step_description[:50]}\n")
                    f.flush()
            except Exception as diag_error:
                pass  # Don't let diagnostic code break execution
            
            if is_totp_step:
                # DIAGNOSTIC: Write to file to confirm TOTP step detected
                try:
                    with open('/tmp/screenshot_diagnostic.log', 'a') as f:
                        import time
                        f.write(f"[{time.time()}] Step {step_number} TOTP step detected - parameters keys: {list(parameters.keys()) if parameters else 'None'}\n")
                        f.flush()
                except:
                    pass
                
                # For TOTP steps, check field value right before screenshot to see if it was cleared
                if action == "fill":
                    selector = parameters.get("selector") if parameters else None
                    # DIAGNOSTIC: Write selector info
                    try:
                        with open('/tmp/screenshot_diagnostic.log', 'a') as f:
                            import time
                            f.write(f"[{time.time()}] Step {step_number} TOTP fill check - selector={selector}, parameters type={type(parameters)}\n")
                            f.flush()
                    except:
                        pass
                    
                    if selector:
                        try:
                            escaped_selector = selector.replace("'", "\\'")
                            check_code = f"document.querySelector('{escaped_selector}')?.value || ''"
                            value_before_screenshot = await self.evaluate(check_code)
                            self.logger.info(f"[SCREENSHOT] Step {step_number} TOTP field value RIGHT BEFORE screenshot: '{value_before_screenshot}' (length: {len(str(value_before_screenshot))})")
                            
                            # DIAGNOSTIC: Check for multiple input elements and their visibility
                            # Use json.dumps to safely escape the selector for JavaScript
                            import json
                            selector_json = json.dumps(escaped_selector)
                            multi_check = f"""
                            (() => {{
                                const selector = {selector_json};
                                const elements = document.querySelectorAll(selector);
                                const results = [];
                                for (let i = 0; i < elements.length; i++) {{
                                    const el = elements[i];
                                    results.push({{
                                        index: i,
                                        value: el.value || '',
                                        visible: el.offsetWidth > 0 && el.offsetHeight > 0,
                                        display: window.getComputedStyle(el).display,
                                        type: el.type || '',
                                        name: el.name || '',
                                        id: el.id || ''
                                    }});
                                }}
                                return JSON.stringify({{count: elements.length, elements: results}});
                            }})()
                            """
                            multi_result = await self.evaluate(multi_check)
                            
                            # DIAGNOSTIC: Write field value and element info to file
                            try:
                                with open('/tmp/screenshot_diagnostic.log', 'a') as f:
                                    import time
                                    f.write(f"[{time.time()}] Step {step_number} TOTP field value before screenshot: '{value_before_screenshot}' (length: {len(str(value_before_screenshot))})\n")
                                    f.write(f"[{time.time()}] Step {step_number} Multiple elements check: {multi_result}\n")
                                    f.flush()
                            except:
                                pass
                            
                            # Also check for validation errors
                            error_check = f"document.querySelector('{escaped_selector}')?.validationMessage || document.querySelector('.error, .invalid, [role=alert]')?.textContent || ''"
                            error_msg = await self.evaluate(error_check)
                            if error_msg:
                                self.logger.warning(f"[SCREENSHOT] Step {step_number} Validation error detected: '{error_msg}'")
                        except Exception as e:
                            self.logger.warning(f"[SCREENSHOT] Step {step_number} Could not check field value before screenshot: {e}")
                            # DIAGNOSTIC: Write exception to file
                            try:
                                with open('/tmp/screenshot_diagnostic.log', 'a') as f:
                                    import time
                                    f.write(f"[{time.time()}] Step {step_number} Exception checking field value: {e}\n")
                                    f.flush()
                            except:
                                pass
                    else:
                        # DIAGNOSTIC: Write if selector is missing
                        try:
                            with open('/tmp/screenshot_diagnostic.log', 'a') as f:
                                import time
                                f.write(f"[{time.time()}] Step {step_number} TOTP fill check - selector is None or missing\n")
                                f.flush()
                        except:
                            pass
                
                # For TOTP submission clicks, minimize wait - we already clicked, just need screenshot
                if is_totp_submission_click:
                    await asyncio.sleep(0.1)  # Minimal wait just for screenshot capture - TOTP already submitted
                    self.logger.info(f"[SCREENSHOT] Step {step_number} TOTP submission click - using minimal wait (0.1s) to prevent code expiration")
                else:
                    await asyncio.sleep(0.5)  # Keep existing wait for TOTP fill steps
            else:
                await asyncio.sleep(2.5)  # Longer wait ensures page is fully loaded and rendered
            
            # Use absolute path for MCP
            abs_screenshot_path = str(screenshot_path.resolve())
            await self.take_screenshot(abs_screenshot_path)
            
            # DIAGNOSTIC: For TOTP steps, check field value IMMEDIATELY after screenshot to see if it was cleared
            if is_totp_step and action == "fill":
                selector = parameters.get("selector") if parameters else None
                if selector:
                    try:
                        escaped_selector = selector.replace("'", "\\'")
                        check_code = f"document.querySelector('{escaped_selector}')?.value || ''"
                        value_after_screenshot = await self.evaluate(check_code)
                        # DIAGNOSTIC: Write field value after screenshot
                        try:
                            with open('/tmp/screenshot_diagnostic.log', 'a') as f:
                                import time
                                f.write(f"[{time.time()}] Step {step_number} TOTP field value IMMEDIATELY AFTER screenshot: '{value_after_screenshot}' (length: {len(str(value_after_screenshot))})\n")
                                f.flush()
                        except:
                            pass
                        self.logger.info(f"[SCREENSHOT] Step {step_number} TOTP field value AFTER screenshot: '{value_after_screenshot}' (length: {len(str(value_after_screenshot))})")
                    except Exception as e:
                        try:
                            with open('/tmp/screenshot_diagnostic.log', 'a') as f:
                                import time
                                f.write(f"[{time.time()}] Step {step_number} Exception checking field value after screenshot: {e}\n")
                                f.flush()
                        except:
                            pass
            
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
            # Default to "unknown" - require explicit validation result
            step_status = "unknown"
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
                
                # Require explicit "valid" key in validation result
                if "valid" not in validation_result:
                    self.logger.error(f"Step {step_number} validation result missing 'valid' key: {validation_result}")
                    step_status = "failed"
                    validation_message = "Validation result missing 'valid' key"
                elif not validation_result.get("valid", False):
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
                    step_status = "passed"
                    self.logger.info(f"Step {step_number} validation passed: {validation_result.get('reasoning', 'OK')}")
                    
                    # Save selector to registry after successful step (for fill and click actions)
                    if step_status == "passed" and current_url and action in ["fill", "click"]:
                        try:
                            from core.selector_registry import SelectorRegistry
                            registry = SelectorRegistry()
                            
                            # Get element type from step description
                            element_type = registry.get_element_type_from_step(step_description, action)
                            
                            # If element_type is None, use a generic type based on action
                            if not element_type:
                                if action == "click":
                                    element_type = "button"  # Generic button type for clicks
                                elif action == "fill":
                                    element_type = "input"  # Generic input type for fills
                            
                            if element_type and "selector" in parameters:
                                selector = parameters.get("selector")
                                registry.save_selector(
                                    url=current_url,
                                    step_description=step_description,
                                    element_type=element_type,
                                    selector=selector,
                                    action=action
                                )
                                self.logger.info(f"Saved selector to registry: {element_type} -> {selector}")
                            else:
                                self.logger.debug(f"Skipping selector save: element_type={element_type}, has_selector={'selector' in parameters}, current_url={bool(current_url)}")
                        except Exception as registry_error:
                            # Don't fail the step if registry save fails
                            self.logger.warning(f"Failed to save selector to registry: {registry_error}")
                    
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
                "parameters": parameters,  # Include parameters in result
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


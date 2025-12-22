"""
AWS Bedrock client for LLM interactions
"""
import json
import boto3
import os
import time
import logging
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class BedrockClient:
    """Client for interacting with AWS Bedrock"""
    
    def __init__(self, region: str = None, model_id: str = None):
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        self.model_id = model_id or os.getenv(
            "BEDROCK_MODEL_ID", 
            "anthropic.claude-3-sonnet-20240229-v1:0"
        )
        
        # Initialize Bedrock runtime client
        self.client = boto3.client(
            'bedrock-runtime',
            region_name=self.region,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        )
    
    def invoke_model(
        self, 
        prompt: str, 
        max_tokens: int = 2000,
        temperature: float = 0.7,
        system_prompt: str = None
    ) -> str:
        """
        Invoke Bedrock model with retry logic
        
        Args:
            prompt: User prompt
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            system_prompt: Optional system prompt
        
        Returns:
            Model response text
        """
        messages = []
        
        if system_prompt:
            messages.append({
                "role": "user",
                "content": [{"type": "text", "text": system_prompt}]
            })
        
        messages.append({
            "role": "user",
            "content": [{"type": "text", "text": prompt}]
        })
        
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages
        }
        
        # Retry logic
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                response = self.client.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps(body)
                )
                
                response_body = json.loads(response['body'].read())
                return response_body['content'][0]['text']
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                
                if error_code == 'ThrottlingException' and attempt < max_retries - 1:
                    # Exponential backoff for throttling
                    wait_time = retry_delay * (2 ** attempt)
                    time.sleep(wait_time)
                    continue
                elif error_code == 'ModelNotReadyException' and attempt < max_retries - 1:
                    # Wait and retry if model is not ready
                    time.sleep(retry_delay * (2 ** attempt))
                    continue
                else:
                    raise RuntimeError(f"Bedrock API error: {e}")
            
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))
                    continue
                raise RuntimeError(f"Unexpected error calling Bedrock: {e}")
        
        raise RuntimeError("Failed to invoke Bedrock model after retries")
    
    def generate_test_cases(self, user_story: str) -> list[Dict[str, Any]]:
        """
        Generate test cases from user story
        
        Args:
            user_story: User story text
        
        Returns:
            List of test case dictionaries
        """
        prompt = f"""Generate comprehensive test cases from this user story. Include ALL required details.

User Story:
{user_story}

CRITICAL REQUIREMENTS - DO NOT OMIT:
1. **URLs**: Include complete URLs (e.g., https://hub-stage.datacommons.cancer.gov/) in step descriptions
2. **Credentials**: Include usernames, passwords, TOTP secret keys exactly as specified
3. **Selectors**: Include element selectors/identifiers when mentioned (button text, field names, etc.)
4. **Wait Requirements**: Include timeout values and wait conditions (e.g., "wait 10s for element")
5. **Validation Criteria**: Include ALL verification details from "Verify:", "Expected:", "Should show:" phrases
6. **Conditional Logic**: Preserve conditional steps (e.g., "If popup appears, click Continue")
7. **Expected Results**: Include specific expected outcomes for each step

Step Format Rules:
- Step description: Include action + all parameters (URLs, credentials, selectors, timeouts)
- Expected result: Include verification criteria (what to check, expected values, validation conditions)
- For "Step X: Action → Verify: Outcome": Put Action+params in description, Outcome+validation in expected_result

Generate 3-5 test cases covering:
- Happy path (primary flow)
- Key edge cases (if applicable)
- Critical error scenarios (if applicable)

JSON format (return ONLY valid JSON, no markdown):
{{
  "test_cases": [
    {{
      "id": "TC001",
      "name": "Test case name",
      "description": "Test case description",
      "steps": [
        {{
          "description": "Action with all details (URL, selector, credentials, timeout if specified)",
          "expected_result": "Complete verification criteria (what to check, expected values, validation)"
        }}
      ],
      "expected_result": "Overall expected outcome",
      "priority": "High|Medium|Low"
    }}
  ]
}}

IMPORTANT:
- Preserve ALL URLs, credentials, selectors, timeouts, and validation details from user story
- Keep descriptions clear and complete (not overly verbose, but include all necessary info)
- Ensure expected_result includes specific verification criteria
- Escape special chars in JSON: \\n, \\", \\\\
- Return ONLY valid JSON, no markdown code blocks"""

        response = self.invoke_model(prompt, max_tokens=4000)
        
        # Parse JSON from response with robust error handling
        try:
            # Remove markdown code blocks if present
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            # Try to parse JSON
            try:
                data = json.loads(response)
            except json.JSONDecodeError as json_err:
                # Try to fix common JSON issues
                import re
                # Fix unescaped quotes in strings (basic attempt)
                # This is a simple fix - for more complex cases, we'll try to extract JSON from the response
                
                # Try to find JSON object boundaries
                json_match = re.search(r'\{[\s\S]*"test_cases"[\s\S]*\}', response)
                if json_match:
                    try:
                        # Try parsing the extracted JSON
                        data = json.loads(json_match.group(0))
                    except:
                        # If that fails, try to fix common issues
                        fixed_json = json_match.group(0)
                        # Fix unescaped newlines in strings
                        fixed_json = re.sub(r'(?<!\\)\n(?=")', '\\n', fixed_json)
                        # Fix unescaped quotes in string values (very basic - may not work for all cases)
                        # This is a last resort - better to ask LLM to regenerate
                        try:
                            data = json.loads(fixed_json)
                        except:
                            # Last attempt: try to extract just the test_cases array
                            array_match = re.search(r'"test_cases"\s*:\s*\[[\s\S]*\]', response)
                            if array_match:
                                # Wrap in object
                                wrapped = '{' + array_match.group(0) + '}'
                                try:
                                    data = json.loads(wrapped)
                                except:
                                    raise ValueError(f"Failed to parse test cases from LLM response after multiple attempts. Original error: {json_err}. Response length: {len(response)}")
                            else:
                                raise ValueError(f"Failed to parse test cases from LLM response. JSON error: {json_err}. Response preview: {response[:500]}")
                else:
                    raise ValueError(f"Failed to parse test cases from LLM response. Could not find JSON structure. Error: {json_err}. Response preview: {response[:500]}")
            
            test_cases = data.get("test_cases", [])
            
            # Ensure steps are properly formatted with expected_result
            for test_case in test_cases:
                if "steps" in test_case:
                    formatted_steps = []
                    for step in test_case["steps"]:
                        if isinstance(step, str):
                            # If step is just a string, try to extract expected result
                            formatted_steps.append({
                                "description": step,
                                "expected_result": None
                            })
                        elif isinstance(step, dict):
                            # If step is already a dict, ensure it has expected_result
                            if "expected_result" not in step:
                                step["expected_result"] = None
                            formatted_steps.append(step)
                    test_case["steps"] = formatted_steps
            
            return test_cases
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse test cases from LLM response: {e}")
    
    def generate_playwright_code(self, test_cases: list[Dict[str, Any]], execution_id: str) -> str:
        """
        Generate Playwright test code from test cases
        
        Args:
            test_cases: List of test case dictionaries
            execution_id: Execution identifier for screenshot paths
        
        Returns:
            Playwright JavaScript code
        """
        test_cases_json = json.dumps(test_cases, indent=2)
        
        prompt = f"""Generate Playwright test code for the following test cases:
{test_cases_json}

Requirements:
1. Use Playwright best practices
2. Add screenshot capture after EACH step using: await page.screenshot({{ path: 'screenshots/execution_{execution_id}/TC{{test_case_id}}/step_{{step_number:02d}}_{{description}}.png' }})
3. Use descriptive locators (text-based preferred over XPath)
4. Include proper waits (page.wait_for_load_state, page.wait_for_selector)
5. Add error handling with try-catch blocks
6. For login flows, include 2FA handling:
   - Generate TOTP code using: const {{ execSync }} = require('child_process'); const otp = execSync('python3 generateOTP.py ${{process.env.TOTP_SECRET_KEY}}').toString().trim();
   - Enter TOTP in 2FA field
7. Use async/await syntax
8. Group tests by test case ID
9. Add test descriptions

Format: JavaScript Playwright test file (.spec.js)

Return ONLY the JavaScript code, no markdown code blocks, no explanations."""

        response = self.invoke_model(prompt, max_tokens=8000)
        
        # Clean up response
        response = response.strip()
        if response.startswith("```javascript"):
            response = response[13:]
        elif response.startswith("```js"):
            response = response[5:]
        elif response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        
        return response.strip()
    
    def analyze_results(self, results: Dict[str, Any], screenshot_paths: list[str] = None) -> Dict[str, Any]:
        """
        Analyze test execution results using LLM
        
        Args:
            results: Test execution results dictionary
            screenshot_paths: Optional list of screenshot paths
        
        Returns:
            Analysis dictionary with summary, insights, recommendations
        """
        results_json = json.dumps(results, indent=2)
        screenshots_info = "\n".join(screenshot_paths) if screenshot_paths else "No screenshots available"
        
        prompt = f"""Analyze the following test execution results:
{results_json}

Screenshots are available at:
{screenshots_info}

Provide a comprehensive analysis in the following JSON format:
{{
  "summary": {{
    "total": number,
    "passed": number,
    "failed": number,
    "duration": number,
    "success_rate": percentage
  }},
  "detailed_analysis": [
    {{
      "test_case_id": "TC001",
      "status": "passed/failed",
      "analysis": "Detailed analysis of the test",
      "issues": ["issue1", "issue2"],
      "recommendations": ["rec1", "rec2"]
    }}
  ],
  "overall_insights": "Overall insights about the test execution",
  "recommendations": ["General recommendation 1", "General recommendation 2"],
  "screenshot_analysis": "Analysis of any issues visible in screenshots"
}}

Return ONLY the JSON object, no additional text."""

        response = self.invoke_model(prompt, max_tokens=4000)
        
        # Parse JSON from response
        try:
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            return json.loads(response)
        except json.JSONDecodeError as e:
            # Fallback: return basic analysis
            return {
                "summary": {
                    "total": len(results.get("test_results", [])),
                    "passed": sum(1 for r in results.get("test_results", []) if r.get("status") == "passed"),
                    "failed": sum(1 for r in results.get("test_results", []) if r.get("status") == "failed"),
                    "duration": results.get("duration", 0),
                    "success_rate": 0
                },
                "detailed_analysis": [],
                "overall_insights": "Analysis parsing failed, please review results manually",
                "recommendations": [],
                "screenshot_analysis": ""
            }
    
    def interpret_step(
        self,
        step_description: str,
        playwright_code: Optional[str] = None,
        dom_snapshot: Optional[str] = None,
        expected_result: Optional[str] = None,
        current_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Interpret a test step description using LLM to determine the action, parameters, and validation criteria
        First checks selector registry for known selectors before using LLM
        
        Args:
            step_description: Natural language step description
            playwright_code: Optional generated Playwright code for context
            dom_snapshot: Optional current page DOM snapshot for element finding
            expected_result: Optional expected result/assertion from user story
            current_url: Optional current page URL for selector registry lookup
        
        Returns:
            Dictionary with action type, parameters, and validation criteria
        """
        # Check selector registry first (if URL provided and action is fill/click)
        logger.info(f"Registry check: current_url='{current_url}', step='{step_description[:60]}...'")
        if current_url and current_url.strip():
            try:
                from core.selector_registry import SelectorRegistry
                registry = SelectorRegistry()
                
                # Determine action type from step description
                step_lower = step_description.lower()
                action_type = None
                if any(kw in step_lower for kw in ["navigate", "go to", "open", "visit"]):
                    action_type = "navigate"
                elif any(kw in step_lower for kw in ["click", "press", "select"]):
                    action_type = "click"
                elif any(kw in step_lower for kw in ["enter", "type", "fill", "input"]):
                    action_type = "fill"
                
                logger.info(f"Registry check: action_type='{action_type}' for step: '{step_description[:60]}...'")
                
                # If it's a fill or click action, try to get element type and lookup selector
                if action_type in ["fill", "click"]:
                    element_type = registry.get_element_type_from_step(step_description, action_type)
                    logger.info(f"Registry check: element_type='{element_type}' for action_type='{action_type}'")
                    if element_type:
                        logger.info(f"Registry lookup: Checking for element_type '{element_type}' with URL '{current_url}'")
                        cached_selector = registry.lookup_selector(
                            current_url,
                            step_description,
                            element_type,
                            action_type
                        )
                        if cached_selector:
                            logger.info(f"Registry lookup SUCCESS: Found cached selector '{cached_selector}' for '{element_type}'")
                            # Found selector in registry - use it directly
                            parameters = {"selector": cached_selector}
                            
                            # Extract text for fill actions
                            if action_type == "fill":
                                # Try to extract text from step description
                                import re
                                text_extracted = False
                                
                                # Pattern 1: "Enter username: value" or "Type password: value"
                                text_match = re.search(r'(?:enter|type|fill|input).*?:\s*([^\n]+?)(?:\s+Expected|\s+Verify|$)', step_description, re.IGNORECASE)
                                if text_match:
                                    text_value = text_match.group(1).strip()
                                    # Remove trailing punctuation if it's part of the description
                                    text_value = re.sub(r'[.,;:]$', '', text_value)
                                    if text_value:
                                        parameters["text"] = text_value
                                        text_extracted = True
                                
                                # Pattern 2: Look for email pattern
                                if not text_extracted:
                                    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', step_description)
                                    if email_match:
                                        parameters["text"] = email_match.group(0)
                                        text_extracted = True
                                
                                # Pattern 3: Look for quoted strings
                                if not text_extracted:
                                    quoted_match = re.search(r'["\']([^"\']+)["\']', step_description)
                                    if quoted_match:
                                        parameters["text"] = quoted_match.group(1)
                                        text_extracted = True
                                
                            # Return cached selector if we have all required parameters
                            # For fill: need both selector and text
                            # For click: only need selector
                            if action_type == "fill":
                                if "text" in parameters:
                                    # Have both selector and text - use cached selector
                                    return {
                                        "action": action_type,
                                        "parameters": parameters,
                                        "validation": {
                                            "type": "inferred",
                                            "assertions": [],
                                            "timeout": 5000
                                        },
                                        "reasoning": f"Used cached selector from registry: {cached_selector}",
                                        "from_registry": True
                                    }
                                # Text not extracted - let LLM handle it (will use cached selector if provided in context)
                                # Add cached selector hint to DOM snapshot for LLM to use
                                if dom_snapshot:
                                    dom_snapshot = f"CACHED_SELECTOR_HINT: Use selector '{cached_selector}' for this element.\n\n{dom_snapshot}"
                                else:
                                    dom_snapshot = f"CACHED_SELECTOR_HINT: Use selector '{cached_selector}' for this element."
                            elif action_type == "click":
                                # Click only needs selector - use cached selector
                                return {
                                    "action": action_type,
                                    "parameters": parameters,
                                    "validation": {
                                        "type": "inferred",
                                        "assertions": [],
                                        "timeout": 5000
                                    },
                                    "reasoning": f"Used cached selector from registry: {cached_selector}",
                                    "from_registry": True
                                }
                            # If we get here for fill without text, continue to LLM with selector hint
                        else:
                            logger.debug(f"Registry lookup: No cached selector found for element_type '{element_type}'")
                    else:
                        logger.debug(f"Registry lookup: Could not infer element_type from step: '{step_description[:50]}...'")
            except Exception as registry_error:
                # Registry lookup failed - log and continue with LLM interpretation
                logger.debug(f"Selector registry lookup failed: {registry_error}. Continuing with LLM interpretation.")
        
        # Build context string
        context_parts = []
        
        if playwright_code:
            # Truncate if too long to avoid token limits
            code_preview = playwright_code[:2000] if len(playwright_code) > 2000 else playwright_code
            context_parts.append(f"Generated Playwright Code:\n{code_preview}")
        
        if dom_snapshot:
            # Truncate DOM if too long
            dom_preview = dom_snapshot[:3000] if len(dom_snapshot) > 3000 else dom_snapshot
            context_parts.append(f"Current Page DOM (if available):\n{dom_preview}")
        
        context = "\n\n".join(context_parts) if context_parts else "No additional context available"
        
        expected_result_context = ""
        if expected_result:
            expected_result_context = f"\n\nExpected Result: {expected_result}"
        
        prompt = f"""You are a test automation AI. Given a test step description, determine what Playwright action to perform and how to validate success.

Step Description: {step_description}{expected_result_context}

Context:
{context}

⚠️ CRITICAL: Read the Step Description FIRST. The step description is the PRIMARY source of truth. Do NOT be misled by context (Playwright code or DOM snapshot) if it contradicts the step description.

Available MCP Actions:
- navigate(url): Navigate to a URL
- click(selector): Click an element
- fill(selector, text): Fill an input field
- wait_for(selector, timeout): Wait for element to appear
- get_text(selector): Get element text
- screenshot(path): Take screenshot (ONLY for verification-only steps that don't require any action)

🚨 ABSOLUTE PRIORITY RULES (CHECK IN THIS ORDER):
1. **NAVIGATION IS HIGHEST PRIORITY** - If the step description contains ANY of these: "Navigate to", "Go to", "Open", "Visit", "Navigate", OR contains a URL pattern (http:// or https://), you MUST use "navigate" action. IGNORE all other context.
   Examples:
   - "Navigate to https://example.com" → action: "navigate", url: "https://example.com" (even if context shows other elements)
   - "Go to the login page" → action: "navigate" (extract URL from context or step)
   - "Open homepage" → action: "navigate" (extract URL from context)
   - If step says "Navigate to https://hub-stage.datacommons.cancer.gov/" → action MUST be "navigate", url MUST be "https://hub-stage.datacommons.cancer.gov/"
   
2. **CLICK KEYWORDS** - If step contains "Click", "Press", "Select", "Choose" (and NO navigation keywords), use "click" action
   Examples:
   - "Click Sign In button" → action: "click", selector: "button:has-text('Sign In')"
   - "Press Submit" → action: "click", selector: "button[type='submit']"
   
3. **FILL KEYWORDS** - If step contains "Enter", "Type", "Fill", "Input" (and NO navigation keywords), use "fill" action
   Examples:
   - "Enter email address" → action: "fill", selector: "input[type='email']", text: (extract from step or context)
   - "Type password" → action: "fill", selector: "input[type='password']", text: (extract from step or context)
   - **TOTP/2FA STEPS**: If step mentions "Generate TOTP", "TOTP code", "one-time code", "2FA code", "authenticator code":
     * Use "fill" action with selector for the TOTP input field (typically "input[name='code']" or "input[type='text']" for TOTP)
     * For text parameter, include the secret key in the text (e.g., "TOTP code generated from secret key LCBUDA6NSWXUO4AKLTU6F3UXXO7QMBCX")
     * The system will automatically generate the actual TOTP code from the secret key
     * Example: "Generate TOTP code using secret key LCBUDA6NSWXUO4AKLTU6F3UXXO7QMBCX and enter it" → action: "fill", selector: "input[name='code']", text: "TOTP code generated from secret key LCBUDA6NSWXUO4AKLTU6F3UXXO7QMBCX"
   
4. **WAIT KEYWORDS** - If step contains "Wait for", "Wait until", use "wait_for" action
   
5. **GET TEXT KEYWORDS** - If step contains "Get text", "Read", "Extract text", use "get_text" action
   
6. **SCREENSHOT** - ONLY use "screenshot" if the step is PURELY verification with no action required (e.g., "Take screenshot", "Capture page state")
   - DO NOT use "screenshot" for steps that require navigation, clicking, filling, etc.
   - Screenshots are automatically taken after each action, so "screenshot" action is rarely needed

DECISION PROCESS:
1. **STEP 1 - Check Step Description for Navigation**: Look at the step description. Does it contain "Navigate to", "Go to", "Open", "Visit", "Navigate", or a URL (http:// or https://)?
   - YES → Action is "navigate". Extract URL from step description. STOP HERE. Do not check context for other actions.
   - NO → Continue to Step 2
   
2. **STEP 2 - Check Step Description for Other Keywords**: Look for "Click", "Enter", "Type", "Fill", "Wait for", etc.
   - Extract action and parameters from step description
   
3. **STEP 3 - Use Context Only for Missing Parameters**: Only use Playwright code or DOM snapshot to find selectors if they're not in the step description
4. For selectors, prefer CSS selectors (e.g., "#id", ".class", "button[type='submit']") or text-based locators
6. **Determine validation criteria** - what indicates the step was successful:
   - For navigate: URL should match expected (check URL contains expected path/domain)
   - For click: Verify element was clicked (check URL changed, new element appeared, or element state changed)
   - For fill: Verify text was entered (check input value matches entered text)
   - For wait_for: Element should appear (already validated by wait)
   - For get_text: Text should be retrieved (already validated by retrieval)
   - If explicit assertion provided (e.g., "Verify that..."), use that as validation
7. Priority: Use explicit assertions if provided, otherwise infer validation from action context

Return JSON (return ONLY valid JSON, no markdown):
{{
  "action": "navigate|click|fill|wait_for|get_text|screenshot",
  "parameters": {{
    "url": "...",  // for navigate (required if action is navigate)
    "selector": "...",  // for click, fill, wait_for, get_text (required if action needs selector)
    "text": "...",  // for fill (required if action is fill)
    "timeout": 30000,  // for wait_for (optional, default 30000ms)
    "path": "..."  // for screenshot (optional)
  }},
  "validation": {{
    "type": "explicit|inferred|playwright",  // explicit if assertion provided, inferred if determined from context, playwright for default checks
    "assertions": ["assertion1", "assertion2"],  // list of what to verify
    "selector": "...",  // element to verify (if applicable)
    "expected_text": "...",  // expected text content (if applicable)
    "expected_url": "...",  // expected URL pattern (if applicable)
    "expected_state": "visible|enabled|clickable",  // expected element state (if applicable)
    "timeout": 5000  // validation timeout in ms (default 5000)
  }},
  "reasoning": "Brief explanation of why this action was chosen and how parameters were extracted"
}}

Return ONLY the JSON object, no additional text."""

        response = self.invoke_model(prompt, max_tokens=1000, temperature=0.3)
        
        # Parse JSON from response
        try:
            # Remove markdown code blocks if present
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            interpretation = json.loads(response)
            
            # Validate required fields based on action
            action = interpretation.get("action")
            parameters = interpretation.get("parameters", {})
            
            if action == "navigate" and not parameters.get("url"):
                raise ValueError("Navigate action requires 'url' parameter")
            elif action in ["click", "fill", "wait_for", "get_text"] and not parameters.get("selector"):
                raise ValueError(f"{action} action requires 'selector' parameter")
            elif action == "fill" and not parameters.get("text"):
                raise ValueError("Fill action requires 'text' parameter")
            
            # Ensure validation field exists with defaults
            if "validation" not in interpretation:
                interpretation["validation"] = {
                    "type": "inferred",
                    "assertions": [],
                    "timeout": 5000
                }
            else:
                # Set defaults for validation
                validation = interpretation["validation"]
                if "type" not in validation:
                    validation["type"] = "inferred"
                if "assertions" not in validation:
                    validation["assertions"] = []
                if "timeout" not in validation:
                    validation["timeout"] = 5000
            
            return interpretation
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse step interpretation from LLM response: {e}. Response: {response[:200]}")
        except KeyError as e:
            raise ValueError(f"Invalid interpretation format: missing {e}")
    
    def validate_step_with_llm(
        self,
        step_description: str,
        action: str,
        action_parameters: Dict[str, Any],
        expected_result: Optional[str] = None,
        dom_snapshot: Optional[str] = None,
        playwright_tool_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ask LLM to validate if a test step was successful using Playwright tools.
        NO hardcoded validation logic - LLM decides what to check and how.
        
        Args:
            step_description: The test step description
            action: The action that was executed (navigate, click, fill, etc.)
            action_parameters: Parameters used for the action (url, selector, text, etc.)
            expected_result: Optional expected result from user story
            dom_snapshot: Optional current page DOM snapshot
            playwright_tool_results: Optional results from Playwright tools (evaluate, get_text, etc.)
        
        Returns:
            {
                "valid": bool,
                "reasoning": str,
                "checks_needed": List[Dict],
                "checks_performed": List[str],
                "evidence": str
            }
        """
        # Build context about what was executed
        action_context = f"Action: {action}\nParameters: {action_parameters}"
        
        if expected_result:
            action_context += f"\nExpected Result: {expected_result}"
        
        # Include DOM snapshot (truncated)
        dom_context = ""
        if dom_snapshot:
            dom_preview = dom_snapshot[:5000] if len(dom_snapshot) > 5000 else dom_snapshot
            dom_context = f"\n\nCurrent Page DOM:\n{dom_preview}"
        
        # Include Playwright tool results if available
        tool_results_context = ""
        if playwright_tool_results:
            # Format tool results more explicitly, especially for URL checks
            formatted_results = {}
            for key, value in playwright_tool_results.items():
                formatted_results[key] = value
                # If this is a URL check, make it very explicit
                if isinstance(value, dict) and value.get("is_url_check"):
                    formatted_results[key]["explicit_note"] = f"THIS IS THE CURRENT PAGE URL: {value.get('url', value.get('result', 'unknown'))}"
            
            tool_results_context = f"\n\nPlaywright Tool Results (evidence gathered):\n{json.dumps(formatted_results, indent=2)}"
            
            # Add explicit guidance for URL checks
            url_checks = [k for k, v in playwright_tool_results.items() if isinstance(v, dict) and v.get("is_url_check")]
            if url_checks:
                tool_results_context += f"\n\nIMPORTANT: URL checks were performed. Look for 'url' or 'result' fields in the tool results above to see the actual current page URL."
        
        prompt = f"""You are a test automation AI. A test step was just executed, and you need to determine if it was successful.

Step Description: {step_description}

{action_context}{dom_context}{tool_results_context}

🚨 CRITICAL FOR NAVIGATE ACTIONS: If the action is "navigate", you MUST:
- ONLY validate that the URL matches the destination in the step description
- IGNORE any "Expected Result" that mentions login, authentication, user logged in, or final test outcomes
- DO NOT check for login status, authentication state, or whether the final test goal was achieved
- Navigation success = URL matches destination. That's it. Nothing else.

Available Playwright Tools (you can request these to verify):
- get_dom(): Get page HTML snapshot - **PREFERRED for validation** - Use this to check page content, elements, and infer URL from DOM structure
- get_text(selector): Get element text content - Use to verify specific element text
- wait_for(selector): Wait for element to appear - Use to verify element visibility
- evaluate(code): Execute JavaScript in browser - **NOW WORKING** - Use for URL checks and DOM queries
  Examples: 
    * "window.location.href" (to get current URL) - **PREFERRED FORMAT**
    * "(function() {{ return window.location.href; }})()" (alternative format for URL)
    * "document.querySelector('input[type=email]').value" (to get input value)
    * "(function() {{ return document.title; }})()" (to get page title)
  **IMPORTANT**: Use direct expressions like "window.location.href" or IIFE format. Arrow functions like "() => window.location.href" will be auto-converted.

Task: Determine if this step was successful. 

CRITICAL: Validate ONLY what this specific step accomplishes, NOT the final goal of the entire test.

IMPORTANT VALIDATION RULES:
- **Each step is validated independently** - Only check if THIS step did what it's supposed to do
    - **Do NOT apply the final test goal to intermediate steps** - If the final goal is "user logged in", don't check login status on "Open homepage" step
- **Focus on the immediate outcome** of this specific action

For CLICK actions: The clicked element may DISAPPEAR after clicking (this is NORMAL and EXPECTED). 
  DO NOT check if the clicked element still exists. Instead:
  * **CRITICAL: CONDITIONAL STEPS** - If step description contains "If X appears", "If X is visible", "If X exists", etc.:
    - This is a CONDITIONAL/OPTIONAL step - it means "IF the element exists, click it; IF it doesn't exist, skip it"
    - **If the element was found and clicked**: Validate that the click succeeded (element disappeared, page changed, etc.)
    - **If the element was NOT found**: The step PASSES (it's optional - no element means nothing to click, which is valid)
    - **DO NOT fail the step just because the element doesn't exist** - Conditional steps are designed to handle optional UI elements
    - Example: "If a popup banner appears, click 'Continue' button" → If popup exists and was clicked → PASS. If popup doesn't exist → PASS (optional step)
  * Analyze ONLY the step description to infer what should happen immediately:
    - "Click Sign In" → Expect login page appears (login form visible, URL may change to login page)
    - "Click Add to Cart" → Expect cart icon updates OR cart page appears
    - "Click Submit" → Expect next page/form appears OR success message
  * **CRITICAL FOR NAVIGATION CLICKS**: If the step description mentions navigation (e.g., "Click Sign In" should navigate to login page):
    - **PREFERRED**: Use evaluate("window.location.href") to check the current URL directly
    - **ALTERNATIVE**: Use get_dom() to check for page content that indicates navigation (e.g., login form, expected page heading, page structure)
    - Compare the actual URL from evaluate() with the expected URL from step description
    - If URL matches expected destination (e.g., contains expected domain/path), the step PASSED
    - If URL doesn't match but step description says it should navigate, the step FAILED
    - If evaluate() is unavailable, fall back to DOM content checks
  * Check for new elements that should appear immediately
  * Check for page content change
  * If no specific outcome is clear, verify the action executed without error
  
    For NAVIGATE actions: 
      * **ONLY check if URL matches the destination** - This is the ONLY validation needed for navigation
      * **IGNORE any "Expected Result" that mentions login, authentication, or final test goals** - Those are for LATER steps, not this navigation step
      * **DO NOT check login status, authentication state, or final outcomes** - Navigation only needs to verify the URL is correct
      * Example: If step is "Navigate to https://example.com" and expected_result says "user logged in", IGNORE the login part - only check URL matches "https://example.com"
      * If URL from evaluate("window.location.href") matches the destination URL in step description → STEP PASSED (regardless of what expected_result says)
  
For FILL actions: Check if the entered text is in the input field value

For WAIT_FOR actions: The action itself validates (element appeared)

For GET_TEXT actions: The action itself validates (text retrieved)

VALIDATION STRATEGY:
    1. **Read ONLY the step description** - it tells you what THIS step should accomplish:
       - "Navigate to https://example.com" → Expect URL is "https://example.com" (ONLY check URL, ignore any expected_result about login/final goals)
       - "Open homepage" → Expect homepage loaded (that's it, don't check login)
       - "Click Sign In" → Expect login page appears (login form visible, URL may change)
       - "Enter email" → Expect email field contains the entered text
       - "Click Submit" → Expect next page or success message appears
   
2. **CRITICAL: For NAVIGATE actions, IGNORE expected_result completely** - If action is "navigate", ONLY check URL matches destination. Ignore any expected_result that mentions login, authentication, or final outcomes.
   
3. **Ignore the final test goal for intermediate steps** - Only the LAST step should verify the final outcome

3. **Infer from THIS step's context only**:
   - What should happen immediately after this action?
   - What page/elements should appear right now?
   - What URL should the page have right now?

4. **Use Playwright tools** to gather evidence (in priority order):
   - **evaluate(code)** - **PRIMARY FOR URL CHECKS** - Use "window.location.href" to get current URL
     * For URL validation: Use evaluate("window.location.href") to check current page URL
     * For DOM queries: Use evaluate("document.querySelector('selector').value") to get element values
   - **get_dom()** - **ALTERNATIVE/FALLBACK** - Use to check page content, structure, and infer navigation state
     * For URL validation (fallback): Check DOM for page-specific elements (e.g., login form for login pages)
     * For content validation: Check for expected text, headings, form fields, buttons
   - **get_text(selector)** - Use to verify specific element text content
   - **wait_for(selector)** - Use to verify element appeared/visible
   
   **IMPORTANT**: When tool results are provided, they contain the ACTUAL values from the browser.
   - **For URL validation**: Use evaluate("window.location.href") to get the actual URL, then compare with expected URL
   - **For content validation**: Use get_dom() or get_text() to verify expected content exists
   - **evaluate() now works correctly** - use it for URL checks with format "window.location.href"
   - If URL from evaluate() matches expected destination, that IS evidence of successful navigation

5. **Make decision** - Did THIS step accomplish what its description says it should? (Not what the final test should achieve)

If you need to use Playwright tools, specify them in your response. The system will execute them and provide results.

Return JSON (return ONLY valid JSON, no markdown):
{{
  "valid": true/false,
  "reasoning": "Why it passed/failed - be specific about what you checked",
  "checks_needed": [
    {{
      "tool": "evaluate|get_text|get_dom|wait_for",
      "code_or_selector": "JavaScript code (for evaluate) or selector (for get_text/wait_for) or empty (for get_dom)",
      "purpose": "What you're checking and why"
    }}
  ],
  "checks_performed": ["check1", "check2"],  // Will be filled after tools are executed
  "evidence": "What evidence proves pass/fail"  // Will be filled after tools are executed
}}

If you can determine validity from the provided context (DOM, action parameters, expected result), return checks_needed as empty array and provide your reasoning.

Return ONLY the JSON object, no additional text."""

        response = self.invoke_model(prompt, max_tokens=1500, temperature=0.3)
        
        # Parse JSON from response
        try:
            # Remove markdown code blocks if present
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            validation_result = json.loads(response)
            
            # Validate required fields
            if "valid" not in validation_result:
                raise ValueError("LLM validation response missing 'valid' field")
            if "reasoning" not in validation_result:
                raise ValueError("LLM validation response missing 'reasoning' field")
            
            # Ensure checks_needed is a list
            if "checks_needed" not in validation_result:
                validation_result["checks_needed"] = []
            if not isinstance(validation_result["checks_needed"], list):
                validation_result["checks_needed"] = []
            
            # Ensure checks_performed is a list
            if "checks_performed" not in validation_result:
                validation_result["checks_performed"] = []
            if not isinstance(validation_result["checks_performed"], list):
                validation_result["checks_performed"] = []
            
            # Ensure evidence exists
            if "evidence" not in validation_result:
                validation_result["evidence"] = validation_result.get("reasoning", "")
            
            return validation_result
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse validation response from LLM: {e}. Response: {response[:200]}")
        except ValueError as e:
            raise ValueError(f"LLM validation response validation failed: {e}. Response: {response[:200]}")


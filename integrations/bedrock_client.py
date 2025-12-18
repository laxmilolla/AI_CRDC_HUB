"""
AWS Bedrock client for LLM interactions
"""
import json
import boto3
import os
import time
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError


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
        prompt = f"""You are a QA automation engineer. Given the following user story, generate comprehensive test cases.

User Story:
{user_story}

Generate test cases in the following JSON format (return ONLY valid JSON, no markdown):
{{
  "test_cases": [
    {{
      "id": "TC001",
      "name": "Test Case Name",
      "description": "Detailed description",
      "steps": ["step1", "step2", ...],
      "expected_result": "What to verify",
      "priority": "High"
    }}
  ]
}}

Generate comprehensive test cases covering:
- Happy path scenarios
- Edge cases
- Error handling
- Validation scenarios

Return ONLY the JSON object, no additional text."""

        response = self.invoke_model(prompt, max_tokens=4000)
        
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
            
            data = json.loads(response)
            return data.get("test_cases", [])
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


"""
Test case generation using LLM
"""
import uuid
from typing import List, Dict, Any
from integrations.bedrock_client import BedrockClient
from utils.file_handler import FileHandler
from utils.logger import get_logger


class TestCaseGenerator:
    """Generate test cases from user stories using LLM"""
    
    def __init__(self):
        self.bedrock_client = BedrockClient()
        self.file_handler = FileHandler()
        self.logger = get_logger(__name__)
    
    def generate_test_cases(self, story: str, execution_id: str = None) -> List[Dict[str, Any]]:
        """
        Generate test cases from user story using Bedrock
        
        Args:
            story: User story text
            execution_id: Optional execution ID (generates new if not provided)
        
        Returns:
            List of test case dictionaries
        """
        if execution_id is None:
            execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        
        self.logger.info(f"Generating test cases for execution {execution_id}")
        
        try:
            # Call Bedrock to generate test cases
            test_cases = self.bedrock_client.generate_test_cases(story)
            
            # Ensure each test case has an ID and properly formatted steps
            for i, test_case in enumerate(test_cases, 1):
                if "id" not in test_case:
                    test_case["id"] = f"TC{i:03d}"
                if "priority" not in test_case:
                    test_case["priority"] = "Medium"
                # Ensure steps are properly formatted with expected_result
                if "steps" in test_case and isinstance(test_case["steps"], list):
                    formatted_steps = []
                    for step in test_case["steps"]:
                        if isinstance(step, str):
                            # If step is just a string, create dict with expected_result
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
            
            # Save test cases
            self.save_test_cases(test_cases, execution_id)
            
            self.logger.info(f"Generated {len(test_cases)} test cases for execution {execution_id}")
            return test_cases
            
        except Exception as e:
            self.logger.error(f"Error generating test cases: {e}")
            raise
    
    def parse_test_cases(self, llm_response: str) -> List[Dict[str, Any]]:
        """
        Parse test cases from LLM response with robust error handling
        
        Args:
            llm_response: Raw LLM response text
        
        Returns:
            List of test case dictionaries
        """
        import json
        import re
        
        try:
            # Clean up response first
            response = llm_response.strip()
            # Remove markdown code blocks if present
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            # Try to parse as JSON
            try:
                data = json.loads(response)
            except json.JSONDecodeError as json_err:
                # Try to fix common JSON issues
                # 1. Try to find JSON object boundaries
                json_match = re.search(r'\{[\s\S]*"test_cases"[\s\S]*\}', response, re.DOTALL)
                if json_match:
                    try:
                        # Try parsing the extracted JSON
                        data = json.loads(json_match.group(0))
                    except:
                        # Try to fix unescaped newlines in strings
                        fixed_json = re.sub(r'(?<!\\)\n(?=")', '\\n', json_match.group(0))
                        try:
                            data = json.loads(fixed_json)
                        except:
                            # Last attempt: try to extract just the test_cases array
                            array_match = re.search(r'"test_cases"\s*:\s*\[[\s\S]*\]', response, re.DOTALL)
                            if array_match:
                                # Wrap in object
                                wrapped = '{' + array_match.group(0) + '}'
                                try:
                                    data = json.loads(wrapped)
                                except:
                                    raise ValueError(f"Failed to parse test cases after multiple attempts. Original error: {json_err}")
                            else:
                                raise ValueError(f"Failed to parse test cases. Could not find JSON structure. Error: {json_err}")
                else:
                    # Try to extract from markdown code block
                    json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
                    if json_match:
                        try:
                            data = json.loads(json_match.group(1))
                        except:
                            raise ValueError(f"Failed to parse test cases from markdown block. Error: {json_err}")
                    else:
                        raise ValueError(f"Failed to parse test cases. Could not find JSON structure. Error: {json_err}")
            
            if isinstance(data, dict) and "test_cases" in data:
                return data["test_cases"]
            elif isinstance(data, list):
                return data
            else:
                raise ValueError("Unexpected JSON structure")
        except Exception as e:
            raise ValueError(f"Could not parse test cases from LLM response: {e}")
    
    def save_test_cases(self, test_cases: List[Dict[str, Any]], execution_id: str) -> str:
        """
        Save test cases to storage
        
        Args:
            test_cases: List of test case dictionaries
            execution_id: Execution identifier
        
        Returns:
            Path to saved file
        """
        file_path = self.file_handler.save_test_cases(execution_id, test_cases)
        self.logger.info(f"Saved test cases to {file_path}")
        return str(file_path)


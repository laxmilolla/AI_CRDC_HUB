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
            
            # Ensure each test case has an ID
            for i, test_case in enumerate(test_cases, 1):
                if "id" not in test_case:
                    test_case["id"] = f"TC{i:03d}"
                if "priority" not in test_case:
                    test_case["priority"] = "Medium"
            
            # Save test cases
            self.save_test_cases(test_cases, execution_id)
            
            self.logger.info(f"Generated {len(test_cases)} test cases for execution {execution_id}")
            return test_cases
            
        except Exception as e:
            self.logger.error(f"Error generating test cases: {e}")
            raise
    
    def parse_test_cases(self, llm_response: str) -> List[Dict[str, Any]]:
        """
        Parse test cases from LLM response
        
        Args:
            llm_response: Raw LLM response text
        
        Returns:
            List of test case dictionaries
        """
        import json
        
        try:
            # Try to parse as JSON
            data = json.loads(llm_response)
            if isinstance(data, dict) and "test_cases" in data:
                return data["test_cases"]
            elif isinstance(data, list):
                return data
            else:
                raise ValueError("Unexpected JSON structure")
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract from markdown
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', llm_response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
                return data.get("test_cases", [])
            raise ValueError("Could not parse test cases from LLM response")
    
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


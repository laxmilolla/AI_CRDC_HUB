"""
Playwright code generation from test cases
"""
from typing import List, Dict, Any
from integrations.bedrock_client import BedrockClient
from utils.file_handler import FileHandler
from utils.logger import get_logger


class CodeGenerator:
    """Generate Playwright test code from test cases"""
    
    def __init__(self):
        self.bedrock_client = BedrockClient()
        self.file_handler = FileHandler()
        self.logger = get_logger(__name__)
    
    def generate_playwright_code(
        self, 
        test_cases: List[Dict[str, Any]], 
        execution_id: str
    ) -> str:
        """
        Generate Playwright code from test cases using Bedrock
        
        Args:
            test_cases: List of selected test case dictionaries
            execution_id: Execution identifier
        
        Returns:
            Playwright JavaScript code
        """
        self.logger.info(f"Generating Playwright code for {len(test_cases)} test cases")
        
        try:
            # Generate code using Bedrock
            playwright_code = self.bedrock_client.generate_playwright_code(test_cases, execution_id)
            
            # Ensure screenshot capture is included
            playwright_code = self.include_screenshot_capture(playwright_code, execution_id)
            
            # Save generated code
            self.save_playwright_code(playwright_code, execution_id)
            
            self.logger.info(f"Generated Playwright code for execution {execution_id}")
            return playwright_code
            
        except Exception as e:
            self.logger.error(f"Error generating Playwright code: {e}")
            raise
    
    def include_screenshot_capture(self, code: str, execution_id: str) -> str:
        """
        Ensure screenshot capture is included after each step
        
        Args:
            code: Playwright code
            execution_id: Execution identifier
        
        Returns:
            Code with screenshot capture added
        """
        # The LLM should already include screenshots based on the prompt
        # This method can be used to verify or add missing screenshots
        
        # Check if screenshots are already included
        if "screenshot" in code.lower() and "execution_" in code:
            return code
        
        # If not, we could add screenshot logic here
        # For now, rely on LLM to include it based on prompt
        self.logger.warning("Screenshot capture may be missing in generated code")
        return code
    
    def save_playwright_code(self, code: str, execution_id: str) -> str:
        """
        Save generated Playwright code
        
        Args:
            code: Playwright JavaScript code
            execution_id: Execution identifier
        
        Returns:
            Path to saved file
        """
        file_path = self.file_handler.save_playwright_code(execution_id, code)
        self.logger.info(f"Saved Playwright code to {file_path}")
        return str(file_path)


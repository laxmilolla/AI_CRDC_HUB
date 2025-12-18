"""
Test execution orchestration and management
"""
import json
import time
from typing import Dict, Any, Optional
from pathlib import Path
from utils.file_handler import FileHandler
from utils.logger import get_logger
from utils.screenshot_handler import ScreenshotHandler


class ExecutionManager:
    """Manage test execution lifecycle"""
    
    def __init__(self):
        self.file_handler = FileHandler()
        self.logger = get_logger(__name__)
        self.executions = {}  # In-memory execution status tracking
    
    def execute_tests(
        self, 
        playwright_code: str, 
        execution_id: str,
        test_cases: list[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute Playwright tests
        
        Note: This will be integrated with MCP Playwright client
        """
        """
        Execute Playwright tests via MCP
        
        Args:
            playwright_code: Playwright JavaScript code
            execution_id: Execution identifier
            test_cases: Optional list of test cases being executed
        
        Returns:
            Execution results dictionary
        """
        self.logger.info(f"Starting test execution: {execution_id}")
        
        # Initialize execution status
        self.executions[execution_id] = {
            "status": "running",
            "progress": 0,
            "started_at": time.time(),
            "completed_at": None,
            "results": []
        }
        
        try:
            # Save execution status
            self._save_execution_status(execution_id)
            
            # Execute via MCP (will be implemented in MCP client)
            # For now, this is a placeholder
            results = {
                "execution_id": execution_id,
                "status": "completed",
                "test_results": [],
                "duration": 0,
                "summary": {
                    "total": 0,
                    "passed": 0,
                    "failed": 0
                }
            }
            
            # Update execution status
            self.executions[execution_id].update({
                "status": "completed",
                "progress": 100,
                "completed_at": time.time(),
                "results": results
            })
            
            # Save results
            self.file_handler.save_results(execution_id, results)
            
            self.logger.info(f"Test execution completed: {execution_id}")
            return results
            
        except Exception as e:
            self.logger.error(f"Error executing tests: {e}")
            self.executions[execution_id].update({
                "status": "failed",
                "error": str(e)
            })
            raise
    
    def monitor_execution(self, execution_id: str) -> Dict[str, Any]:
        """
        Monitor execution progress
        
        Args:
            execution_id: Execution identifier
        
        Returns:
            Execution status dictionary
        """
        if execution_id not in self.executions:
            # Try to load from file
            try:
                results = self.file_handler.load_results(execution_id)
                return {
                    "status": "completed",
                    "progress": 100,
                    "results": results
                }
            except FileNotFoundError:
                return {
                    "status": "not_found",
                    "progress": 0
                }
        
        execution = self.executions[execution_id]
        return {
            "status": execution["status"],
            "progress": execution.get("progress", 0),
            "started_at": execution.get("started_at"),
            "completed_at": execution.get("completed_at"),
            "error": execution.get("error")
        }
    
    def capture_screenshots(
        self, 
        execution_id: str, 
        test_case_id: str, 
        step: Dict[str, Any]
    ) -> str:
        """
        Capture screenshot for a test step
        
        Args:
            execution_id: Execution identifier
            test_case_id: Test case identifier
            step: Step information dictionary
        
        Returns:
            Screenshot file path
        """
        screenshot_handler = ScreenshotHandler(execution_id=execution_id)
        step_number = step.get("step_number", 1)
        step_description = step.get("description", "step")
        
        screenshot_path = screenshot_handler.get_screenshot_path(
            test_case_id, 
            step_number, 
            step_description
        )
        
        return str(screenshot_path)
    
    def handle_execution_errors(self, error: Exception, execution_id: str):
        """
        Handle execution errors
        
        Args:
            error: Exception that occurred
            execution_id: Execution identifier
        """
        self.logger.error(f"Execution error for {execution_id}: {error}")
        
        if execution_id in self.executions:
            self.executions[execution_id].update({
                "status": "failed",
                "error": str(error),
                "completed_at": time.time()
            })
            self._save_execution_status(execution_id)
    
    def _save_execution_status(self, execution_id: str):
        """Save execution status to file"""
        if execution_id in self.executions:
            status_file = Path("data") / "executions" / f"{execution_id}_status.json"
            status_file.parent.mkdir(parents=True, exist_ok=True)
            status_file.write_text(
                json.dumps(self.executions[execution_id], indent=2),
                encoding='utf-8'
            )


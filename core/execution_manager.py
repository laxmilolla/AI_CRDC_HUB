"""
Test execution orchestration and management
"""
import json
import time
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
from utils.file_handler import FileHandler
from utils.logger import get_logger
from utils.screenshot_handler import ScreenshotHandler
from integrations.mcp_client import MCPPlaywrightClient


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
        Execute Playwright tests via MCP
        
        Args:
            playwright_code: Generated Playwright JavaScript code
            execution_id: Execution identifier
            test_cases: List of test cases being executed
        
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
            
            # Execute via MCP Playwright
            # Run async execution
            results = asyncio.run(
                self._execute_with_mcp(playwright_code, execution_id, test_cases)
            )
            
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
                "error": str(e),
                "completed_at": time.time()
            })
            self._save_execution_status(execution_id)
            raise
    
    async def _execute_with_mcp(
        self,
        playwright_code: str,
        execution_id: str,
        test_cases: list[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Execute tests using MCP Playwright client
        
        Args:
            playwright_code: Playwright JavaScript code
            execution_id: Execution identifier
            test_cases: List of test cases
        
        Returns:
            Execution results
        """
        mcp_client = MCPPlaywrightClient()
        screenshot_handler = ScreenshotHandler(execution_id=execution_id)
        
        test_results = []
        start_time = time.time()
        
        try:
            # Connect to MCP with timeout
            self.logger.info("Connecting to MCP Playwright server...")
            try:
                await asyncio.wait_for(mcp_client.connect_mcp_server(), timeout=30.0)
                self.logger.info("Successfully connected to MCP Playwright server")
            except asyncio.TimeoutError:
                raise RuntimeError("MCP connection timeout after 30 seconds")
            
            # Execute each test case
            for idx, test_case in enumerate(test_cases or []):
                test_case_id = test_case.get('id', f'TC{idx+1:03d}')
                self.logger.info(f"Executing test case: {test_case_id}")
                
                # Update progress
                progress = int((idx / len(test_cases)) * 100) if test_cases else 0
                self.executions[execution_id]['progress'] = progress
                self._save_execution_status(execution_id)
                
                # Execute test case steps
                steps = test_case.get('steps', [])
                step_results = []
                test_status = "passed"
                test_error = None
                
                for step_idx, step_desc in enumerate(steps, 1):
                    try:
                        # Execute step via MCP
                        step_result = await mcp_client.execute_step(
                            step_desc,
                            execution_id,
                            test_case_id,
                            step_idx,
                            step_desc
                        )
                        step_results.append(step_result)
                        
                        if step_result.get('status') == 'failed':
                            test_status = "failed"
                            test_error = step_result.get('error')
                            break
                            
                    except Exception as e:
                        self.logger.error(f"Error in step {step_idx}: {e}")
                        step_results.append({
                            "status": "failed",
                            "error": str(e),
                            "step_number": step_idx,
                            "description": step_desc
                        })
                        test_status = "failed"
                        test_error = str(e)
                        break
                
                test_results.append({
                    "test_case_id": test_case_id,
                    "status": test_status,
                    "steps": step_results,
                    "error": test_error,
                    "duration": time.time() - start_time
                })
            
            # Calculate summary
            total = len(test_results)
            passed = sum(1 for r in test_results if r['status'] == 'passed')
            failed = total - passed
            duration = time.time() - start_time
            
            results = {
                "execution_id": execution_id,
                "status": "completed",
                "test_results": test_results,
                "duration": duration,
                "summary": {
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "success_rate": (passed / total * 100) if total > 0 else 0
                }
            }
            
            return results
            
        finally:
            # Close MCP connection
            await mcp_client.close()
    
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


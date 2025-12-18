"""
Result analysis using LLM
"""
import json
from typing import Dict, Any, List
from integrations.bedrock_client import BedrockClient
from utils.file_handler import FileHandler
from utils.screenshot_handler import ScreenshotHandler
from utils.logger import get_logger
from pathlib import Path


class ResultAnalyzer:
    """Analyze test execution results using LLM"""
    
    def __init__(self):
        self.bedrock_client = BedrockClient()
        self.file_handler = FileHandler()
        self.logger = get_logger(__name__)
    
    def analyze_results(
        self, 
        results: Dict[str, Any], 
        execution_id: str
    ) -> Dict[str, Any]:
        """
        Analyze results using Bedrock LLM
        
        Args:
            results: Test execution results dictionary
            execution_id: Execution identifier
        
        Returns:
            Analysis dictionary with insights and recommendations
        """
        self.logger.info(f"Analyzing results for execution {execution_id}")
        
        try:
            # Get screenshot paths
            screenshot_paths = self._get_screenshot_paths(execution_id, results)
            
            # Call Bedrock to analyze results
            analysis = self.bedrock_client.analyze_results(results, screenshot_paths)
            
            # Generate report
            report = self.generate_report(analysis, results, execution_id)
            
            # Save analysis
            self._save_analysis(execution_id, analysis, report)
            
            self.logger.info(f"Analysis completed for execution {execution_id}")
            return {
                "analysis": analysis,
                "report": report
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing results: {e}")
            raise
    
    def generate_report(
        self, 
        analysis: Dict[str, Any], 
        results: Dict[str, Any],
        execution_id: str
    ) -> str:
        """
        Generate HTML report from analysis
        
        Args:
            analysis: LLM analysis dictionary
            results: Test execution results
            execution_id: Execution identifier
        
        Returns:
            HTML report content
        """
        summary = analysis.get("summary", {})
        detailed = analysis.get("detailed_analysis", [])
        insights = analysis.get("overall_insights", "")
        recommendations = analysis.get("recommendations", [])
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Test Execution Report - {execution_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .summary {{ background: #f5f5f5; padding: 20px; border-radius: 5px; }}
        .test-case {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .passed {{ border-left: 5px solid #4CAF50; }}
        .failed {{ border-left: 5px solid #f44336; }}
        .recommendations {{ background: #e3f2fd; padding: 15px; margin: 20px 0; border-radius: 5px; }}
        ul {{ margin: 10px 0; }}
    </style>
</head>
<body>
    <h1>Test Execution Report</h1>
    <p><strong>Execution ID:</strong> {execution_id}</p>
    
    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Total:</strong> {summary.get('total', 0)}</p>
        <p><strong>Passed:</strong> {summary.get('passed', 0)}</p>
        <p><strong>Failed:</strong> {summary.get('failed', 0)}</p>
        <p><strong>Success Rate:</strong> {summary.get('success_rate', 0)}%</p>
        <p><strong>Duration:</strong> {summary.get('duration', 0)}s</p>
    </div>
    
    <h2>Overall Insights</h2>
    <p>{insights}</p>
    
    <h2>Detailed Analysis</h2>
"""
        
        for test_analysis in detailed:
            status = test_analysis.get("status", "unknown")
            status_class = "passed" if status == "passed" else "failed"
            html += f"""
    <div class="test-case {status_class}">
        <h3>{test_analysis.get('test_case_id', 'Unknown')} - {status.upper()}</h3>
        <p>{test_analysis.get('analysis', '')}</p>
"""
            if test_analysis.get("issues"):
                html += "<p><strong>Issues:</strong></p><ul>"
                for issue in test_analysis.get("issues", []):
                    html += f"<li>{issue}</li>"
                html += "</ul>"
            
            if test_analysis.get("recommendations"):
                html += "<p><strong>Recommendations:</strong></p><ul>"
                for rec in test_analysis.get("recommendations", []):
                    html += f"<li>{rec}</li>"
                html += "</ul>"
            
            html += "</div>"
        
        if recommendations:
            html += """
    <div class="recommendations">
        <h2>Recommendations</h2>
        <ul>
"""
            for rec in recommendations:
                html += f"<li>{rec}</li>"
            html += """
        </ul>
    </div>
"""
        
        html += """
</body>
</html>
"""
        
        return html
    
    def identify_failures(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Identify failed tests from results
        
        Args:
            results: Test execution results
        
        Returns:
            List of failed test information
        """
        failures = []
        test_results = results.get("test_results", [])
        
        for test_result in test_results:
            if test_result.get("status") == "failed":
                failures.append({
                    "test_case_id": test_result.get("test_case_id"),
                    "error": test_result.get("error"),
                    "steps": test_result.get("steps", [])
                })
        
        return failures
    
    def suggest_fixes(self, failures: List[Dict[str, Any]]) -> List[str]:
        """
        Get LLM suggestions for fixing failures
        
        Args:
            failures: List of failed test information
        
        Returns:
            List of fix suggestions
        """
        if not failures:
            return []
        
        failures_json = json.dumps(failures, indent=2)
        prompt = f"""Given these test failures, suggest fixes:

{failures_json}

Provide a list of actionable fix suggestions. Return as JSON array of strings."""

        try:
            response = self.bedrock_client.invoke_model(prompt, max_tokens=1000)
            import json
            suggestions = json.loads(response)
            return suggestions if isinstance(suggestions, list) else []
        except Exception as e:
            self.logger.error(f"Error getting fix suggestions: {e}")
            return []
    
    def _get_screenshot_paths(
        self, 
        execution_id: str, 
        results: Dict[str, Any]
    ) -> List[str]:
        """Get all screenshot paths for an execution"""
        screenshot_handler = ScreenshotHandler(execution_id=execution_id)
        paths = screenshot_handler.list_screenshots(execution_id)
        return [str(p) for p in paths]
    
    def _save_analysis(
        self, 
        execution_id: str, 
        analysis: Dict[str, Any],
        report: str
    ):
        """Save analysis and report to files"""
        report_dir = Path("reports") / f"execution_{execution_id}"
        report_dir.mkdir(parents=True, exist_ok=True)
        
        # Save HTML report
        html_file = report_dir / "report.html"
        html_file.write_text(report, encoding='utf-8')
        
        # Save analysis JSON
        json_file = report_dir / "report.json"
        json_file.write_text(
            json.dumps(analysis, indent=2),
            encoding='utf-8'
        )
        
        self.logger.info(f"Saved report to {report_dir}")


"""
Screenshot capture and management
"""
import re
from pathlib import Path
from typing import Optional
from datetime import datetime


class ScreenshotHandler:
    """Handle screenshot capture and organization"""
    
    def __init__(self, base_dir: str = ".", execution_id: str = None):
        self.base_dir = Path(base_dir)
        self.execution_id = execution_id
        self.step_count = {}
    
    def get_screenshot_path(self, test_case_id: str, step_number: int, step_description: str) -> Path:
        """
        Generate screenshot path for a test step
        
        Args:
            test_case_id: Test case identifier (e.g., "TC001")
            step_number: Step number (1-based)
            step_description: Description of the step
        
        Returns:
            Path object for screenshot file
        """
        if not self.execution_id:
            raise ValueError("Execution ID must be set")
        
        # Create safe filename from description
        safe_description = self._sanitize_filename(step_description)
        
        # Format: screenshots/execution_{id}/TC{test_case_id}/step_{number:02d}_{description}.png
        screenshot_dir = (
            self.base_dir / 
            "screenshots" / 
            f"execution_{self.execution_id}" / 
            f"TC{test_case_id}"
        )
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"step_{step_number:02d}_{safe_description}.png"
        return screenshot_dir / filename
    
    def _sanitize_filename(self, filename: str, max_length: int = 50) -> str:
        """
        Sanitize filename by removing/replacing invalid characters
        
        Args:
            filename: Original filename
            max_length: Maximum length for filename
        
        Returns:
            Sanitized filename
        """
        # Replace spaces and special chars with underscores
        sanitized = re.sub(r'[^\w\s-]', '', filename)
        sanitized = re.sub(r'[-\s]+', '_', sanitized)
        sanitized = sanitized.lower()
        
        # Truncate if too long
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized.strip('_')
    
    def get_screenshot_url(self, screenshot_path: Path) -> str:
        """
        Generate web-accessible URL for screenshot
        
        Args:
            screenshot_path: Path to screenshot file
        
        Returns:
            URL string
        """
        # Convert to relative path from base_dir
        relative_path = screenshot_path.relative_to(self.base_dir)
        return f"/api/screenshots/{relative_path.as_posix()}"
    
    def list_screenshots(self, execution_id: str, test_case_id: str = None) -> list[Path]:
        """
        List all screenshots for an execution or specific test case
        
        Args:
            execution_id: Execution identifier
            test_case_id: Optional test case identifier
        
        Returns:
            List of screenshot paths
        """
        base_path = self.base_dir / "screenshots" / f"execution_{execution_id}"
        
        if not base_path.exists():
            return []
        
        if test_case_id:
            test_path = base_path / f"TC{test_case_id}"
            if test_path.exists():
                return sorted(test_path.glob("*.png"))
            return []
        
        # Return all screenshots for execution
        screenshots = []
        for test_dir in base_path.iterdir():
            if test_dir.is_dir():
                screenshots.extend(sorted(test_dir.glob("*.png")))
        
        return sorted(screenshots)
    
    def organize_screenshots(self, execution_id: str):
        """
        Organize screenshots by execution (already organized by structure)
        This method can be used for cleanup or reorganization if needed
        
        Args:
            execution_id: Execution identifier
        """
        # Screenshots are already organized by the directory structure
        # This method can be extended for additional organization logic
        pass


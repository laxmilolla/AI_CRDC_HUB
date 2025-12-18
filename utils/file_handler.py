"""
File operations for stories, test cases, results, etc.
"""
import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime


class FileHandler:
    """Handle file operations for the application"""
    
    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create necessary directories if they don't exist"""
        directories = [
            "data/stories",
            "data/test_cases",
            "data/selections",
            "data/results",
            "generated_tests",
            "screenshots",
            "reports",
            "logs"
        ]
        for dir_path in directories:
            (self.base_dir / dir_path).mkdir(parents=True, exist_ok=True)
    
    def save_story(self, story_id: str, content: str) -> Path:
        """
        Save user story to file
        
        Args:
            story_id: Unique story identifier
            content: Story content
        
        Returns:
            Path to saved file
        """
        file_path = self.base_dir / "data" / "stories" / f"story_{story_id}.txt"
        file_path.write_text(content, encoding='utf-8')
        return file_path
    
    def load_story(self, story_id: str) -> str:
        """Load user story from file"""
        file_path = self.base_dir / "data" / "stories" / f"story_{story_id}.txt"
        if not file_path.exists():
            raise FileNotFoundError(f"Story {story_id} not found")
        return file_path.read_text(encoding='utf-8')
    
    def save_test_cases(self, execution_id: str, test_cases: List[Dict[str, Any]]) -> Path:
        """Save test cases to JSON file"""
        file_path = self.base_dir / "data" / "test_cases" / f"execution_{execution_id}.json"
        data = {
            "execution_id": execution_id,
            "test_cases": test_cases,
            "generated_at": datetime.utcnow().isoformat()
        }
        file_path.write_text(json.dumps(data, indent=2), encoding='utf-8')
        return file_path
    
    def load_test_cases(self, execution_id: str) -> List[Dict[str, Any]]:
        """Load test cases from JSON file"""
        file_path = self.base_dir / "data" / "test_cases" / f"execution_{execution_id}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Test cases for execution {execution_id} not found")
        data = json.loads(file_path.read_text(encoding='utf-8'))
        return data.get("test_cases", [])
    
    def save_selection(self, execution_id: str, selected_ids: List[str]) -> Path:
        """Save selected test case IDs"""
        file_path = self.base_dir / "data" / "selections" / f"execution_{execution_id}.json"
        data = {
            "execution_id": execution_id,
            "selected_ids": selected_ids,
            "selected_at": datetime.utcnow().isoformat()
        }
        file_path.write_text(json.dumps(data, indent=2), encoding='utf-8')
        return file_path
    
    def load_selection(self, execution_id: str) -> List[str]:
        """Load selected test case IDs"""
        file_path = self.base_dir / "data" / "selections" / f"execution_{execution_id}.json"
        if not file_path.exists():
            return []
        data = json.loads(file_path.read_text(encoding='utf-8'))
        return data.get("selected_ids", [])
    
    def save_results(self, execution_id: str, results: Dict[str, Any]) -> Path:
        """Save test execution results"""
        file_path = self.base_dir / "data" / "results" / f"execution_{execution_id}.json"
        results["saved_at"] = datetime.utcnow().isoformat()
        file_path.write_text(json.dumps(results, indent=2), encoding='utf-8')
        return file_path
    
    def load_results(self, execution_id: str) -> Dict[str, Any]:
        """Load test execution results"""
        file_path = self.base_dir / "data" / "results" / f"execution_{execution_id}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Results for execution {execution_id} not found")
        return json.loads(file_path.read_text(encoding='utf-8'))
    
    def save_playwright_code(self, execution_id: str, code: str) -> Path:
        """Save generated Playwright test code"""
        dir_path = self.base_dir / "generated_tests" / f"execution_{execution_id}"
        dir_path.mkdir(parents=True, exist_ok=True)
        file_path = dir_path / "test.spec.js"
        file_path.write_text(code, encoding='utf-8')
        return file_path


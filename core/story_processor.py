"""
User story parsing and validation
"""
import re
from typing import Dict, List, Optional, Any
from utils.validators import validate_story_format
from utils.logger import get_logger

logger = get_logger(__name__)


class StoryProcessor:
    """Process and parse user stories"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def parse_story(self, story_text: str) -> Dict[str, Any]:
        """
        Parse user story and extract key information
        
        Args:
            story_text: User story text
        
        Returns:
            Dictionary with parsed story information
        """
        story_text = story_text.strip()
        
        # Validate story format
        is_valid, error = validate_story_format(story_text)
        if not is_valid:
            raise ValueError(f"Invalid story format: {error}")
        
        parsed = {
            "raw_content": story_text,
            "scenarios": self.extract_scenarios(story_text),
            "user_type": self._extract_user_type(story_text),
            "actions": self._extract_actions(story_text),
            "benefits": self._extract_benefits(story_text),
            "acceptance_criteria": self._extract_acceptance_criteria(story_text)
        }
        
        self.logger.info(f"Parsed story with {len(parsed['scenarios'])} scenarios")
        return parsed
    
    def validate_story(self, story: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate parsed story
        
        Args:
            story: Parsed story dictionary
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not story.get("raw_content"):
            return False, "Story content is missing"
        
        if not story.get("scenarios"):
            return False, "No scenarios found in story"
        
        return True, None
    
    def extract_scenarios(self, story_text: str) -> List[str]:
        """
        Identify test scenarios from user story
        
        Args:
            story_text: User story text
        
        Returns:
            List of scenario descriptions
        """
        scenarios = []
        
        # Look for "As a... I want... So that..." pattern
        user_story_pattern = r'As\s+(?:a|an)\s+([^,]+),\s*I\s+want\s+to\s+([^,]+?)(?:,|\s+so\s+that)'
        matches = re.finditer(user_story_pattern, story_text, re.IGNORECASE | re.DOTALL)
        
        for match in matches:
            user_type = match.group(1).strip()
            action = match.group(2).strip()
            scenarios.append(f"{user_type} wants to {action}")
        
        # Look for numbered scenarios or bullet points
        numbered_pattern = r'(?:\d+\.|[-*])\s*(.+?)(?=\n(?:\d+\.|[-*])|\n\n|$)'
        numbered_matches = re.finditer(numbered_pattern, story_text, re.MULTILINE)
        
        for match in numbered_matches:
            scenario = match.group(1).strip()
            if len(scenario) > 10:  # Filter out very short items
                scenarios.append(scenario)
        
        # Look for "Given-When-Then" format
        gwt_pattern = r'Given\s+(.+?)\s+When\s+(.+?)\s+Then\s+(.+?)(?=\n\n|$)'
        gwt_matches = re.finditer(gwt_pattern, story_text, re.IGNORECASE | re.DOTALL)
        
        for match in gwt_matches:
            given = match.group(1).strip()
            when = match.group(2).strip()
            then = match.group(3).strip()
            scenarios.append(f"Given {given}, when {when}, then {then}")
        
        # If no structured scenarios found, extract sentences as potential scenarios
        if not scenarios:
            sentences = re.split(r'[.!?]\s+', story_text)
            scenarios = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        return scenarios[:10]  # Limit to 10 scenarios
    
    def _extract_user_type(self, story_text: str) -> Optional[str]:
        """Extract user type from story"""
        match = re.search(r'As\s+(?:a|an)\s+([^,]+)', story_text, re.IGNORECASE)
        return match.group(1).strip() if match else None
    
    def _extract_actions(self, story_text: str) -> List[str]:
        """Extract actions from story"""
        actions = []
        # Look for "I want to..." patterns
        action_pattern = r'I\s+want\s+to\s+([^,.!?]+)'
        matches = re.finditer(action_pattern, story_text, re.IGNORECASE)
        actions.extend([m.group(1).strip() for m in matches])
        return actions
    
    def _extract_benefits(self, story_text: str) -> List[str]:
        """Extract benefits from story"""
        benefits = []
        # Look for "So that..." patterns
        benefit_pattern = r'so\s+that\s+([^,.!?]+)'
        matches = re.finditer(benefit_pattern, story_text, re.IGNORECASE)
        benefits.extend([m.group(1).strip() for m in matches])
        return benefits
    
    def _extract_acceptance_criteria(self, story_text: str) -> List[str]:
        """Extract acceptance criteria"""
        criteria = []
        
        # Look for "Acceptance Criteria:" section
        ac_section = re.search(r'Acceptance\s+Criteria:?\s*(.+?)(?=\n\n|$)', story_text, re.IGNORECASE | re.DOTALL)
        if ac_section:
            ac_text = ac_section.group(1)
            # Split by lines or bullets
            criteria = [c.strip() for c in re.split(r'\n[-*•]\s*|\n\d+\.\s*', ac_text) if c.strip()]
        
        return criteria
    
    def extract_expected_results(self, step_description: str) -> Optional[str]:
        """
        Extract expected result/assertion from step description.
        Looks for patterns like:
        - "Verify that..."
        - "Expected: ..."
        - "Should see..."
        - "Assert that..."
        - "Check that..."
        
        Args:
            step_description: Step description text
        
        Returns:
            Expected result string if found, None otherwise
        """
        # Look for explicit verification patterns
        verify_patterns = [
            r'Verify\s+that\s+(.+?)(?:\.|$|,|\n)',
            r'Expected:\s*(.+?)(?:\.|$|,|\n)',
            r'Should\s+see\s+(.+?)(?:\.|$|,|\n)',
            r'Assert\s+that\s+(.+?)(?:\.|$|,|\n)',
            r'Check\s+that\s+(.+?)(?:\.|$|,|\n)',
            r'Ensure\s+that\s+(.+?)(?:\.|$|,|\n)',
            r'Confirm\s+that\s+(.+?)(?:\.|$|,|\n)',
        ]
        
        for pattern in verify_patterns:
            match = re.search(pattern, step_description, re.IGNORECASE)
            if match:
                result = match.group(1).strip()
                # Remove trailing punctuation
                result = re.sub(r'[.,;:]+$', '', result)
                if len(result) > 5:  # Filter out very short matches
                    return result
        
        # Look for "Expected Result:" section in multi-line steps
        expected_section = re.search(r'Expected\s+Result:?\s*(.+?)(?=\n|$)', step_description, re.IGNORECASE)
        if expected_section:
            result = expected_section.group(1).strip()
            if len(result) > 5:
                return result
        
        return None


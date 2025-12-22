"""
Selector Registry - Store and retrieve known selectors for websites/pages
This registry learns from successful test executions and provides fast selector lookup
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from urllib.parse import urlparse
import logging


class SelectorRegistry:
    """
    Registry for storing and retrieving DOM selectors for websites/pages.
    Selectors are organized by domain and page context, allowing fast lookup
    without LLM interpretation on subsequent test runs.
    """
    
    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.selectors_dir = self.base_dir / "data" / "selectors"
        self.selectors_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        self._cache = {}  # In-memory cache for loaded registries
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path
            # Remove www. prefix
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            # Fallback: extract domain manually
            match = re.search(r'https?://([^/]+)', url)
            if match:
                domain = match.group(1)
                if domain.startswith("www."):
                    domain = domain[4:]
                return domain
            return "unknown"
    
    def _get_registry_file(self, domain: str) -> Path:
        """Get path to registry file for a domain"""
        # Sanitize domain for filename
        safe_domain = re.sub(r'[^\w\-.]', '_', domain)
        return self.selectors_dir / f"{safe_domain}.json"
    
    def _load_registry(self, domain: str) -> Dict[str, Any]:
        """Load registry for a domain (with caching)"""
        if domain in self._cache:
            return self._cache[domain]
        
        registry_file = self._get_registry_file(domain)
        if registry_file.exists():
            try:
                with open(registry_file, 'r', encoding='utf-8') as f:
                    registry = json.load(f)
                    self._cache[domain] = registry
                    return registry
            except Exception as e:
                self.logger.warning(f"Failed to load selector registry for {domain}: {e}")
        
        # Return empty registry structure
        return {
            "domain": domain,
            "pages": {},
            "created_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def _save_registry(self, domain: str, registry: Dict[str, Any]):
        """Save registry to file"""
        registry["last_updated"] = datetime.utcnow().isoformat()
        registry_file = self._get_registry_file(domain)
        
        try:
            with open(registry_file, 'w', encoding='utf-8') as f:
                json.dump(registry, f, indent=2, ensure_ascii=False)
            self._cache[domain] = registry
            self.logger.info(f"Saved selector registry for {domain}")
        except Exception as e:
            self.logger.error(f"Failed to save selector registry for {domain}: {e}")
    
    def _match_url_pattern(self, url: str, patterns: List[str]) -> bool:
        """Check if URL matches any of the patterns"""
        for pattern in patterns:
            if pattern in url or re.search(pattern, url, re.IGNORECASE):
                return True
        return False
    
    def _find_page_context(self, registry: Dict[str, Any], url: str, step_description: str) -> Optional[str]:
        """Find matching page context in registry"""
        pages = registry.get("pages", {})
        
        # Try to match by URL pattern first
        for page_name, page_data in pages.items():
            url_patterns = page_data.get("url_patterns", [])
            if self._match_url_pattern(url, url_patterns):
                self.logger.debug(f"Matched page context '{page_name}' by URL pattern")
                return page_name
        
        # If no URL match, try to match by domain (fallback for main pages)
        domain = self._extract_domain(url)
        for page_name, page_data in pages.items():
            url_patterns = page_data.get("url_patterns", [])
            # Check if any pattern contains the domain
            for pattern in url_patterns:
                if domain in pattern or pattern in domain:
                    self.logger.debug(f"Matched page context '{page_name}' by domain")
                    return page_name
        
        # Try to match by step description keywords
        step_lower = step_description.lower()
        for page_name, page_data in pages.items():
            keywords = page_data.get("keywords", [])
            for keyword in keywords:
                if keyword.lower() in step_lower:
                    self.logger.debug(f"Matched page context '{page_name}' by keyword")
                    return page_name
        
        # If only one page exists, use it (common case for single-page sites)
        if len(pages) == 1:
            page_name = list(pages.keys())[0]
            self.logger.debug(f"Using only page context '{page_name}' (single page)")
            return page_name
        
        self.logger.debug(f"No page context match found for URL: {url}")
        return None
    
    def lookup_selector(
        self,
        url: str,
        step_description: str,
        element_type: str,
        action: str = "fill"
    ) -> Optional[str]:
        """
        Look up selector from registry
        
        Args:
            url: Current page URL
            step_description: Step description (for context matching)
            element_type: Type of element (e.g., "username", "password", "submit", "totp")
            action: Action type (e.g., "fill", "click")
        
        Returns:
            Selector string if found, None otherwise
        """
        domain = self._extract_domain(url)
        registry = self._load_registry(domain)
        
        # Find matching page context
        page_context = self._find_page_context(registry, url, step_description)
        if not page_context:
            self.logger.debug(f"Registry lookup: No page context found for URL: {url}, step: {step_description[:50]}")
            return None
        
        self.logger.debug(f"Registry lookup: Found page context '{page_context}' for element_type '{element_type}'")
        
        pages = registry.get("pages", {})
        page_data = pages.get(page_context, {})
        selectors = page_data.get("selectors", {})
        
        # Look for element type in selectors
        element_data = selectors.get(element_type)
        if element_data:
            primary = element_data.get("primary")
            if primary:
                self.logger.info(f"Found selector from registry: {element_type} -> {primary} (domain: {domain}, page: {page_context})")
                return primary
        
        return None
    
    def save_selector(
        self,
        url: str,
        step_description: str,
        element_type: str,
        selector: str,
        page_context: Optional[str] = None,
        alternatives: Optional[List[str]] = None,
        action: str = "fill"
    ):
        """
        Save selector to registry after successful step execution
        
        Args:
            url: Current page URL
            step_description: Step description (for context)
            element_type: Type of element (e.g., "username", "password")
            selector: The selector that worked
            page_context: Optional page context name (auto-detected if not provided)
            alternatives: Optional list of alternative selectors
            action: Action type (e.g., "fill", "click")
        """
        domain = self._extract_domain(url)
        registry = self._load_registry(domain)
        
        # Auto-detect page context if not provided
        if not page_context:
            page_context = self._find_page_context(registry, url, step_description)
            if not page_context:
                # Create new page context based on URL and step description
                page_context = self._generate_page_context(url, step_description)
        
        # Initialize pages structure if needed
        if "pages" not in registry:
            registry["pages"] = {}
        pages = registry["pages"]
        
        # Initialize page data if needed
        if page_context not in pages:
            pages[page_context] = {
                "url_patterns": [self._extract_url_pattern(url)],
                "keywords": self._extract_keywords(step_description),
                "selectors": {}
            }
        else:
            # Add URL pattern if not already present
            url_pattern = self._extract_url_pattern(url)
            if url_pattern not in pages[page_context].get("url_patterns", []):
                pages[page_context].setdefault("url_patterns", []).append(url_pattern)
        
        page_data = pages[page_context]
        selectors = page_data.setdefault("selectors", {})
        
        # Update or create selector entry
        if element_type in selectors:
            # Update existing selector
            element_data = selectors[element_type]
            if element_data.get("primary") == selector:
                # Same selector - increment verified count
                element_data["verified_count"] = element_data.get("verified_count", 0) + 1
            else:
                # Different selector - add as alternative and update primary
                if alternatives is None:
                    alternatives = []
                if element_data.get("primary") not in alternatives:
                    alternatives.append(element_data.get("primary"))
                element_data["primary"] = selector
                element_data["alternatives"] = alternatives
                element_data["verified_count"] = 1
            element_data["last_success"] = datetime.utcnow().isoformat()
        else:
            # Create new selector entry
            selectors[element_type] = {
                "primary": selector,
                "alternatives": alternatives or [],
                "verified_count": 1,
                "last_success": datetime.utcnow().isoformat(),
                "context": step_description[:100]  # Store context for reference
            }
        
        # Save registry
        self._save_registry(domain, registry)
        self.logger.info(f"Saved selector to registry: {element_type} -> {selector} (domain: {domain}, page: {page_context})")
    
    def _generate_page_context(self, url: str, step_description: str) -> str:
        """Generate a page context name from URL and step description"""
        # Extract meaningful parts from URL
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split('/') if p]
        
        # Use last meaningful path part or domain
        if path_parts:
            context = path_parts[-1].replace('-', '_').replace('.', '_')
        else:
            context = parsed.netloc.split('.')[0] if parsed.netloc else "page"
        
        # Add step description keywords
        step_lower = step_description.lower()
        if "login" in step_lower:
            context = "login_form"
        elif "form" in step_lower:
            context = "form"
        elif "dashboard" in step_lower:
            context = "dashboard"
        
        return context
    
    def _extract_url_pattern(self, url: str) -> str:
        """Extract a URL pattern for matching"""
        parsed = urlparse(url)
        # Use domain + first path segment
        pattern = parsed.netloc
        if parsed.path:
            path_parts = parsed.path.split('/')
            if len(path_parts) > 1 and path_parts[1]:
                pattern += "/" + path_parts[1]
        return pattern
    
    def _extract_keywords(self, step_description: str) -> List[str]:
        """Extract keywords from step description for matching"""
        keywords = []
        step_lower = step_description.lower()
        
        # Common keywords
        if "login" in step_lower:
            keywords.append("login")
        if "form" in step_lower:
            keywords.append("form")
        if "username" in step_lower or "email" in step_lower:
            keywords.append("username")
        if "password" in step_lower:
            keywords.append("password")
        if "submit" in step_lower:
            keywords.append("submit")
        if "totp" in step_lower or "2fa" in step_lower or "one-time" in step_lower:
            keywords.append("totp")
        
        return keywords
    
    def get_element_type_from_step(self, step_description: str, action: str) -> Optional[str]:
        """
        Infer element type from step description
        
        Args:
            step_description: Step description
            action: Action type (fill, click, etc.)
        
        Returns:
            Element type string or None
        """
        step_lower = step_description.lower()
        
        if action == "fill":
            if "username" in step_lower or "email" in step_lower:
                return "username"
            elif "password" in step_lower:
                return "password"
            elif "totp" in step_lower or "2fa" in step_lower or "two-factor" in step_lower or "authenticator" in step_lower:
                return "totp_code"
            elif "one-time" in step_lower or ("code" in step_lower and ("one-time" in step_lower or "security" in step_lower)):
                return "totp_code"
            elif "code" in step_lower:
                return "code"
        elif action == "click":
            if "submit" in step_lower:
                return "submit"
            elif "login" in step_lower or "log in" in step_lower:
                return "login_button"
            elif "continue" in step_lower:
                return "continue_button"
        
        return None


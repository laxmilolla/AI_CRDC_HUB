#!/usr/bin/env python3
"""
Validation script to check if the AI_CRDC_HUB setup is correct
"""
import sys
from pathlib import Path

def check_file_exists(filepath: str, description: str) -> bool:
    """Check if a file exists"""
    path = Path(filepath)
    exists = path.exists()
    status = "✓" if exists else "✗"
    print(f"{status} {description}: {filepath}")
    return exists

def check_directory_exists(dirpath: str, description: str) -> bool:
    """Check if a directory exists"""
    path = Path(dirpath)
    exists = path.exists() and path.is_dir()
    status = "✓" if exists else "✗"
    print(f"{status} {description}: {dirpath}")
    return exists

def check_import(module: str, description: str) -> bool:
    """Check if a Python module can be imported"""
    try:
        __import__(module)
        print(f"✓ {description}: {module}")
        return True
    except ImportError as e:
        print(f"✗ {description}: {module} - {e}")
        return False

def main():
    """Run validation checks"""
    print("=" * 60)
    print("AI_CRDC_HUB Setup Validation")
    print("=" * 60)
    print()
    
    errors = []
    
    # Check project structure
    print("Checking project structure...")
    print("-" * 60)
    
    required_dirs = [
        ("api", "API package directory"),
        ("core", "Core package directory"),
        ("integrations", "Integrations package directory"),
        ("utils", "Utils package directory"),
        ("templates", "Templates directory"),
        ("static/css", "CSS directory"),
        ("static/js", "JavaScript directory"),
        ("data", "Data directory"),
        ("data/stories", "Stories data directory"),
        ("data/test_cases", "Test cases data directory"),
        ("data/executions", "Executions data directory"),
        ("screenshots", "Screenshots directory"),
        ("reports", "Reports directory"),
        ("generated_tests", "Generated tests directory"),
    ]
    
    for dirpath, desc in required_dirs:
        if not check_directory_exists(dirpath, desc):
            errors.append(f"Missing directory: {dirpath}")
    
    print()
    
    # Check required files
    print("Checking required files...")
    print("-" * 60)
    
    required_files = [
        ("app.py", "Main Flask application"),
        ("requirements.txt", "Python dependencies"),
        (".env.example", "Environment variables example"),
        (".gitignore", "Git ignore file"),
        ("README.md", "README documentation"),
        ("generateOTP.py", "TOTP generator script"),
        ("api/stories.py", "Stories API"),
        ("api/test_cases.py", "Test cases API"),
        ("api/executions.py", "Executions API"),
        ("api/screenshots.py", "Screenshots API"),
        ("api/reports.py", "Reports API"),
        ("core/story_processor.py", "Story processor"),
        ("core/test_case_generator.py", "Test case generator"),
        ("core/code_generator.py", "Code generator"),
        ("core/execution_manager.py", "Execution manager"),
        ("core/result_analyzer.py", "Result analyzer"),
        ("integrations/bedrock_client.py", "Bedrock client"),
        ("integrations/mcp_client.py", "MCP client"),
        ("utils/logger.py", "Logger utility"),
        ("utils/file_handler.py", "File handler utility"),
        ("utils/validators.py", "Validators utility"),
        ("utils/screenshot_handler.py", "Screenshot handler utility"),
        ("utils/otp_helper.py", "OTP helper utility"),
        ("templates/base.html", "Base HTML template"),
        ("templates/upload_story.html", "Upload story template"),
        ("templates/test_cases.html", "Test cases template"),
        ("templates/progress.html", "Progress template"),
        ("templates/results.html", "Results template"),
        ("static/css/style.css", "CSS stylesheet"),
        ("static/js/app.js", "JavaScript file"),
    ]
    
    for filepath, desc in required_files:
        if not check_file_exists(filepath, desc):
            errors.append(f"Missing file: {filepath}")
    
    print()
    
    # Check Python imports
    print("Checking Python dependencies...")
    print("-" * 60)
    
    required_modules = [
        ("flask", "Flask web framework"),
        ("boto3", "AWS SDK"),
        ("playwright", "Playwright automation"),
        ("pyotp", "TOTP library"),
        ("pandas", "Data processing"),
    ]
    
    missing_modules = []
    for module, desc in required_modules:
        if not check_import(module, desc):
            missing_modules.append(module)
    
    if missing_modules:
        print()
        print("⚠ Missing Python modules (install with: pip install -r requirements.txt)")
        # Don't add to errors - these are expected if dependencies aren't installed yet
    
    print()
    
    # Check environment file
    print("Checking environment configuration...")
    print("-" * 60)
    
    env_example = Path(".env.example")
    env_file = Path(".env")
    
    if env_example.exists():
        print("✓ .env.example exists")
    else:
        errors.append("Missing .env.example file")
    
    if env_file.exists():
        print("✓ .env file exists (make sure it's configured)")
    else:
        print("⚠ .env file not found (create from .env.example)")
    
    print()
    
    # Summary
    print("=" * 60)
    if errors:
        print(f"❌ Validation failed with {len(errors)} error(s):")
        for error in errors:
            print(f"  - {error}")
        print()
        print("Please fix the errors above before proceeding.")
        return 1
    else:
        print("✓ All checks passed! Setup looks good.")
        print()
        print("Next steps:")
        print("1. Copy .env.example to .env and configure it")
        print("2. Install dependencies: pip install -r requirements.txt")
        print("3. Install Playwright browsers: npx playwright install")
        print("4. Run the application: python app.py")
        return 0

if __name__ == "__main__":
    sys.exit(main())


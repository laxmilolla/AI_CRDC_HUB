---
name: AI Test Automation Implementation
overview: Step-by-step implementation plan for AI-powered test automation system with LLM-driven test generation, web UI for test selection, MCP Playwright execution, screenshot capture, and result analysis.
todos:
  - id: setup-project-structure
    content: Create complete project directory structure (api/, core/, integrations/, utils/, templates/, static/, data/, etc.) with all subdirectories
    status: pending
  - id: setup-config-files
    content: Create requirements.txt, .env.example, .gitignore, and README.md with initial configuration
    status: pending
    dependencies:
      - setup-project-structure
  - id: implement-logging
    content: Create utils/logger.py with centralized logging, log rotation, and log level configuration
    status: pending
    dependencies:
      - setup-project-structure
  - id: implement-utilities
    content: Create utils/file_handler.py, utils/validators.py, and utils/screenshot_handler.py for core utility functions
    status: pending
    dependencies:
      - setup-project-structure
      - implement-logging
  - id: implement-otp-generator
    content: Create generateOTP.py script for TOTP generation for application under test 2FA login. Add pyotp to requirements.txt. Script should accept secret key as argument and output OTP code. Create utils/otp_helper.py to call the script during test execution.
    status: pending
    dependencies:
      - setup-config-files
  - id: integrate-otp-into-code-generation
    content: Update core/code_generator.py to include 2FA handling in login flows. When generating Playwright code for login steps, include TOTP generation and input. Add TOTP secret key configuration to .env.example.
    status: pending
    dependencies:
      - implement-otp-generator
      - implement-code-generator
  - id: implement-bedrock-client
    content: Create integrations/bedrock_client.py with AWS Bedrock API client, retry logic, and prompt templates
    status: pending
    dependencies:
      - setup-config-files
  - id: implement-story-processor
    content: Create core/story_processor.py to parse, validate, and extract scenarios from user stories
    status: pending
    dependencies:
      - implement-utilities
  - id: implement-test-case-generator
    content: Create core/test_case_generator.py to generate test cases using Bedrock API and save to storage
    status: pending
    dependencies:
      - implement-bedrock-client
      - implement-story-processor
  - id: implement-code-generator
    content: Create core/code_generator.py to generate Playwright code with screenshot capture from test cases
    status: pending
    dependencies:
      - implement-bedrock-client
      - implement-test-case-generator
  - id: implement-execution-manager
    content: Create core/execution_manager.py to orchestrate test execution, monitor progress, and handle errors
    status: pending
    dependencies:
      - implement-code-generator
  - id: implement-result-analyzer
    content: Create core/result_analyzer.py to analyze results using LLM and generate HTML/text reports
    status: pending
    dependencies:
      - implement-bedrock-client
      - implement-execution-manager
  - id: setup-mcp-server
    content: Set up MCP Playwright server with browser control functions (navigate, click, fill, screenshot, etc.)
    status: pending
    dependencies:
      - implement-utilities
  - id: implement-mcp-client
    content: Create integrations/mcp_client.py to connect to MCP server and execute Playwright steps
    status: pending
    dependencies:
      - setup-mcp-server
      - implement-screenshot-handler
  - id: integrate-screenshots
    content: Integrate screenshot capture into execution flow with automatic saving after each step
    status: pending
    dependencies:
      - implement-mcp-client
      - implement-execution-manager
  - id: setup-flask-app
    content: Create app.py with Flask/FastAPI initialization, CORS, static files, templates, and error handlers
    status: pending
    dependencies:
      - setup-project-structure
  - id: implement-story-api
    content: Create api/stories.py with POST /api/stories, GET /api/stories/:id, and GET /api/stories endpoints
    status: pending
    dependencies:
      - setup-flask-app
      - implement-story-processor
  - id: implement-test-case-api
    content: Create api/test_cases.py with test case generation and selection endpoints
    status: pending
    dependencies:
      - setup-flask-app
      - implement-test-case-generator
  - id: implement-execution-api
    content: Create api/executions.py with execution start, status, and results endpoints
    status: pending
    dependencies:
      - setup-flask-app
      - implement-execution-manager
  - id: implement-screenshot-report-api
    content: Create api/screenshots.py and api/reports.py with screenshot serving and report download endpoints
    status: pending
    dependencies:
      - setup-flask-app
      - integrate-screenshots
      - implement-result-analyzer
  - id: create-base-ui
    content: Create templates/base.html, static/css/style.css, and static/js/app.js with navigation and styling
    status: pending
    dependencies:
      - setup-flask-app
  - id: create-upload-page
    content: Create templates/upload_story.html with file upload, text area, and form submission functionality
    status: pending
    dependencies:
      - create-base-ui
      - implement-story-api
  - id: create-test-case-selection-page
    content: Create templates/test_cases.html with test case cards, checkboxes, selection controls, and run button
    status: pending
    dependencies:
      - create-base-ui
      - implement-test-case-api
  - id: create-progress-page
    content: Create templates/progress.html with progress bars, live updates, and execution status display
    status: pending
    dependencies:
      - create-base-ui
      - implement-execution-api
  - id: create-results-page
    content: Create templates/results.html with test results, screenshot gallery, LLM analysis, and download buttons
    status: pending
    dependencies:
      - create-base-ui
      - implement-screenshot-report-api
  - id: integrate-end-to-end
    content: Connect all components, register API routes in app.py, and test complete user journey
    status: pending
    dependencies:
      - create-results-page
      - implement-screenshot-report-api
  - id: enhance-error-handling
    content: Add comprehensive error handling in all API endpoints, Bedrock calls, and Playwright execution
    status: pending
    dependencies:
      - integrate-end-to-end
  - id: create-tests
    content: Create unit tests, integration tests, and end-to-end tests for all components
    status: pending
    dependencies:
      - enhance-error-handling
  - id: setup-ec2-infrastructure
    content: Create EC2 instance (t3.large recommended): Ubuntu 22.04, configure security groups (SSH, HTTP, HTTPS), attach IAM role with Bedrock permissions, set up SSH access. Document instance details and connection info.
    status: pending
  - id: create-deployment-scripts
    content: Create deployment/install_dependencies.sh and deployment/app.service for EC2 deployment
    status: pending
    dependencies:
      - setup-ec2-infrastructure
  - id: complete-documentation
    content: Update README.md with setup instructions, API documentation, deployment guide, and troubleshooting
    status: pending
    dependencies:
      - create-deployment-scripts
  - id: final-configuration
    content: Finalize .env.example, verify all configurations, test locally, and prepare EC2 deployment checklist
    status: pending
    dependencies:
      - complete-documentation
      - create-tests
---

# Step-by-Step Implementation Plan: AI-Powered Test Automation System

## Phase 1: Project Foundation (Steps 1-5)

### Step 1: Project Structure Setup

Create the base project structure with all necessary directories:

- Create root directory structure: `api/`, `core/`, `integrations/`, `utils/`, `templates/`, `static/`, `data/`, `generated_tests/`, `screenshots/`, `reports/`, `logs/`, `deployment/`
- Create `__init__.py` files in Python packages
- Create subdirectories: `data/stories/`, `data/test_cases/`, `data/selections/`, `data/results/`
- Create `static/css/`, `static/js/`, `static/images/`
- Create `templates/` for HTML files

**Files to create:**

- Directory structure as per [Design_AI_CRDC.md](Design_AI_CRDC.md) Section 14

### Step 2: Configuration Files

Set up configuration and dependency management:

- Create `requirements.txt` with Python dependencies (Flask/FastAPI, boto3, playwright, python-dotenv, pyotp, etc.)
- Create `.env.example` template with AWS credentials placeholders
- Create `.gitignore` for Python, Node.js, and environment files
- Create `README.md` with setup instructions

**Files to create:**

- `requirements.txt` (include pyotp for TOTP generation)
- `.env.example`
- `.gitignore`
- `README.md`

### Step 3: Logging Infrastructure

Implement centralized logging system:

- Create `utils/logger.py` with logging configuration
- Set up log rotation (daily, keep 30 days)
- Create log directories: `logs/`
- Implement log levels: DEBUG, INFO, WARNING, ERROR

**Files to create:**

- `utils/logger.py`
- `utils/__init__.py`

### Step 4: Utility Functions

Create core utility modules:

- Create `utils/file_handler.py` for file operations (read/write stories, test cases, results)
- Create `utils/validators.py` for input validation (story format, file uploads, path validation)
- Create `utils/screenshot_handler.py` for screenshot path generation and organization

**Files to create:**

- `utils/file_handler.py`
- `utils/validators.py`
- `utils/screenshot_handler.py`

### Step 4a: TOTP Generator Utility

Create TOTP (Time-based One-Time Password) generator script for application under test 2FA authentication:

- Create `generateOTP.py` in project root with shebang `#!/usr/bin/env python3`
- Implement script that accepts secret key as command-line argument
- Use `pyotp` library to generate TOTP codes
- Output only the OTP code (no extra text)
- Add error handling for missing arguments and generation errors
- Add `pyotp` to `requirements.txt`
- Make script executable: `chmod +x generateOTP.py`
- Create `utils/otp_helper.py` with function to call the script and retrieve OTP programmatically
- Add `TOTP_SECRET_KEY` to `.env.example` for storing the 2FA secret

**Usage:** `python3 generateOTP.py <your_secret_key>`

**Files to create:**

- `generateOTP.py`
- `utils/otp_helper.py`

**Files to modify:**

- `requirements.txt` (add pyotp dependency)
- `.env.example` (add TOTP_SECRET_KEY)

### Step 5: AWS Bedrock Integration

Implement AWS Bedrock client for LLM interactions:

- Create `integrations/bedrock_client.py` with boto3 Bedrock client
- Implement `invoke_model()` method with retry logic and error handling
- Add configuration for region, model ID (Claude 3 Sonnet)
- Implement token limit management
- Create prompt templates for: test case generation, code generation, result analysis

**Files to create:**

- `integrations/bedrock_client.py`
- `integrations/__init__.py`

## Phase 2: Core Business Logic (Steps 6-10)

### Step 6: Story Processor

Implement user story parsing and validation:

- Create `core/story_processor.py`
- Implement `parse_story(story_text)` to extract key information
- Implement `validate_story(story)` for format validation
- Implement `extract_scenarios(story)` to identify test scenarios
- Save stories to `data/stories/story_{id}.txt`

**Files to create:**

- `core/story_processor.py`
- `core/__init__.py`

### Step 7: Test Case Generator

Implement LLM-driven test case generation:

- Create `core/test_case_generator.py`
- Implement `generate_test_cases(story)` calling Bedrock API
- Implement `parse_test_cases(llm_response)` to parse JSON response
- Implement `save_test_cases(test_cases, execution_id)` to save to `data/test_cases/`
- Handle LLM response parsing and error cases

**Files to create:**

- `core/test_case_generator.py`

### Step 8: Playwright Code Generator

Implement LLM-driven Playwright code generation:

- Create `core/code_generator.py`
- Implement `generate_playwright_code(test_cases, execution_id)` calling Bedrock
- Implement `include_screenshot_capture(code)` to add screenshot steps after each action
- Implement `save_playwright_code(code, execution_id)` to save to `generated_tests/{execution_id}/test.spec.js`
- Ensure generated code follows Playwright best practices

**Files to create:**

- `core/code_generator.py`

### Step 8a: Integrate 2FA/TOTP into Code Generation

Integrate TOTP generation for 2FA login handling:

- Update `core/code_generator.py` to include `include_2fa_handling(code)` function
- When generating code for login scenarios, automatically include:
- Username/password input
- TOTP code generation using `utils/otp_helper.py` (calls `generateOTP.py`)
- TOTP code input in 2FA field
- Screenshot after each login step (username, password, 2FA, success)
- Update LLM prompt template in `integrations/bedrock_client.py` to include 2FA handling instructions
- Ensure generated Playwright code can execute Python subprocess to get TOTP code
- Add environment variable `TOTP_SECRET_KEY` usage in generated code

**Files to modify:**

- `core/code_generator.py`
- `integrations/bedrock_client.py` (update prompt template for code generation)

### Step 9: Execution Manager

Implement test execution orchestration:

- Create `core/execution_manager.py`
- Implement `execute_tests(playwright_code, execution_id)` to coordinate execution
- Implement `monitor_execution(execution_id)` to track progress
- Implement `handle_execution_errors(error)` for error handling
- Create execution status tracking (running, completed, failed)

**Files to create:**

- `core/execution_manager.py`

### Step 10: Result Analyzer

Implement LLM-driven result analysis:

- Create `core/result_analyzer.py`
- Implement `analyze_results(results, execution_id)` calling Bedrock API
- Implement `generate_report(analysis, results)` to create HTML/text reports
- Implement `identify_failures(results)` to find failed tests
- Save reports to `reports/{execution_id}/report.html` and `report.json`

**Files to create:**

- `core/result_analyzer.py`

## Phase 3: MCP Playwright Integration (Steps 11-13)

### Step 11: MCP Playwright Server

Set up MCP Playwright server for browser control:

- Create `integrations/mcp_server.py` or configure MCP Playwright server
- Implement browser control functions: navigate, click, fill, screenshot, get_text, wait_for
- Set up MCP server connection and initialization
- Handle browser lifecycle (launch, close)

**Files to create:**

- `integrations/mcp_server.py` (or MCP configuration)

### Step 12: MCP Client

Implement MCP client for Playwright control:

- Create `integrations/mcp_client.py`
- Implement `connect_mcp_server()` for connection
- Implement `execute_step(step_code)` for single step execution
- Implement `take_screenshot(path)` for screenshot capture
- Implement `get_dom()` and `navigate(url)` methods
- Integrate with screenshot handler for automatic screenshot saving

**Files to create:**

- `integrations/mcp_client.py`

### Step 13: Screenshot Integration

Integrate screenshot capture into execution flow:

- Update `core/execution_manager.py` to call screenshot handler after each step
- Update `utils/screenshot_handler.py` to work with MCP client
- Implement automatic screenshot naming: `step_{number:02d}_{description}.png`
- Organize screenshots by execution: `screenshots/execution_{id}/TC{test_case_id}/`
- Ensure screenshots are captured after every test step

**Files to modify:**

- `core/execution_manager.py`
- `utils/screenshot_handler.py`

## Phase 4: Backend API (Steps 14-18)

### Step 14: Flask/FastAPI Application Setup

Create main application file:

- Create `app.py` with Flask or FastAPI initialization
- Set up CORS if needed
- Configure static files and templates
- Set up error handlers
- Initialize logging

**Files to create:**

- `app.py`

### Step 15: Story API Endpoints

Implement story management endpoints:

- Create `api/stories.py`
- Implement `POST /api/stories` for story upload (file or text)
- Implement `GET /api/stories/:story_id` to retrieve story
- Implement `GET /api/stories` to list all stories
- Integrate with `core/story_processor.py`

**Files to create:**

- `api/stories.py`
- `api/__init__.py`

### Step 16: Test Case API Endpoints

Implement test case management endpoints:

- Create `api/test_cases.py`
- Implement `POST /api/stories/:story_id/generate-test-cases` to trigger generation
- Implement `GET /api/test-cases/:execution_id` to retrieve test cases
- Implement `POST /api/test-cases/select` to save user selections
- Integrate with `core/test_case_generator.py`

**Files to create:**

- `api/test_cases.py`

### Step 17: Execution API Endpoints

Implement test execution endpoints:

- Create `api/executions.py`
- Implement `POST /api/executions` to start execution
- Implement `GET /api/executions/:execution_id/status` for progress tracking
- Implement `GET /api/executions/:execution_id/results` to get results
- Integrate with `core/execution_manager.py` and MCP client

**Files to create:**

- `api/executions.py`

### Step 18: Screenshot and Report API Endpoints

Implement screenshot and report endpoints:

- Create `api/screenshots.py` and `api/reports.py`
- Implement `GET /api/screenshots/:execution_id/:test_case_id` to list screenshots
- Implement `GET /api/screenshots/:execution_id/:test_case_id/:step_number` to serve image
- Implement `GET /api/screenshots/:execution_id/download` for ZIP download
- Implement `GET /api/reports/:execution_id` to get report
- Implement `GET /api/reports/:execution_id/download` for report download

**Files to create:**

- `api/screenshots.py`
- `api/reports.py`

## Phase 5: Frontend UI (Steps 19-23)

### Step 19: Base Template and Styling

Create base HTML template and CSS:

- Create `templates/base.html` with navigation and layout
- Create `static/css/style.css` with modern, responsive styling
- Set up JavaScript foundation in `static/js/app.js`
- Implement loading indicators and error message displays

**Files to create:**

- `templates/base.html`
- `static/css/style.css`
- `static/js/app.js`

### Step 20: Upload Story Page

Create story upload interface:

- Create `templates/upload_story.html`
- Implement file upload input and text area for pasting
- Add "Generate Test Cases" button
- Implement form submission with loading state
- Add error handling and success messages
- Redirect to test cases page after successful generation

**Files to create:**

- `templates/upload_story.html`

### Step 21: Test Cases Selection Page

Create test case selection interface:

- Create `templates/test_cases.html`
- Display test cases as cards with checkboxes
- Show test case details: ID, name, description, steps, priority
- Implement "Select All" / "Deselect All" functionality
- Add "Run Selected Tests" button
- Implement search/filter functionality (optional)
- Connect to API for test case retrieval and selection

**Files to create:**

- `templates/test_cases.html`

### Step 22: Execution Progress Page

Create real-time progress display:

- Create `templates/progress.html`
- Display overall progress bar
- Show individual test progress with step indicators
- Implement auto-refresh for live updates
- Display live logs/console output
- Add "Cancel Execution" button (optional)
- Poll `/api/executions/:id/status` endpoint

**Files to create:**

- `templates/progress.html`

### Step 23: Results and Report Page

Create results display with screenshots:

- Create `templates/results.html`
- Display test summary (total, passed, failed)
- Show detailed results per test case with step-by-step breakdown
- Implement screenshot gallery with lightbox/modal viewer
- Display LLM-generated analysis and recommendations
- Add download buttons for report and screenshots
- Add "Run Again" button

**Files to create:**

- `templates/results.html`

## Phase 6: Integration and Testing (Steps 24-26)

### Step 24: End-to-End Integration

Connect all components:

- Update `app.py` to register all API routes
- Ensure data flow: Story → Test Cases → Selection → Code Generation → Execution → Results
- Test complete user journey
- Verify screenshot capture at each step
- Verify LLM calls at each stage

**Files to modify:**

- `app.py`
- All API route files

### Step 25: Error Handling Enhancement

Implement comprehensive error handling:

- Add error handling in all API endpoints
- Implement retry logic for Bedrock API calls
- Handle Playwright execution errors gracefully
- Capture error screenshots on test failures
- Display user-friendly error messages in UI
- Log all errors appropriately

**Files to modify:**

- All API files
- `integrations/bedrock_client.py`
- `core/execution_manager.py`
- Frontend JavaScript

### Step 26: Testing

Create and run tests:

- Write unit tests for core components (story processor, test case generator, etc.)
- Write integration tests for API endpoints
- Test Bedrock integration with mock responses
- Test MCP Playwright integration
- Perform end-to-end testing of complete flow

**Files to create:**

- `tests/` directory with test files
- `tests/test_story_processor.py`
- `tests/test_api.py`
- `tests/test_integrations.py`

## Phase 7: Deployment Preparation (Steps 27-30)

### Step 27: EC2 Infrastructure Setup

EC2 instance is ready and configured:

- **Instance ID**: `i-0bb2e7c8d94a69d3b`
- **Instance Name**: `AI_CRDC_HUB`
- **Instance Type**: `t3.small` (2 vCPU, 2GB RAM) - upgraded from t3.micro
- **Static IP (Elastic IP)**: `3.221.24.93`
- **Elastic IP Allocation ID**: `eipalloc-0f01e70812f8a398e`
- **Region**: `us-east-1`
- **State**: Running
- **SSH Key**: `mcp-playwright-key-final`
- **Security Group**: Ports 22, 80, 443, 8080, 3000, 3001, 4000, 4001, 4002 open
- **Instance is clean/unused** - ready for fresh setup

**Next Steps:**
- Verify IAM role has Bedrock permissions (if not, attach role with `bedrock:InvokeModel`)
- SSH into instance and prepare for application deployment
- Run deployment scripts to install dependencies

**Files created:**
- `deployment/EC2_CREDENTIALS.md` - Contains all EC2 access details

### Step 28: Deployment Scripts

Create deployment automation:

- Create `deployment/install_dependencies.sh` for EC2 setup
- Create `deployment/app.service` for systemd service
- Add instructions for AWS IAM role configuration
- Create environment variable setup guide

**Files to create:**

- `deployment/install_dependencies.sh`
- `deployment/app.service`

### Step 29: Documentation

Complete project documentation:

- Update `README.md` with setup instructions
- Document API endpoints
- Document environment variables
- Create deployment guide for EC2
- Add troubleshooting section

**Files to modify:**

- `README.md`

### Step 30: Final Configuration

Prepare for deployment:

- Update `.env.example` with all required variables
- Verify all file paths are relative or configurable
- Test on local environment
- Prepare EC2 deployment checklist
- Verify AWS credentials and Bedrock access

**Files to modify:**

- `.env.example`
- Configuration files

## Implementation Order Summary

1. **Foundation** (Steps 1-5, 4a): Project structure, configs, utilities, TOTP generator, Bedrock client
2. **Core Logic** (Steps 6-10, 8a): Story processing, test generation, code generation with 2FA handling, execution, analysis
3. **MCP Integration** (Steps 11-13): MCP server, client, screenshot integration
4. **Backend API** (Steps 14-18): All REST endpoints
5. **Frontend** (Steps 19-23): All UI pages
6. **Integration** (Steps 24-26): End-to-end testing and error handling
7. **Deployment** (Steps 27-30): EC2 infrastructure, deployment scripts, and documentation

## Key Features

- **2FA/TOTP Support**: Automatic TOTP generation and input for application under test login flows
- **LLM-Driven**: All test generation, code generation, and analysis powered by AWS Bedrock
- **Screenshot Capture**: Automatic screenshot after each test step
- **Web UI**: User-friendly interface for test case selection and result viewing
- **MCP Playwright**: LLM-controlled test execution via MCP

## Dependencies

- Steps 1-5 must be completed before any other steps
- Steps 6-10 depend on Step 5 (Bedrock client)
- Steps 11-13 depend on Steps 6-10 (core logic)
- Steps 14-18 depend on Steps 6-13 (core logic and MCP)
- Steps 19-23 depend on Steps 14-18 (API endpoints)
- Steps 24-26 depend on all previous steps
- Steps 27-29 can be done in parallel with development but are needed for deployment
# Complete Design Plan: AI-Powered Test Automation System

## 1. System Overview

### 1.1 Purpose
AI-driven test automation system that:
- Reads user stories
- Generates test cases via LLM (AWS Bedrock)
- Allows human selection of test cases via web UI
- Generates Playwright scripts via LLM
- Executes tests via LLM (MCP Playwright)
- Captures screenshots after each step
- Analyzes results and generates reports via LLM

### 1.2 Key Features
- ✅ LLM-driven test generation
- ✅ Web UI for test case selection
- ✅ MCP Playwright for execution
- ✅ Screenshot capture per step
- ✅ LLM-based result analysis
- ✅ EC2 deployment
- ✅ Human-in-the-loop selection

### 1.3 Technology Stack
- **Backend**: Python 3.9+
- **Web Framework**: Flask or FastAPI
- **AI/LLM**: AWS Bedrock (Claude 3)
- **Automation**: Playwright
- **MCP**: MCP Playwright Server
- **Frontend**: HTML, CSS, JavaScript
- **Deployment**: AWS EC2
- **Storage**: Local filesystem (optional S3)

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    EC2 INSTANCE                              │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐ │
│  │              WEB UI LAYER                              │ │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐      │ │
│  │  │ Upload     │  │ Test Case  │  │ Results    │      │ │
│  │  │ Story Page │  │ Selection  │  │ & Reports  │      │ │
│  │  └────────────┘  └────────────┘  └────────────┘      │ │
│  └──────────────────────────────────────────────────────┘ │
│                        ↓                                    │
│  ┌──────────────────────────────────────────────────────┐ │
│  │           APPLICATION LAYER                           │ │
│  │  ┌──────────────────────────────────────────────┐    │ │
│  │  │         Orchestration Engine                 │    │ │
│  │  │  - Story Processor                           │    │ │
│  │  │  - Test Case Generator                       │    │ │
│  │  │  - Execution Manager                         │    │ │
│  │  │  - Result Analyzer                           │    │ │
│  │  └──────────────────────────────────────────────┘    │ │
│  └──────────────────────────────────────────────────────┘ │
│                        ↓                                    │
│  ┌──────────────────────────────────────────────────────┐ │
│  │            AI/LLM INTEGRATION LAYER                  │ │
│  │  ┌──────────────────────────────────────────────┐    │ │
│  │  │         AWS Bedrock Client                   │    │ │
│  │  │  - Test Case Generation                      │    │ │
│  │  │  - Playwright Code Generation                │    │ │
│  │  │  - Result Analysis                           │    │ │
│  │  └──────────────────────────────────────────────┘    │ │
│  └──────────────────────────────────────────────────────┘ │
│                        ↓                                    │
│  ┌──────────────────────────────────────────────────────┐ │
│  │         AUTOMATION LAYER (MCP Playwright)            │ │
│  │  ┌──────────────────────────────────────────────┐    │ │
│  │  │         MCP Playwright Server                │    │ │
│  │  │  - Browser Control                           │    │ │
│  │  │  - Test Execution                            │    │ │
│  │  │  - Screenshot Capture                        │    │ │
│  │  └──────────────────────────────────────────────┘    │ │
│  └──────────────────────────────────────────────────────┘ │
│                        ↓                                    │
│  ┌──────────────────────────────────────────────────────┐ │
│  │              STORAGE LAYER                            │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐            │ │
│  │  │ Stories  │ │ Tests    │ │ Results  │            │ │
│  │  │ Screenshots │ Reports │            │ │
│  │  └──────────┘ └──────────┘ └──────────┘            │ │
│  └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                        ↓ API Calls
┌─────────────────────────────────────────────────────────────┐
│              AWS BEDROCK (Cloud)                            │
│  - Claude 3 Model                                            │
│  - Test Generation                                           │
│  - Code Generation                                           │
│  - Analysis                                                  │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Component Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Web UI)                    │
│  - React/Vanilla JS                                     │
│  - HTML/CSS                                             │
│  - REST API Client                                      │
└─────────────────────────────────────────────────────────┘
                        ↓ HTTP
┌─────────────────────────────────────────────────────────┐
│              Backend API (Flask/FastAPI)                │
│  - REST Endpoints                                       │
│  - Request Validation                                   │
│  - Session Management                                   │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│              Core Business Logic                        │
│  - Story Processor                                      │
│  - Test Case Manager                                    │
│  - Execution Orchestrator                                │
│  - Result Processor                                     │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│              External Integrations                      │
│  - AWS Bedrock Client                                   │
│  - MCP Playwright Client                                │
│  - File System Handler                                  │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Component Design

### 3.1 Frontend Components

#### 3.1.1 Upload Story Page
**Purpose**: User uploads or pastes user story

**Elements**:
- File upload button
- Text area for pasting story
- "Generate Test Cases" button
- Loading indicator
- Error messages

**User Flow**:
1. User uploads file OR pastes text
2. Clicks "Generate Test Cases"
3. Shows loading state
4. Redirects to Test Cases page

#### 3.1.2 Test Cases Selection Page
**Purpose**: Display generated test cases, allow selection

**Elements**:
- List of test cases (cards/table)
- Checkbox for each test case
- Test case details (ID, name, description, steps)
- "Select All" / "Deselect All" buttons
- "Run Selected Tests" button
- Search/filter functionality

**Test Case Card Structure**:
```
┌─────────────────────────────────────┐
│ ☑ TC001: User Login Test           │
│ Description: Verify user can login  │
│ Steps:                              │
│  1. Navigate to login page          │
│  2. Enter credentials               │
│  3. Click login button              │
│  4. Verify dashboard                │
│ Priority: High                      │
└─────────────────────────────────────┘
```

#### 3.1.3 Execution Progress Page
**Purpose**: Show real-time execution progress

**Elements**:
- Progress bar (overall)
- List of running tests with individual progress
- Live logs/console output
- Current step indicator
- "Cancel Execution" button
- Auto-refresh

**Progress Display**:
```
Overall Progress: ████████░░ 80%

TC002: File Upload Test
  Step 3/4: Selecting file...
  ████████████░░ 75%
  
TC003: Form Submission
  Step 2/3: Filling form...
  ████████░░░░░░ 66%
```

#### 3.1.4 Results & Report Page
**Purpose**: Display execution results with screenshots

**Elements**:
- Test summary (passed/failed/total)
- Detailed results per test case
- Screenshot gallery
- Step-by-step breakdown with screenshots
- Download report button
- Download screenshots button
- "Run Again" button

**Result Card Structure**:
```
┌─────────────────────────────────────┐
│ TC002: File Upload Test    ✅ PASS  │
│                                     │
│ Steps:                              │
│  ✅ Step 1: Navigate [📸]          │
│  ✅ Step 2: Click Upload [📸]      │
│  ✅ Step 3: Select File [📸]       │
│  ✅ Step 4: Verify [📸]           │
│                                     │
│ Duration: 12.5s                     │
│ [View Screenshots] [View Logs]      │
└─────────────────────────────────────┘
```

### 3.2 Backend Components

#### 3.2.1 Story Processor
**Responsibility**: Parse and validate user stories

**Input**: User story (text file or string)
**Output**: Parsed story object

**Functions**:
- `parse_story(story_text)`: Extract key information
- `validate_story(story)`: Validate format
- `extract_scenarios(story)`: Identify test scenarios

#### 3.2.2 Test Case Generator
**Responsibility**: Generate test cases using LLM

**Input**: User story
**Output**: List of test cases

**Functions**:
- `generate_test_cases(story)`: Call Bedrock API
- `parse_test_cases(llm_response)`: Parse JSON response
- `save_test_cases(test_cases, execution_id)`: Save to storage

**LLM Prompt Template**:
```
You are a QA automation engineer. Given the following user story, 
generate comprehensive test cases.

User Story:
{user_story}

Generate test cases in the following JSON format:
[
  {
    "id": "TC001",
    "name": "Test Case Name",
    "description": "Detailed description",
    "steps": ["step1", "step2", ...],
    "expected_result": "What to verify",
    "priority": "High/Medium/Low"
  }
]
```

#### 3.2.3 Playwright Code Generator
**Responsibility**: Generate Playwright test code from test cases

**Input**: Selected test cases
**Output**: Playwright JavaScript/TypeScript code

**Functions**:
- `generate_playwright_code(test_cases, execution_id)`: Call Bedrock
- `include_screenshot_capture(code)`: Add screenshot steps
- `save_playwright_code(code, execution_id)`: Save generated code

**LLM Prompt Template**:
```
Generate Playwright test code for the following test cases:
{test_cases}

Requirements:
1. Use Playwright best practices
2. Add screenshot capture after EACH step
3. Use descriptive locators (text-based preferred)
4. Include proper waits
5. Add error handling

Format: JavaScript/TypeScript Playwright test file
```

#### 3.2.4 Execution Manager
**Responsibility**: Orchestrate test execution via MCP

**Input**: Playwright code, execution_id
**Output**: Execution results

**Functions**:
- `execute_tests(playwright_code, execution_id)`: Execute via MCP
- `monitor_execution(execution_id)`: Track progress
- `capture_screenshots(execution_id, test_case_id, step)`: Save screenshots
- `handle_execution_errors(error)`: Error handling

#### 3.2.5 Result Analyzer
**Responsibility**: Analyze results using LLM

**Input**: Execution results, screenshots
**Output**: Analysis report

**Functions**:
- `analyze_results(results, execution_id)`: Call Bedrock
- `generate_report(analysis, results)`: Create HTML/text report
- `identify_failures(results)`: Find failed tests
- `suggest_fixes(failures)`: LLM suggests fixes

**LLM Prompt Template**:
```
Analyze the following test execution results:
{results}

Screenshots are available at: {screenshot_paths}

Provide:
1. Summary (total, passed, failed)
2. Detailed analysis of each test
3. Failure reasons (if any)
4. Recommendations
5. Screenshot analysis

Format: Comprehensive test report
```

### 3.3 Integration Components

#### 3.3.1 AWS Bedrock Client
**Responsibility**: Interface with AWS Bedrock API

**Configuration**:
- Region: us-east-1 (configurable)
- Model: Claude 3 Sonnet
- API credentials: AWS IAM

**Functions**:
- `invoke_model(prompt, model_id)`: Call Bedrock API
- `generate_test_cases(story)`: Generate test cases
- `generate_code(test_cases)`: Generate Playwright code
- `analyze_results(results)`: Analyze execution results

**Error Handling**:
- Retry logic for API failures
- Rate limiting
- Token limit management

#### 3.3.2 MCP Playwright Client
**Responsibility**: Control Playwright via MCP

**Functions**:
- `connect_mcp_server()`: Connect to MCP server
- `execute_step(step_code)`: Execute single step
- `take_screenshot(path)`: Capture screenshot
- `get_dom()`: Get current page DOM
- `navigate(url)`: Navigate to URL

**MCP Server Functions**:
- `playwright.navigate(url)`
- `playwright.click(selector)`
- `playwright.fill(selector, text)`
- `playwright.screenshot(path)`
- `playwright.get_text(selector)`
- `playwright.wait_for(selector)`

#### 3.3.3 Screenshot Handler
**Responsibility**: Manage screenshot capture and storage

**Functions**:
- `create_screenshot_path(execution_id, test_case_id, step)`: Generate path
- `save_screenshot(image_data, path)`: Save screenshot
- `organize_screenshots(execution_id)`: Organize by execution
- `get_screenshot_url(path)`: Generate web-accessible URL

**Storage Structure**:
```
screenshots/
  execution_{execution_id}/
    TC{test_case_id:03d}/
      step_{step_number:02d}_{description}.png
```

---

## 4. Data Flow

### 4.1 Complete User Journey

```
1. USER UPLOADS STORY
   User → UI → API → Story Processor
   ↓
   Story saved to: data/stories/{story_id}.txt

2. LLM GENERATES TEST CASES
   Story Processor → Bedrock Client → AWS Bedrock
   ↓
   Bedrock → Test Cases (JSON)
   ↓
   Test Case Generator → Save to: data/test_cases/{execution_id}.json

3. USER SELECTS TEST CASES
   UI → API → Test Case Manager
   ↓
   Selected IDs: [1, 2, 3]
   ↓
   Save selection: data/selections/{execution_id}.json

4. LLM GENERATES PLAYWRIGHT CODE
   Selected Test Cases → Bedrock Client → AWS Bedrock
   ↓
   Bedrock → Playwright Code
   ↓
   Code Generator → Save to: generated_tests/{execution_id}/test.spec.js

5. LLM EXECUTES VIA MCP
   Playwright Code → MCP Client → MCP Server → Playwright
   ↓
   For each step:
     - Execute action
     - Capture screenshot
     - Save screenshot
   ↓
   Results → Save to: data/results/{execution_id}.json

6. LLM ANALYZES RESULTS
   Results + Screenshots → Bedrock Client → AWS Bedrock
   ↓
   Bedrock → Analysis Report
   ↓
   Result Analyzer → Save to: reports/{execution_id}.html

7. USER VIEWS RESULTS
   UI → API → Results Repository
   ↓
   Display: Results + Screenshots + Report
```

### 4.2 Data Structures

#### 4.2.1 User Story
```json
{
  "id": "story_001",
  "content": "As a user, I want to...",
  "uploaded_at": "2024-01-15T10:30:00Z",
  "status": "processed"
}
```

#### 4.2.2 Test Case
```json
{
  "id": "TC001",
  "name": "User Login Test",
  "description": "Verify user can login with valid credentials",
  "steps": [
    "Navigate to login page",
    "Enter username",
    "Enter password",
    "Click login button",
    "Verify dashboard is displayed"
  ],
  "expected_result": "User is logged in and sees dashboard",
  "priority": "High",
  "generated_at": "2024-01-15T10:35:00Z"
}
```

#### 4.2.3 Execution
```json
{
  "execution_id": "exec_001",
  "story_id": "story_001",
  "selected_test_cases": ["TC001", "TC002"],
  "status": "running",
  "started_at": "2024-01-15T10:40:00Z",
  "completed_at": null,
  "progress": 60
}
```

#### 4.2.4 Test Result
```json
{
  "execution_id": "exec_001",
  "test_case_id": "TC001",
  "status": "passed",
  "duration": 12.5,
  "steps": [
    {
      "step_number": 1,
      "description": "Navigate to login page",
      "status": "passed",
      "duration": 2.1,
      "screenshot": "screenshots/exec_001/TC001/step_01_navigate.png"
    },
    {
      "step_number": 2,
      "description": "Enter username",
      "status": "passed",
      "duration": 1.5,
      "screenshot": "screenshots/exec_001/TC001/step_02_enter_username.png"
    }
  ],
  "error": null
}
```

#### 4.2.5 Report
```json
{
  "execution_id": "exec_001",
  "summary": {
    "total": 2,
    "passed": 2,
    "failed": 0,
    "duration": 25.3
  },
  "test_results": [...],
  "analysis": "All tests passed successfully...",
  "recommendations": [...],
  "generated_at": "2024-01-15T10:45:00Z"
}
```

---

## 5. API Design

### 5.1 REST API Endpoints

#### 5.1.1 Story Management
```
POST   /api/stories
  Body: { "story": "text content" } or multipart/form-data
  Response: { "story_id": "story_001", "status": "uploaded" }

GET    /api/stories/:story_id
  Response: { "id": "story_001", "content": "...", ... }

GET    /api/stories
  Response: [{ "id": "story_001", ... }, ...]
```

#### 5.1.2 Test Case Management
```
POST   /api/stories/:story_id/generate-test-cases
  Response: { "execution_id": "exec_001", "status": "generating" }

GET    /api/test-cases/:execution_id
  Response: { "test_cases": [...], "status": "ready" }

POST   /api/test-cases/select
  Body: { "execution_id": "exec_001", "selected_ids": [1, 2, 3] }
  Response: { "status": "selected", "count": 3 }
```

#### 5.1.3 Test Execution
```
POST   /api/executions
  Body: { "execution_id": "exec_001" }
  Response: { "execution_id": "exec_001", "status": "started" }

GET    /api/executions/:execution_id/status
  Response: { "status": "running", "progress": 60, ... }

GET    /api/executions/:execution_id/results
  Response: { "results": [...], "summary": {...} }
```

#### 5.1.4 Screenshots
```
GET    /api/screenshots/:execution_id/:test_case_id
  Response: { "screenshots": ["path1", "path2", ...] }

GET    /api/screenshots/:execution_id/:test_case_id/:step_number
  Response: Image file (PNG)

GET    /api/screenshots/:execution_id/download
  Response: ZIP file
```

#### 5.1.5 Reports
```
GET    /api/reports/:execution_id
  Response: { "report": "HTML content", ... }

GET    /api/reports/:execution_id/download
  Response: HTML/PDF file
```

---

## 6. Database/Storage Design

### 6.1 File-Based Storage (Primary)

**Directory Structure**:
```
AI_CRDCHub/
├── data/
│   ├── stories/
│   │   └── story_{id}.txt
│   ├── test_cases/
│   │   └── execution_{id}.json
│   ├── selections/
│   │   └── execution_{id}.json
│   └── results/
│       └── execution_{id}.json
├── generated_tests/
│   └── execution_{id}/
│       └── test.spec.js
├── screenshots/
│   └── execution_{id}/
│       └── TC{test_case_id}/
│           └── step_{number}_{description}.png
└── reports/
    └── execution_{id}/
        ├── report.html
        └── report.json
```

### 6.2 Optional Database (Future Enhancement)

**Tables**:
- `stories` (id, content, created_at, status)
- `test_cases` (id, story_id, name, description, steps, priority)
- `executions` (id, story_id, status, started_at, completed_at)
- `test_results` (id, execution_id, test_case_id, status, duration)
- `screenshots` (id, execution_id, test_case_id, step_number, path)

---

## 7. Security Design

### 7.1 Authentication & Authorization
- **Phase 1**: No authentication (single user)
- **Phase 2**: Basic authentication (username/password)
- **Phase 3**: JWT tokens
- **Phase 4**: OAuth integration

### 7.2 AWS Security
- IAM roles for EC2 (Bedrock access)
- Secrets Manager for API keys
- VPC for network isolation
- Security Groups for firewall rules

### 7.3 Data Security
- Input validation
- File upload restrictions
- Path traversal prevention
- XSS protection in UI

---

## 8. Deployment Design

### 8.1 EC2 Instance Specifications

**Instance Type**: t3.large
- **vCPU**: 2
- **RAM**: 8 GB
- **Storage**: 50 GB EBS
- **OS**: Ubuntu 22.04 LTS

**Security Group Rules**:
- Inbound: SSH (22), HTTP (80), HTTPS (443)
- Outbound: All (for Bedrock API, target apps)

**IAM Role Permissions**:
- `bedrock:InvokeModel`
- `bedrock:ListFoundationModels`
- S3 access (if using S3 for screenshots)

### 8.2 Application Deployment

**Setup Script**:
```bash
#!/bin/bash
# install_dependencies.sh

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python
sudo apt install python3 python3-pip python3-venv -y

# Install Node.js (for Playwright)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install Playwright browsers
npx playwright install --with-deps

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# User edits .env with AWS credentials

# Create directories
mkdir -p data/{stories,test_cases,selections,results}
mkdir -p generated_tests screenshots reports

# Start application
python app.py
```

**Systemd Service** (Optional):
```ini
[Unit]
Description=AI Test Automation System
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/AI_CRDCHub
Environment="PATH=/opt/AI_CRDCHub/venv/bin"
ExecStart=/opt/AI_CRDCHub/venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### 8.3 Deployment Steps

1. **Launch EC2 Instance**
   - Choose Ubuntu 22.04
   - Configure security group
   - Attach IAM role

2. **SSH into EC2**
   ```bash
   ssh -i key.pem ubuntu@ec2-ip
   ```

3. **Clone/Upload Code**
   ```bash
   git clone <repo> AI_CRDCHub
   # or upload via SCP
   ```

4. **Run Setup Script**
   ```bash
   cd AI_CRDCHub
   chmod +x install_dependencies.sh
   ./install_dependencies.sh
   ```

5. **Configure Environment**
   ```bash
   nano .env
   # Add AWS credentials, Bedrock region, etc.
   ```

6. **Start Application**
   ```bash
   python app.py
   # or use systemd service
   sudo systemctl start ai-test-automation
   ```

7. **Access Web UI**
   - Open browser: `http://ec2-ip:5000`

---

## 9. Error Handling & Logging

### 9.1 Error Handling Strategy

**LLM API Errors**:
- Retry with exponential backoff
- Fallback to alternative model
- Log error details
- Notify user

**Playwright Execution Errors**:
- Capture error screenshots
- Log step where error occurred
- Continue with other tests
- Generate error report

**File System Errors**:
- Check disk space
- Validate file paths
- Handle permission errors

### 9.2 Logging

**Log Levels**:
- DEBUG: Detailed execution flow
- INFO: General operations
- WARNING: Non-critical issues
- ERROR: Failures requiring attention

**Log Storage**:
- Application logs: `logs/app.log`
- Execution logs: `logs/execution_{id}.log`
- Error logs: `logs/errors.log`

**Log Rotation**:
- Daily rotation
- Keep last 30 days
- Compress old logs

---

## 10. Testing Strategy

### 10.1 Unit Tests
- Test case generation logic
- Code parsing functions
- Screenshot handler
- File operations

### 10.2 Integration Tests
- Bedrock API integration
- MCP Playwright integration
- File system operations
- API endpoints

### 10.3 End-to-End Tests
- Complete user journey
- Story upload → Test generation → Execution → Results

---

## 11. Performance Considerations

### 11.1 Optimization Strategies

**LLM API Calls**:
- Batch requests where possible
- Cache common responses
- Use streaming for long responses

**Screenshot Storage**:
- Compress screenshots (PNG → WebP)
- Clean up old screenshots
- Optional: Move to S3 for long-term storage

**Concurrent Execution**:
- Queue system for multiple executions
- Limit concurrent browser instances
- Resource monitoring

### 11.2 Scalability

**Current Design**: Single EC2 instance
- Handles: 10-20 concurrent test executions
- Suitable for: Small to medium teams

**Future Scaling**:
- Multiple EC2 instances with load balancer
- SQS for job queue
- S3 for shared storage
- RDS for centralized database

---

## 12. Monitoring & Maintenance

### 12.1 Monitoring

**Metrics to Track**:
- Test execution success rate
- Average execution time
- LLM API response times
- Screenshot storage usage
- Error rates

**Tools**:
- CloudWatch (AWS)
- Application logs
- Custom dashboard (optional)

### 12.2 Maintenance Tasks

**Daily**:
- Monitor execution logs
- Check disk space
- Review error logs

**Weekly**:
- Clean up old screenshots
- Archive old results
- Review performance metrics

**Monthly**:
- Update dependencies
- Review and optimize prompts
- Backup important data

---

## 13. Implementation Phases

### Phase 1: Core Functionality (Week 1-2)
- ✅ Basic Flask/FastAPI setup
- ✅ AWS Bedrock integration
- ✅ Story upload
- ✅ Test case generation
- ✅ Simple UI for test case display

### Phase 2: Execution (Week 3-4)
- ✅ MCP Playwright setup
- ✅ Test case selection UI
- ✅ Playwright code generation
- ✅ Test execution via MCP
- ✅ Basic results display

### Phase 3: Screenshots & Reports (Week 5-6)
- ✅ Screenshot capture after each step
- ✅ Screenshot gallery in UI
- ✅ Result analysis via LLM
- ✅ Report generation
- ✅ Download functionality

### Phase 4: Polish & Deployment (Week 7-8)
- ✅ Error handling improvements
- ✅ UI/UX enhancements
- ✅ EC2 deployment
- ✅ Documentation
- ✅ Testing & bug fixes

---

## 14. File Structure Summary

```
AI_CRDCHub/
├── app.py                          # Main Flask/FastAPI app
├── requirements.txt                # Python dependencies
├── package.json                    # Node.js dependencies (if needed)
├── .env                            # Environment variables
├── .gitignore
├── README.md
│
├── api/                            # API routes
│   ├── __init__.py
│   ├── stories.py                  # Story endpoints
│   ├── test_cases.py               # Test case endpoints
│   ├── executions.py               # Execution endpoints
│   ├── screenshots.py              # Screenshot endpoints
│   └── reports.py                  # Report endpoints
│
├── core/                           # Core business logic
│   ├── __init__.py
│   ├── story_processor.py          # Story parsing
│   ├── test_case_generator.py      # Test case generation
│   ├── code_generator.py           # Playwright code generation
│   ├── execution_manager.py        # Execution orchestration
│   └── result_analyzer.py          # Result analysis
│
├── integrations/                   # External integrations
│   ├── __init__.py
│   ├── bedrock_client.py           # AWS Bedrock client
│   └── mcp_client.py              # MCP Playwright client
│
├── utils/                          # Utilities
│   ├── __init__.py
│   ├── screenshot_handler.py      # Screenshot management
│   ├── file_handler.py            # File operations
│   ├── logger.py                  # Logging
│   └── validators.py              # Input validation
│
├── templates/                      # HTML templates
│   ├── base.html
│   ├── upload_story.html
│   ├── test_cases.html
│   ├── progress.html
│   └── results.html
│
├── static/                         # Static files
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── app.js
│   └── images/
│
├── data/                           # Data storage
│   ├── stories/
│   ├── test_cases/
│   ├── selections/
│   └── results/
│
├── generated_tests/                # Generated Playwright code
├── screenshots/                    # Screenshot storage
├── reports/                        # Generated reports
├── logs/                           # Application logs
│
└── deployment/                     # Deployment files
    ├── install_dependencies.sh
    ├── app.service                # Systemd service
    └── nginx.conf                 # Nginx config (if needed)
```

---

## 15. Success Criteria

### 15.1 Functional Requirements
- ✅ User can upload user story
- ✅ System generates test cases via LLM
- ✅ User can select test cases via UI
- ✅ System generates Playwright code via LLM
- ✅ System executes tests via LLM (MCP)
- ✅ Screenshots captured after each step
- ✅ Results analyzed via LLM
- ✅ Reports generated and displayed

### 15.2 Non-Functional Requirements
- Response time: < 5 seconds for UI operations
- Test execution: Handles 10+ concurrent tests
- Reliability: 95%+ success rate
- Usability: Intuitive UI, minimal training needed

---

**Document Version**: 1.0
**Last Updated**: 2024-01-15
**Author**: AI Assistant


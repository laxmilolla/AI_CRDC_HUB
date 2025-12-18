# AI_CRDC_HUB - AI-Powered Test Automation System

An intelligent test automation system that uses LLM (AWS Bedrock) to generate test cases from user stories, execute them via Microsoft MCP Playwright, and analyze results with AI.

## Features

- **LLM-Driven Test Generation**: Automatically generates comprehensive test cases from user stories using AWS Bedrock (Claude 3)
- **Human Test Selection**: Web UI for selecting which test cases to execute
- **MCP Playwright Execution**: Executes tests using Microsoft's MCP Playwright server
- **Screenshot Capture**: Automatic screenshot after each test step
- **AI Result Analysis**: LLM analyzes execution results and generates insights
- **2FA Support**: Built-in TOTP generator for applications requiring two-factor authentication

## Architecture

```
User Story → LLM (Test Cases) → UI (User Selects) → LLM (Playwright Code) → MCP (Execute) → LLM (Analyze) → Report
```

## Technology Stack

- **Backend**: Python 3.9+, Flask
- **AI/LLM**: AWS Bedrock (Claude 3 Sonnet)
- **Automation**: Microsoft MCP Playwright
- **Frontend**: HTML, CSS, JavaScript
- **Deployment**: AWS EC2

## Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- AWS account with Bedrock access
- EC2 instance (or local development)

### Installation

1. **Clone repository**
   ```bash
   git clone https://github.com/laxmilolla/AI_CRDC_HUB.git
   cd AI_CRDC_HUB
   ```

2. **Install Python dependencies**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Install Playwright browsers**
   ```bash
   npx playwright install --with-deps chromium
   ```

4. **Install Microsoft MCP Playwright**
   ```bash
   npm install -g @modelcontextprotocol/server-playwright
   ```

5. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your AWS credentials and configuration
   ```

6. **Run application**
   ```bash
   python app.py
   ```

7. **Access web UI**
   - Open browser: `http://localhost:5000`

## Configuration

### Environment Variables

Create `.env` file with:

```env
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# TOTP Configuration (for 2FA)
TOTP_SECRET_KEY=your_totp_secret_key

# Flask Configuration
FLASK_ENV=development
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
```

## Usage

### 1. Upload User Story

- Go to the home page
- Upload a text file or paste your user story
- Click "Generate Test Cases"

### 2. Select Test Cases

- Review generated test cases
- Select which tests to run using checkboxes
- Click "Run Selected Tests"

### 3. Monitor Execution

- View real-time progress
- See individual test execution status
- Monitor step-by-step progress

### 4. View Results

- See test execution summary
- View detailed results per test case
- Review AI-generated analysis and recommendations
- Download reports and screenshots

## TOTP Generator

For applications requiring 2FA, use the TOTP generator:

```bash
python3 generateOTP.py <your_secret_key>
```

This outputs the current TOTP code for authentication.

## Project Structure

```
AI_CRDCHub/
├── app.py                 # Main Flask application
├── api/                   # API routes
├── core/                  # Core business logic
├── integrations/          # External integrations (Bedrock, MCP)
├── utils/                 # Utilities
├── templates/             # HTML templates
├── static/                # CSS, JS, images
├── data/                  # Data storage
├── generated_tests/       # Generated Playwright code
├── screenshots/           # Test screenshots
└── reports/               # Generated reports
```

## API Endpoints

- `POST /api/stories` - Upload user story
- `GET /api/stories/:id` - Get story
- `POST /api/stories/:id/generate-test-cases` - Generate test cases
- `GET /api/test-cases/:execution_id` - Get test cases
- `POST /api/test-cases/select` - Select test cases
- `POST /api/executions` - Start execution
- `GET /api/executions/:id/status` - Get execution status
- `GET /api/executions/:id/results` - Get results
- `GET /api/screenshots/:execution_id/:test_case_id` - List screenshots
- `GET /api/reports/:execution_id` - Get report

## Deployment

See [deployment/DEPLOYMENT_GUIDE.md](deployment/DEPLOYMENT_GUIDE.md) for EC2 deployment instructions.

## EC2 Instance

- **Instance ID**: `i-0bb2e7c8d94a69d3b`
- **Name**: `AI_CRDC_HUB`
- **Static IP**: `3.221.24.93`
- **Type**: `t3.small`

See [deployment/EC2_CREDENTIALS.md](deployment/EC2_CREDENTIALS.md) for access details.

## Documentation

- [Design Document](Design_AI_CRDC.md) - Complete system design
- [Implementation Plan](IMPLEMENTATION_PLAN.md) - Step-by-step implementation plan
- [Deployment Guide](deployment/DEPLOYMENT_GUIDE.md) - EC2 deployment instructions

## License

[Add your license here]

## Contributing

[Add contribution guidelines]

---

**Last Updated**: 2024-01-15


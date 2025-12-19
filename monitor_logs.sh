#!/bin/bash
# Monitor logs with filtering for important events

echo "=== AI_CRDC_HUB Log Monitor ==="
echo "Press Ctrl+C to stop"
echo ""

# Monitor Flask app logs with filtering (including LLM validation)
echo "--- Flask App Logs (Filtered) ---"
ssh -i ~/Downloads/ai-crdc-hub-key.pem ubuntu@3.221.24.93 "sudo journalctl -u ai-crdc-hub.service -f --no-pager" | grep --line-buffered -E 'INFO|ERROR|WARNING|execution|Execution|test.*case|screenshot|Screenshot|Step|step|status|Status|error|Error|Exception|Traceback|TC001|TC002|TC003|validation|Validation|LLM|llm|validate|reasoning|evidence|checks|checks_needed|checks_performed|validate_step_with_llm|tool.*result|Bedrock|bedrock' &

# Monitor MCP Bridge logs with filtering
echo "--- MCP Bridge Logs (Filtered) ---"
ssh -i ~/Downloads/ai-crdc-hub-key.pem ubuntu@3.221.24.93 "sudo journalctl -u mcp-bridge.service -f --no-pager" | grep --line-buffered -E 'MCP Bridge|tool|Tool|screenshot|Screenshot|navigate|Navigate|click|Click|fill|Fill|error|Error|connected|Connected|success|Success|playwright|evaluate|get_text|get_dom|wait_for' &

wait


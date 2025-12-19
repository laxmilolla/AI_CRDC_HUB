#!/bin/bash
# Cleanup script to kill hung browser processes
# Run this periodically via cron or systemd timer

LOG_FILE="/opt/AI_CRDC_HUB/logs/cleanup.log"
MAX_BROWSER_AGE=3600  # Kill browsers older than 1 hour
MAX_MCP_AGE=7200      # Kill MCP servers older than 2 hours

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log "Starting browser cleanup..."

# Kill Chrome processes older than MAX_BROWSER_AGE
OLD_CHROME=$(ps -eo pid,etime,cmd | grep -E 'chrome|chromium' | grep -v grep | awk -v max_age="$MAX_BROWSER_AGE" '
{
    # Parse elapsed time (format: HH:MM:SS or MM:SS)
    split($2, time_parts, ":")
    if (length(time_parts) == 3) {
        age = time_parts[1]*3600 + time_parts[2]*60 + time_parts[3]
    } else if (length(time_parts) == 2) {
        age = time_parts[1]*60 + time_parts[2]
    } else {
        age = 0
    }
    if (age > max_age) {
        print $1
    }
}')

if [ -n "$OLD_CHROME" ]; then
    log "Killing old Chrome processes: $OLD_CHROME"
    echo "$OLD_CHROME" | xargs kill -9 2>/dev/null
fi

# Kill MCP server processes older than MAX_MCP_AGE
OLD_MCP=$(ps -eo pid,etime,cmd | grep 'playwright-mcp-server' | grep -v grep | awk -v max_age="$MAX_MCP_AGE" '
{
    split($2, time_parts, ":")
    if (length(time_parts) == 3) {
        age = time_parts[1]*3600 + time_parts[2]*60 + time_parts[3]
    } else if (length(time_parts) == 2) {
        age = time_parts[1]*60 + time_parts[2]
    } else {
        age = 0
    }
    if (age > max_age) {
        print $1
    }
}')

if [ -n "$OLD_MCP" ]; then
    log "Killing old MCP server processes: $OLD_MCP"
    echo "$OLD_MCP" | xargs kill -9 2>/dev/null
fi

# Clean up defunct processes
DEFUNCT=$(ps aux | grep '<defunct>' | grep -v grep | awk '{print $2}')
if [ -n "$DEFUNCT" ]; then
    log "Cleaning up defunct processes: $DEFUNCT"
    echo "$DEFUNCT" | xargs kill -9 2>/dev/null
fi

# Count remaining processes
CHROME_COUNT=$(ps aux | grep -E 'chrome|chromium' | grep -v grep | wc -l)
MCP_COUNT=$(ps aux | grep 'playwright-mcp-server' | grep -v grep | wc -l)

log "Cleanup complete. Chrome processes: $CHROME_COUNT, MCP servers: $MCP_COUNT"


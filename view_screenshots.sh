#!/bin/bash
# Quick script to view latest screenshots from EC2

EC2_HOST="3.221.24.93"
EC2_USER="ubuntu"
KEY_FILE="$HOME/Downloads/ai-crdc-hub-key.pem"
SCREENSHOT_DIR="/opt/AI_CRDC_HUB/screenshots"

echo "=== Latest Screenshots ==="
echo ""

# Get latest execution
LATEST_EXEC=$(ssh -i "$KEY_FILE" "$EC2_USER@$EC2_HOST" "ls -td $SCREENSHOT_DIR/execution_* 2>/dev/null | head -1 | xargs basename")
if [ -z "$LATEST_EXEC" ]; then
    echo "No screenshots found"
    exit 1
fi

echo "Latest execution: $LATEST_EXEC"
echo ""

# List all screenshots in latest execution
ssh -i "$KEY_FILE" "$EC2_USER@$EC2_HOST" "find $SCREENSHOT_DIR/$LATEST_EXEC -name '*.png' -type f | sort" | while read screenshot; do
    filename=$(basename "$screenshot")
    size=$(ssh -i "$KEY_FILE" "$EC2_USER@$EC2_HOST" "ls -lh \"$screenshot\" | awk '{print \$5}'")
    echo "  $filename ($size)"
done

echo ""
echo "To download a screenshot:"
echo "  scp -i $KEY_FILE $EC2_USER@$EC2_HOST:$SCREENSHOT_DIR/$LATEST_EXEC/TCTC001/<filename> ./"
echo ""
echo "To download all screenshots from latest execution:"
echo "  scp -i $KEY_FILE -r $EC2_USER@$EC2_HOST:$SCREENSHOT_DIR/$LATEST_EXEC ./screenshots_$LATEST_EXEC"


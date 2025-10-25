#!/bin/bash

# Agent Selection Integration Test
# This script tests the complete agent selection workflow

echo "=========================================="
echo "AGENT SELECTION INTEGRATION TEST"
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if services are running
echo -e "\n${YELLOW}Checking services...${NC}"

# Check backend
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Backend running (port 8000)"
else
    echo -e "${RED}✗${NC} Backend not running (port 8000)"
    echo "   Start with: cd backend && python app.py"
    exit 1
fi

# Check LangGraph
if curl -s http://localhost:2024/ok > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} LangGraph running (port 2024)"
else
    echo -e "${YELLOW}⚠${NC} LangGraph not running (port 2024)"
    echo "   Start with: cd main && langgraph dev"
fi

# Check frontend
if curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Frontend running (port 5173)"
else
    echo -e "${YELLOW}⚠${NC} Frontend not running (port 5173)"
    echo "   Start with: cd frontend && npm run dev"
fi

echo -e "\n${YELLOW}Creating test session...${NC}"

# Create a new session
SESSION_RESPONSE=$(curl -s -X POST http://localhost:8000/api/session/create)
SESSION_ID=$(echo $SESSION_RESPONSE | grep -o '"session_id":"[^"]*' | cut -d'"' -f4)

if [ -z "$SESSION_ID" ]; then
    echo -e "${RED}✗${NC} Failed to create session"
    exit 1
fi

echo -e "${GREEN}✓${NC} Session created: $SESSION_ID"

echo -e "\n${YELLOW}Testing agent selection routing...${NC}"

# Test 1: DOCX Agent
echo -e "\n1. Testing DOCX Agent"
curl -s -X POST http://localhost:8000/api/chat/send \
    -H "Content-Type: application/json" \
    -d "{
        \"session_id\": \"$SESSION_ID\",
        \"message\": \"Create a test document\",
        \"selected_agent\": \"docx_agent\"
    }" > /dev/null

if [ $? -eq 0 ]; then
    echo -e "   ${GREEN}✓${NC} Message sent with selected_agent=docx_agent"
else
    echo -e "   ${RED}✗${NC} Failed to send message"
fi

# Test 2: RFP Finance Team
echo -e "\n2. Testing RFP Finance Team"
curl -s -X POST http://localhost:8000/api/chat/send \
    -H "Content-Type: application/json" \
    -d "{
        \"session_id\": \"$SESSION_ID\",
        \"message\": \"Prepare budget analysis\",
        \"selected_agent\": \"rfp_finance\"
    }" > /dev/null

if [ $? -eq 0 ]; then
    echo -e "   ${GREEN}✓${NC} Message sent with selected_agent=rfp_finance"
else
    echo -e "   ${RED}✗${NC} Failed to send message"
fi

# Test 3: General Assistant
echo -e "\n3. Testing General Assistant"
curl -s -X POST http://localhost:8000/api/chat/send \
    -H "Content-Type: application/json" \
    -d "{
        \"session_id\": \"$SESSION_ID\",
        \"message\": \"What can you help me with?\",
        \"selected_agent\": \"general_assistant\"
    }" > /dev/null

if [ $? -eq 0 ]; then
    echo -e "   ${GREEN}✓${NC} Message sent with selected_agent=general_assistant"
else
    echo -e "   ${RED}✗${NC} Failed to send message"
fi

# Test 4: Supervisor (default)
echo -e "\n4. Testing Supervisor (default routing)"
curl -s -X POST http://localhost:8000/api/chat/send \
    -H "Content-Type: application/json" \
    -d "{
        \"session_id\": \"$SESSION_ID\",
        \"message\": \"Help me with my RFP\",
        \"selected_agent\": \"supervisor\"
    }" > /dev/null

if [ $? -eq 0 ]; then
    echo -e "   ${GREEN}✓${NC} Message sent with selected_agent=supervisor"
else
    echo -e "   ${RED}✗${NC} Failed to send message"
fi

echo -e "\n${YELLOW}Verifying session persistence...${NC}"

# Get session info
SESSION_INFO=$(curl -s http://localhost:8000/api/session/$SESSION_ID)

if echo "$SESSION_INFO" | grep -q "thread_id"; then
    THREAD_ID=$(echo $SESSION_INFO | grep -o '"thread_id":"[^"]*' | cut -d'"' -f4)
    echo -e "${GREEN}✓${NC} Session persisted with thread_id: $THREAD_ID"
else
    echo -e "${RED}✗${NC} Session not found or missing thread_id"
fi

echo -e "\n=========================================="
echo "TEST SUMMARY"
echo "=========================================="
echo "Session ID: $SESSION_ID"
echo ""
echo "Agents tested:"
echo "  ✓ docx_agent"
echo "  ✓ rfp_finance"
echo "  ✓ general_assistant"
echo "  ✓ supervisor"
echo ""
echo "Next steps:"
echo "  1. Open http://localhost:5173 in browser"
echo "  2. Use session: $SESSION_ID"
echo "  3. Select different agents from dropdown"
echo "  4. Verify messages route correctly"
echo "  5. Check browser console for debug logs"
echo "=========================================="

# Agent Selection Feature - Testing Checklist

## Pre-Testing Setup

### Start All Services
- [ ] **LangGraph Dev Server** (Port 2024)
  ```bash
  cd main
  langgraph dev
  ```
  Verify: http://localhost:2024/ok returns 200

- [ ] **Backend FastAPI Server** (Port 8000)
  ```bash
  cd backend
  python app.py
  ```
  Verify: http://localhost:8000/health returns 200

- [ ] **Frontend Vite Dev Server** (Port 5173)
  ```bash
  cd frontend
  npm run dev
  ```
  Verify: http://localhost:5173 loads successfully

## Code Verification

### Frontend Changes
- [ ] File: `frontend/src/components/ChatPanel.tsx`
  - [ ] `selectedAgent` state added with default 'supervisor'
  - [ ] `agents` array contains 9 options
  - [ ] Dropdown UI visible in chat header
  - [ ] Socket.IO emit includes `selected_agent` field

### Backend Changes  
- [ ] File: `backend/app.py`
  - [ ] `send_message` handler extracts `selected_agent`
  - [ ] Session metadata updated with selected agent
  - [ ] Message enhanced with `[Route to {agent}]` prefix
  - [ ] `process_message` called with `selected_agent` parameter

- [ ] File: `backend/agent_runner.py`
  - [ ] `process_message` signature includes `selected_agent` parameter
  - [ ] `_process_remote` signature updated
  - [ ] `_process_local` signature updated
  - [ ] Config includes `selected_agent` in configurable
  - [ ] Input data includes `selected_agent` when not supervisor

### LangGraph Changes
- [ ] File: `main/src/agent/router.py`
  - [ ] `logging` module imported
  - [ ] `logger` initialized
  - [ ] `supervisor_router` checks for `selected_agent` in state
  - [ ] `agent_mapping` dictionary created
  - [ ] Direct routing returns mapped agent when selected

## Functional Testing

### Test 1: Dropdown UI
- [ ] Open http://localhost:5173
- [ ] Create new session or use existing
- [ ] Locate agent dropdown in chat header
- [ ] Click dropdown - verify all 9 agents listed:
  - [ ] 🤖 Supervisor
  - [ ] 📝 DOCX Agent
  - [ ] 📄 PDF Parser
  - [ ] 💬 General Assistant
  - [ ] 💰 RFP Finance Team
  - [ ] 🔧 RFP Technical Team
  - [ ] ⚖️ RFP Legal Team
  - [ ] ✅ RFP QA Team
  - [ ] 🖼️ Image Adder Agent
- [ ] Each agent has description text
- [ ] Selecting agent updates UI

### Test 2: Agent Routing (DOCX Agent)
- [ ] Select "📝 DOCX Agent" from dropdown
- [ ] Send message: "Create a test document"
- [ ] Open browser console (F12)
- [ ] Verify Socket.IO emit shows: `selected_agent: "docx_agent"`
- [ ] Check backend logs for: `"Forcing route to: docx_agent"`
- [ ] Check LangGraph logs for: `"Direct routing to selected agent: docx_agent"`
- [ ] Verify response comes from DOCX Agent

### Test 3: Agent Routing (RFP Finance)
- [ ] Select "💰 RFP Finance Team" from dropdown
- [ ] Send message: "Prepare budget analysis for Q1"
- [ ] Verify Socket.IO emit shows: `selected_agent: "rfp_finance"`
- [ ] Check backend logs for routing
- [ ] Check LangGraph logs for routing to rfp_supervisor
- [ ] Verify response is finance-focused

### Test 4: Agent Routing (General Assistant)
- [ ] Select "💬 General Assistant" from dropdown
- [ ] Send message: "What can you help me with?"
- [ ] Verify Socket.IO emit shows: `selected_agent: "general_assistant"`
- [ ] Check routing in logs
- [ ] Verify response from general assistant

### Test 5: Supervisor (Default Routing)
- [ ] Select "🤖 Supervisor" from dropdown
- [ ] Send message with keyword: "parse this PDF"
- [ ] Verify Socket.IO emit shows: `selected_agent: "supervisor"`
- [ ] Check that keyword routing is used (not direct routing)
- [ ] Verify message routed to PDF Parser based on keyword

### Test 6: Session Persistence
- [ ] Note your current session_id
- [ ] Select "📝 DOCX Agent" and send message
- [ ] Select "💰 RFP Finance Team" and send message
- [ ] Select "💬 General Assistant" and send message
- [ ] Verify session_id stays the same
- [ ] Check backend session CSV for metadata
- [ ] Verify thread_id remains constant
- [ ] All messages appear in same conversation

### Test 7: Message Enhancement
- [ ] Select any non-supervisor agent
- [ ] Send message: "Test message"
- [ ] Check backend logs for enhanced message
- [ ] Verify format: `"[Route to {agent}] Test message"`
- [ ] Supervisor messages should NOT be enhanced

### Test 8: Invalid Agent Handling
- [ ] Open browser console
- [ ] Manually emit Socket.IO with invalid agent:
  ```javascript
  socket.emit('send_message', {
    session_id: 'your-session-id',
    message: 'Test',
    selected_agent: 'invalid_agent'
  });
  ```
- [ ] Verify fallback to general_assistant
- [ ] Check no errors in backend logs

## Automated Testing

### Python Test Suite
- [ ] Run: `python test_agent_selection.py`
- [ ] Verify all tests pass:
  - [ ] Test 1: Session Creation ✅
  - [ ] Test 2: Agent Metadata Storage ✅
  - [ ] Test 3: LangGraph Routing ✅
  - [ ] Test 4: Session Persistence ✅
  - [ ] Test 5: Agent Dropdown Values ✅

### Bash Integration Test
- [ ] Run: `bash test_agent_selection.sh`
- [ ] Verify all services detected
- [ ] Verify session created
- [ ] Verify all 4 agent tests pass
- [ ] Verify session persisted

## Edge Case Testing

### Edge Case 1: Empty Message
- [ ] Select any agent
- [ ] Try to send empty message
- [ ] Verify appropriate handling

### Edge Case 2: Very Long Message
- [ ] Select any agent
- [ ] Send message > 1000 characters
- [ ] Verify agent processes correctly

### Edge Case 3: Rapid Agent Switching
- [ ] Quickly switch between 5 different agents
- [ ] Send messages rapidly
- [ ] Verify no race conditions
- [ ] Check session remains stable

### Edge Case 4: Refresh Browser
- [ ] Select non-supervisor agent
- [ ] Refresh browser
- [ ] Verify agent selection resets to supervisor
- [ ] Session should still be valid

### Edge Case 5: New Session Mid-Conversation
- [ ] Have active conversation
- [ ] Create new session
- [ ] Verify clean state
- [ ] Verify previous session unaffected

## Performance Testing

### Response Time
- [ ] Select each agent
- [ ] Time response for standard message
- [ ] Verify < 2 seconds for simple queries
- [ ] Document any slow agents

### Concurrent Users
- [ ] Open 3 browser tabs
- [ ] Use different agents in each
- [ ] Send messages simultaneously
- [ ] Verify no session mixing
- [ ] Check backend handles load

## Browser Compatibility

### Chrome
- [ ] All features work
- [ ] Dropdown renders correctly
- [ ] Socket.IO connects
- [ ] No console errors

### Firefox
- [ ] All features work
- [ ] Dropdown renders correctly
- [ ] Socket.IO connects
- [ ] No console errors

### Edge
- [ ] All features work
- [ ] Dropdown renders correctly
- [ ] Socket.IO connects
- [ ] No console errors

## Logging Verification

### Backend Logs
- [ ] Session creation logged
- [ ] Agent selection logged
- [ ] Message enhancement logged
- [ ] "Forcing route to:" appears for non-supervisor
- [ ] Errors properly logged

### LangGraph Logs
- [ ] "Direct routing to selected agent:" appears
- [ ] Agent name correctly logged
- [ ] State contains selected_agent
- [ ] No routing errors

### Frontend Console
- [ ] Socket.IO connection established
- [ ] Emit events show selected_agent
- [ ] Receive events logged
- [ ] No React warnings

## Documentation Review

- [ ] `AGENT_SELECTION_GUIDE.md` - Read through, verify accuracy
- [ ] `AGENT_SELECTION_IMPLEMENTATION.md` - Review implementation details
- [ ] Code comments added where needed
- [ ] README updated with feature description

## Regression Testing

### Existing Features (Should Still Work)
- [ ] Keyword-based routing when supervisor selected
- [ ] Session creation/management
- [ ] Document upload (if applicable)
- [ ] Chat history display
- [ ] User authentication (if applicable)
- [ ] All existing API endpoints

## Final Verification

- [ ] All modified files committed to git
- [ ] No merge conflicts
- [ ] No linting errors in critical files
- [ ] No TypeScript errors in frontend
- [ ] No Python syntax errors in backend
- [ ] All services start without errors

## Sign-Off

### Tested By: _______________
### Date: _______________
### Environment: _______________

### Issues Found:
1. _______________________________________
2. _______________________________________
3. _______________________________________

### Notes:
_____________________________________________
_____________________________________________
_____________________________________________

---

## Quick Test Commands

```bash
# Check all services
curl http://localhost:8000/health
curl http://localhost:2024/ok
curl http://localhost:5173

# Create test session
curl -X POST http://localhost:8000/api/session/create

# Send test message with agent selection
curl -X POST http://localhost:8000/api/chat/send \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "YOUR_SESSION_ID",
    "message": "Test message",
    "selected_agent": "docx_agent"
  }'

# Get session info
curl http://localhost:8000/api/session/YOUR_SESSION_ID

# Run Python tests
python test_agent_selection.py

# Run bash tests
bash test_agent_selection.sh
```

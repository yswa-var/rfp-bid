# Complete Approval Flow - Curl Test Commands

Quick reference for testing the DOCX Agent approval flow with curl commands.

---

## 1. Health Check

Check if the server is running:

```bash
curl -X GET 'http://localhost:8080/health' | python3 -m json.tool
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-09-30T13:31:35.678953",
  "active_sessions": 4
}
```

---

## 2. Query Operation (No Approval Required)

Read-only operations don't require approval:

```bash
curl -X POST 'http://localhost:8080/api/chat' \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "test_user_123",
    "message": "What is in the Executive Overview section?",
    "platform": "api"
  }' | python3 -m json.tool
```

**Expected Response:**
```json
{
  "message": "The Executive Overview contains...",
  "requires_approval": false,
  "approval_data": null,
  "session_id": "abc-123",
  "status": "completed"
}
```

---

## 3. Edit Operation - Request Approval ✏️

Write operations trigger the approval flow:

```bash
curl -X POST 'http://localhost:8080/api/chat' \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "test_user_123",
    "message": "Change the CEO name in Executive Overview to Tony Stark",
    "platform": "api"
  }' | python3 -m json.tool
```

**Expected Response:**
```json
{
  "message": "🔔 **Approval Required**\n\n**Edit Operation**\n- Location: ['body', 0, 0, 0, 76]\n- New text: Tony Stark...\n\nDo you approve this change? (yes/no)\n\nReply with:\n• `/approve` or `yes` to proceed\n• `/reject` or `no` to cancel",
  "requires_approval": true,
  "approval_data": {
    "type": "approval_request",
    "tool_name": "apply_edit",
    "tool_call_id": "call_xxx",
    "args": {
      "anchor": ["body", 0, 0, 0, 76],
      "new_text": "Tony Stark"
    },
    "description": "**Edit Operation**..."
  },
  "session_id": "abc-123",
  "status": "waiting_approval"
}
```

**📝 Save the `session_id` for the next step!**

---

## 4. Approve the Edit ✅

To approve and execute the edit:

```bash
curl -X POST 'http://localhost:8080/api/approve' \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "test_user_123",
    "session_id": "abc-123",
    "approved": true,
    "platform": "api"
  }' | python3 -m json.tool
```

**Expected Response:**
```json
{
  "message": "The CEO name has been updated to Tony Stark.",
  "requires_approval": false,
  "approval_data": null,
  "session_id": "abc-123",
  "status": "completed"
}
```

---

## 5. Reject an Edit ❌

To reject and cancel the operation:

```bash
# First, trigger another edit
curl -X POST 'http://localhost:8080/api/chat' \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "test_user_123",
    "message": "Change the company name to Wayne Enterprises",
    "platform": "api"
  }' | python3 -m json.tool

# Then reject it (use the session_id from the response)
curl -X POST 'http://localhost:8080/api/approve' \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "test_user_123",
    "session_id": "abc-456",
    "approved": false,
    "platform": "api"
  }' | python3 -m json.tool
```

**Expected Response:**
```json
{
  "message": "The operation was canceled. If you'd like to proceed with this change, please let me know.",
  "requires_approval": false,
  "approval_data": null,
  "session_id": "abc-456",
  "status": "completed"
}
```

---

## 6. View User Sessions

Get all sessions for a specific user:

```bash
curl -X GET 'http://localhost:8080/api/sessions/test_user_123' | python3 -m json.tool
```

**Expected Response:**
```json
{
  "user_id": "test_user_123",
  "sessions": [
    {
      "session_id": "abc-123",
      "user_id": "test_user_123",
      "platform": "api",
      "thread_id": "thread-xxx",
      "pending_approval": false,
      "created_at": "2025-09-30 13:00:00",
      "last_activity": "2025-09-30 13:05:00"
    }
  ]
}
```

---

## 7. List All Sessions (Admin)

View all active sessions:

```bash
curl -X GET 'http://localhost:8080/api/sessions' | python3 -m json.tool
```

**Expected Response:**
```json
{
  "active_sessions": [...],
  "count": 5
}
```

---

## 8. Delete a Session

Remove a specific session:

```bash
curl -X DELETE 'http://localhost:8080/api/sessions/abc-123' | python3 -m json.tool
```

**Expected Response:**
```json
{
  "status": "deleted",
  "session_id": "abc-123"
}
```

---

## 9. Try to Send Message with Pending Approval

If a user has a pending approval, they can't send new messages:

```bash
# First message - creates pending approval
curl -X POST 'http://localhost:8080/api/chat' \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "blocked_user",
    "message": "Update the title",
    "platform": "api"
  }' | python3 -m json.tool

# Second message - should be blocked
curl -X POST 'http://localhost:8080/api/chat' \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "blocked_user",
    "message": "What is in the document?",
    "platform": "api"
  }' | python3 -m json.tool
```

**Expected Response (Second Request):**
```json
{
  "message": "You have a pending approval request. Please respond with /approve or /reject first.",
  "requires_approval": false,
  "approval_data": null,
  "session_id": "abc-789",
  "status": "error"
}
```

---

## Complete Flow Example

Here's a complete flow from start to finish:

```bash
# 1. Check server health
curl -X GET 'http://localhost:8080/health'

# 2. Send a query (no approval needed)
curl -X POST 'http://localhost:8080/api/chat' \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "demo_user",
    "message": "Show me the document structure",
    "platform": "api"
  }'

# 3. Request an edit (triggers approval)
curl -X POST 'http://localhost:8080/api/chat' \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "demo_user",
    "message": "In the Executive Overview section, change the CEO name from Yashaswa Varshney to Tony Stark",
    "platform": "api"
  }'

# Response will contain: session_id = "xyz-123"

# 4. Approve the edit
curl -X POST 'http://localhost:8080/api/approve' \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "demo_user",
    "session_id": "xyz-123",
    "approved": true,
    "platform": "api"
  }'

# 5. Verify the change
curl -X POST 'http://localhost:8080/api/chat' \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "demo_user",
    "message": "What is the CEO name in Executive Overview?",
    "platform": "api"
  }'
```

---

## Testing Different Edit Operations

### 1. Single Paragraph Edit
```bash
curl -X POST 'http://localhost:8080/api/chat' \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "edit_test",
    "message": "In the first paragraph, change the company name to Stark Industries",
    "platform": "api"
  }'
```

### 2. Section Update
```bash
curl -X POST 'http://localhost:8080/api/chat' \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "edit_test",
    "message": "Update the Technical Approach section with: We will use cutting-edge AI technology",
    "platform": "api"
  }'
```

### 3. Add New Content
```bash
curl -X POST 'http://localhost:8080/api/chat' \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "edit_test",
    "message": "Add a new paragraph to the conclusion: We look forward to working with you",
    "platform": "api"
  }'
```

---

## Environment Variables

Make sure these are set in `/backend/.env`:

```bash
OPENAI_API_KEY=sk-proj-your-key-here
MODEL=openai/gpt-3.5-turbo
DEBUG=true
```

---

## Troubleshooting

### Error: Connection Refused
```bash
# Check if server is running
curl http://localhost:8080/health

# If not running, start it:
cd /Users/yash/Documents/rfp/DOCX-agent/backend
source ../venv/bin/activate
python app.py
```

### Error: API Key Not Set
```bash
# Check .env file
cat /Users/yash/Documents/rfp/DOCX-agent/backend/.env

# Restart server after adding API key
pkill -f "python app.py"
cd /Users/yash/Documents/rfp/DOCX-agent/backend
source ../venv/bin/activate
export $(cat .env | grep -v '^#' | xargs)
python app.py
```

### Error: Session Not Found
The session may have expired. Start a new conversation with a fresh user_id.

---

## Quick Test Script

Want to run all tests automatically? Use:

```bash
cd /Users/yash/Documents/rfp/DOCX-agent/backend
chmod +x TEST_APPROVAL_FLOW.sh
./TEST_APPROVAL_FLOW.sh
```

This will run through all test scenarios interactively.

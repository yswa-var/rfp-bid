# 📖 Using Swagger Docs to Create User Sessions

## Quick Start

### 1. Start the Backend

```bash
cd backend
./start.sh
```

### 2. Open Swagger Docs

Visit: **http://localhost:8000/docs**

You'll see the interactive API documentation with all available endpoints.

---

## Creating a User Session

### Method 1: Send a Chat Message (Recommended)

Sessions are **automatically created** when a user sends their first message!

#### Step-by-Step:

**1. Find the `/api/chat` endpoint**
   - Look for the green `POST` button
   - Click on `/api/chat` to expand it

**2. Click "Try it out"**
   - This makes the form editable

**3. Fill in the Request Body:**

```json
{
  "user_id": "test_user_123",
  "message": "Show me the document outline",
  "platform": "api",
  "metadata": null
}
```

**Fields explained:**
- `user_id`: Your unique user identifier (e.g., `telegram_12345`, `discord_67890`)
- `message`: The message to send to the agent
- `platform`: Platform name (`api`, `telegram`, `discord`, `slack`, etc.)
- `metadata`: Optional extra data (can be `null`)

**4. Click "Execute"**

**5. See the Response:**

```json
{
  "message": "Here's the document outline...",
  "requires_approval": false,
  "session_id": "abc-123-def-456",
  "status": "completed"
}
```

**✅ Session Created!** 

The `session_id` in the response is your new session. It's also saved to `sessions.csv`.

---

## Viewing Sessions

### Check All Active Sessions

**1. Find `/api/sessions` endpoint**
   - GET method (blue button)

**2. Click "Try it out"**

**3. Click "Execute"**

**Response:**
```json
{
  "active_sessions": [
    {
      "session_id": "abc-123-def-456",
      "user_id": "test_user_123",
      "platform": "api",
      "thread_id": "xyz-789",
      "created_at": "2025-09-30T10:30:00",
      "last_activity": "2025-09-30T10:35:00",
      "has_pending_approval": false,
      "metadata": {}
    }
  ],
  "count": 1
}
```

### Check Sessions for Specific User

**1. Find `/api/sessions/{user_id}` endpoint**
   - GET method (blue button)

**2. Click "Try it out"**

**3. Enter user_id:**
```
test_user_123
```

**4. Click "Execute"**

**Response:**
```json
{
  "user_id": "test_user_123",
  "sessions": [
    {
      "session_id": "abc-123-def-456",
      "user_id": "test_user_123",
      "platform": "api",
      "thread_id": "xyz-789",
      "created_at": "2025-09-30T10:30:00",
      "last_activity": "2025-09-30T10:35:00",
      "has_pending_approval": false,
      "metadata": {}
    }
  ]
}
```

---

## Testing the Approval Workflow

### 1. Send a Write Operation

**Endpoint:** `POST /api/chat`

**Request:**
```json
{
  "user_id": "test_user_123",
  "message": "Update section 2.1 to say 'New Company Overview'",
  "platform": "api",
  "metadata": null
}
```

**Response (if approval required):**
```json
{
  "message": "🔔 **Approval Required**\n\n**Edit Operation**\n- Location: [\"body\", 0, 0, 0, 95]\n- New text: New Company Overview\n\nReply with:\n• `/approve` or `yes` to proceed\n• `/reject` or `no` to cancel",
  "requires_approval": true,
  "approval_data": {
    "type": "approval_request",
    "tool_name": "apply_edit",
    "tool_call_id": "call_123",
    "args": {
      "anchor": ["body", 0, 0, 0, 95],
      "new_text": "New Company Overview"
    },
    "description": "..."
  },
  "session_id": "abc-123-def-456",
  "status": "waiting_approval"
}
```

### 2. Approve the Operation

**Endpoint:** `POST /api/approve`

**Request:**
```json
{
  "user_id": "test_user_123",
  "session_id": "abc-123-def-456",
  "approved": true,
  "platform": "api"
}
```

**Response:**
```json
{
  "message": "✅ Operation approved and executed successfully",
  "requires_approval": false,
  "session_id": "abc-123-def-456",
  "status": "completed"
}
```

---

## Example Workflows

### Workflow 1: Simple Q&A

```
1. POST /api/chat
   {
     "user_id": "user_001",
     "message": "What's in the document?"
   }
   
   ✅ Response: Agent's answer
   ✅ Session auto-created
   ✅ No approval needed
```

### Workflow 2: Edit with Approval

```
1. POST /api/chat
   {
     "user_id": "user_001",
     "message": "Update section 3"
   }
   
   ⚠️ Response: Approval required
   
2. POST /api/approve
   {
     "user_id": "user_001",
     "session_id": "from_step_1",
     "approved": true
   }
   
   ✅ Response: Operation completed
```

### Workflow 3: Multi-turn Conversation

```
1. POST /api/chat
   {
     "user_id": "user_001",
     "message": "Show me section 2"
   }
   
   ✅ Session created: abc-123

2. POST /api/chat (same user_id)
   {
     "user_id": "user_001",
     "message": "Search for 'budget'"
   }
   
   ✅ Uses same session: abc-123
   ✅ Conversation history maintained
```

---

## Checking the CSV File

After creating sessions via Swagger, verify they're saved:

```bash
cd backend
cat sessions.csv
```

You should see your test sessions!

---

## Common Use Cases

### Use Case 1: Testing as Different Users

**Test User 1 (Telegram):**
```json
{
  "user_id": "telegram_12345",
  "message": "Hello",
  "platform": "telegram"
}
```

**Test User 2 (Discord):**
```json
{
  "user_id": "discord_67890",
  "message": "Hello",
  "platform": "discord"
}
```

Each gets their own session!

### Use Case 2: Metadata Tracking

```json
{
  "user_id": "user_001",
  "message": "Hello",
  "platform": "api",
  "metadata": {
    "source": "web_app",
    "ip_address": "192.168.1.1",
    "user_agent": "Chrome"
  }
}
```

Metadata is stored in the session!

### Use Case 3: Deleting Sessions

**Endpoint:** `DELETE /api/sessions/{session_id}`

**Steps:**
1. Find the endpoint
2. Click "Try it out"
3. Enter session_id: `abc-123-def-456`
4. Click "Execute"

**Response:**
```json
{
  "status": "deleted",
  "session_id": "abc-123-def-456"
}
```

---

## Health Check

Test if backend is running:

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-09-30T10:30:00.000Z",
  "active_sessions": 5
}
```

---

## Tips for Using Swagger

### 1. Schemas

Click on "Schemas" at the bottom to see all data models:
- `ChatMessage` - Request format
- `ChatResponse` - Response format
- `ApprovalRequest` - Approval format
- `Session` - Session structure

### 2. Copy as cURL

After executing a request, you can copy it as a cURL command:
- Scroll down to "Curl" section
- Copy the command
- Use in terminal or scripts

### 3. Save Responses

Click "Download" to save responses for testing or documentation.

### 4. Authorization (Future)

If you add API key authentication:
- Click the "Authorize" button at top
- Enter your API key
- All requests will include it

---

## Testing Different Scenarios

### Scenario 1: New User First Message

```json
POST /api/chat
{
  "user_id": "new_user_999",
  "message": "What can you do?",
  "platform": "telegram"
}
```

✅ Creates new session  
✅ Starts new conversation  
✅ Returns agent's capabilities  

### Scenario 2: Existing User Returns

```json
POST /api/chat
{
  "user_id": "new_user_999",
  "message": "Show me section 1",
  "platform": "telegram"
}
```

✅ Uses existing session  
✅ Maintains conversation context  
✅ Continues from previous messages  

### Scenario 3: User on Different Platform

```json
POST /api/chat
{
  "user_id": "new_user_999",
  "message": "Hello",
  "platform": "discord"
}
```

✅ Creates separate session for Discord  
✅ Different conversation per platform  
✅ User can have multiple sessions  

### Scenario 4: Session Timeout Test

1. Create a session
2. Wait 60+ minutes (or change timeout in `.env`)
3. Try to use it

✅ Session expired and removed  
✅ New session created automatically  

---

## Debugging with Swagger

### Check Session State

1. Send message: `POST /api/chat`
2. Get session: `GET /api/sessions/{user_id}`
3. Check fields:
   - `last_activity` - Should update
   - `has_pending_approval` - Shows if waiting
   - `thread_id` - LangGraph conversation ID

### Monitor Approval Flow

1. Send write operation
2. Check `requires_approval` = `true`
3. Get session - verify `has_pending_approval` = `true`
4. Send approval
5. Get session - verify `has_pending_approval` = `false`

---

## Screenshot Guide

### 1. Swagger Homepage
```
http://localhost:8000/docs

You'll see:
- API title and version
- List of all endpoints
- Grouped by tags
```

### 2. Expanding an Endpoint
```
Click on any endpoint (e.g., POST /api/chat)
Shows:
- Parameters
- Request body schema
- Response schemas
- "Try it out" button
```

### 3. Making a Request
```
1. Click "Try it out"
2. Edit JSON in Request body
3. Click "Execute"
4. See response below
```

---

## Quick Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | API info |
| `/health` | GET | Health check |
| `/api/chat` | POST | Send message (creates session) |
| `/api/approve` | POST | Handle approval |
| `/api/sessions` | GET | List all sessions |
| `/api/sessions/{user_id}` | GET | Get user's sessions |
| `/api/sessions/{session_id}` | DELETE | Delete session |

---

## Example Script from Swagger

After testing in Swagger, you can generate code:

### Python Example
```python
import requests

# Generated from Swagger
response = requests.post(
    'http://localhost:8000/api/chat',
    headers={'Content-Type': 'application/json'},
    json={
        'user_id': 'test_user_123',
        'message': 'Hello',
        'platform': 'api'
    }
)

result = response.json()
print(f"Session ID: {result['session_id']}")
print(f"Message: {result['message']}")
```

### cURL Example
```bash
# Generated from Swagger
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_123",
    "message": "Hello",
    "platform": "api"
  }'
```

---

## Summary

**To create a user session using Swagger:**

1. ✅ Visit http://localhost:8000/docs
2. ✅ Find `POST /api/chat`
3. ✅ Click "Try it out"
4. ✅ Fill in user_id and message
5. ✅ Click "Execute"
6. ✅ Session auto-created!

**Check your session:**
- In response: Look for `session_id`
- In API: `GET /api/sessions/{user_id}`
- In file: `cat backend/sessions.csv`

**The session includes:**
- Unique session ID
- User ID
- Platform
- Thread ID (for LangGraph)
- Creation time
- Last activity
- Pending approvals

**Sessions are automatically:**
- ✅ Created on first message
- ✅ Saved to CSV
- ✅ Reused for same user + platform
- ✅ Loaded on server restart
- ✅ Cleaned up after timeout

---

**Ready to test?** Visit http://localhost:8000/docs and start creating sessions! 🚀

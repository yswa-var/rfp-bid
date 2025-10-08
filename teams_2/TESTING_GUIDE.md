# Testing Guide - Teams Bot with LangGraph

Comprehensive testing guide for the Teams + LangGraph integration.

## Testing Levels

1. **Unit Tests** - Individual components
2. **Integration Tests** - Bot + LangGraph Server
3. **End-to-End Tests** - Full user flow
4. **Load Tests** - Performance and scalability

## Prerequisites

Ensure both services are running:
```bash
# Terminal 1: LangGraph Server
cd main && langgraph dev

# Terminal 2: Teams Bot
cd teams_2 && ./start.sh
```

## 1. Health Check Tests

### Test Server Connectivity

```bash
# Check LangGraph Server
curl http://localhost:8123/ok
# Expected: {"ok": true}

# Check Teams Bot
curl http://localhost:3978/health
# Expected: {"status": "healthy", "langgraph_connection": "ok", ...}

# Check thread mappings
curl http://localhost:3978/debug/threads
# Expected: {"count": 0, "mappings": {}}
```

## 2. Bot Framework Emulator Tests

### Setup
1. Open Bot Framework Emulator
2. File → Open Bot
3. Bot URL: `http://localhost:3978/api/messages`
4. App ID: (leave empty for local)
5. Password: (leave empty for local)

### Test Cases

#### TC1: Welcome Message
```
Action: Add bot to conversation
Expected: Welcome message with capabilities
```

#### TC2: Basic Conversation
```
User: Hello
Expected: Greeting response from supervisor
```

#### TC3: Simple Query
```
User: What can you help me with?
Expected: List of capabilities (document ops, RFP, Q&A, PDF parsing)
```

#### TC4: Thread Persistence
```
User: Remember that my name is John
Bot: [Response acknowledging]
User: What's my name?
Expected: Bot remembers "John" (thread maintains context)
```

#### TC5: PDF Parser Route
```
User: Parse the PDF files in the example-PDF folder
Expected: 
- Message routed to pdf_parser
- Files are indexed
- Success confirmation
```

#### TC6: General Assistant Route
```
User: What information do you have about green hydrogen?
Expected:
- Message routed to general_assistant
- RAG-based response using indexed documents
```

#### TC7: DOCX Agent Route (Read)
```
User: Read the master.docx file
Expected:
- Message routed to docx_agent
- Document content returned
- No approval required (read operation)
```

#### TC8: DOCX Agent Route (Write) - Approval Flow
```
User: Edit the master.docx and change the title to "Updated Title"
Expected:
1. Bot responds with approval request
2. Displays operation details
3. Shows /approve and /reject buttons

User: /approve
Expected:
1. Bot processes approval
2. Executes edit operation
3. Returns success message
```

#### TC9: Approval Rejection
```
User: Delete all content from master.docx
Expected: Approval request

User: /reject
Expected: 
- Operation cancelled
- No changes made
- Confirmation message
```

#### TC10: Multiple Conversations
```
Test: Open multiple conversation windows
Action: Send different messages in each
Expected: Each maintains separate context (separate threads)
```

## 3. API Tests with curl

### Test Message Endpoint

```bash
# Send a message
curl -X POST http://localhost:3978/api/messages \
  -H "Content-Type: application/json" \
  -d '{
    "type": "message",
    "id": "test-001",
    "timestamp": "2025-01-01T00:00:00.000Z",
    "channelId": "test",
    "from": {
      "id": "user1",
      "name": "Test User"
    },
    "conversation": {
      "id": "test-conv-1"
    },
    "recipient": {
      "id": "bot1",
      "name": "Bot"
    },
    "text": "Hello bot",
    "serviceUrl": "http://localhost:3978"
  }'
```

### Test Thread Creation

```bash
# Send first message (creates thread)
curl -X POST http://localhost:3978/api/messages \
  -H "Content-Type: application/json" \
  -d '{"type":"message","conversation":{"id":"test-1"},"from":{"id":"user1","name":"User"},"text":"Hello"}'

# Check thread was created
curl http://localhost:3978/debug/threads
# Should show one mapping: test-1 → <thread_id>

# Send second message (reuses thread)
curl -X POST http://localhost:3978/api/messages \
  -H "Content-Type: application/json" \
  -d '{"type":"message","conversation":{"id":"test-1"},"from":{"id":"user1","name":"User"},"text":"Remember this"}'

# Thread count should still be 1
curl http://localhost:3978/debug/threads
```

## 4. LangGraph Server Tests

### Direct Thread Testing

```bash
# Create thread directly
curl -X POST http://localhost:8123/threads \
  -H "Content-Type: application/json" \
  -d '{
    "metadata": {
      "test": "direct_thread",
      "platform": "test"
    }
  }'

# Save the thread_id from response
THREAD_ID="<thread_id_here>"

# Create run
curl -X POST http://localhost:8123/threads/$THREAD_ID/runs/wait \
  -H "Content-Type: application/json" \
  -d '{
    "assistant_id": "agent",
    "input": {
      "messages": [
        {"role": "user", "content": "Hello from direct API"}
      ]
    }
  }'
```

### Test Interrupt Handling

```bash
# Send request that triggers approval
curl -X POST http://localhost:8123/threads/$THREAD_ID/runs/wait \
  -H "Content-Type: application/json" \
  -d '{
    "assistant_id": "agent",
    "input": {
      "messages": [
        {"role": "user", "content": "Edit master.docx and change title to Test"}
      ]
    }
  }'

# Check for interrupted status
# Response should have: "status": "interrupted"

# Get thread state
curl http://localhost:8123/threads/$THREAD_ID/state

# Look for interrupt data in response
```

## 5. Approval Flow Tests

### Test Complete Approval Cycle

```python
# test_approval_flow.py
import asyncio
from langgraph_sdk import get_client

async def test_approval_flow():
    client = get_client(url="http://localhost:8123")
    
    # Create thread
    thread = await client.threads.create()
    thread_id = thread["thread_id"]
    print(f"Created thread: {thread_id}")
    
    # Send message requiring approval
    run = await client.runs.wait(
        thread_id=thread_id,
        assistant_id="agent",
        input={
            "messages": [
                {"role": "user", "content": "Edit master.docx title to 'Test'"}
            ]
        }
    )
    
    print(f"Run status: {run['status']}")
    assert run["status"] == "interrupted", "Should be interrupted for approval"
    
    # Get state
    state = await client.threads.get_state(thread_id)
    print(f"State: {state}")
    
    # Simulate approval
    await client.threads.update_state(
        thread_id=thread_id,
        values={"approval": "yes"}
    )
    
    # Continue run
    run2 = await client.runs.wait(
        thread_id=thread_id,
        assistant_id="agent",
        input=None
    )
    
    print(f"Final run status: {run2['status']}")
    assert run2["status"] == "success", "Should complete successfully"
    
    print("✅ Approval flow test passed")

if __name__ == "__main__":
    asyncio.run(test_approval_flow())
```

Run the test:
```bash
cd teams_2
python test_approval_flow.py
```

## 6. Load Testing

### Simple Load Test

```bash
# test_load.sh
#!/bin/bash

echo "Starting load test..."
CONCURRENT=10
REQUESTS=100

for i in $(seq 1 $CONCURRENT); do
  (
    for j in $(seq 1 $(($REQUESTS / $CONCURRENT))); do
      curl -X POST http://localhost:3978/api/messages \
        -H "Content-Type: application/json" \
        -d "{\"type\":\"message\",\"conversation\":{\"id\":\"load-test-$i\"},\"from\":{\"id\":\"user$i\",\"name\":\"User$i\"},\"text\":\"Hello $j\"}" \
        > /dev/null 2>&1
      echo "Thread $i: Request $j"
    done
  ) &
done

wait
echo "Load test complete"
```

Run:
```bash
chmod +x test_load.sh
./test_load.sh
```

Check results:
```bash
curl http://localhost:3978/debug/threads | jq '.count'
# Should show CONCURRENT threads created
```

## 7. Error Handling Tests

### TC11: LangGraph Server Down
```
1. Stop LangGraph Server (Ctrl+C in terminal)
2. Send message in Bot Framework Emulator
Expected: Error message about server connection
```

### TC12: Invalid Input
```
User: [Send very long message, 10000+ characters]
Expected: Graceful handling or appropriate error
```

### TC13: Timeout Handling
```
User: [Trigger long-running operation]
Expected: 
- Either completes within timeout
- Or returns timeout error
- No hanging connections
```

### TC14: Malformed Approval
```
User: Trigger approval request
Bot: [Shows approval request]
User: maybe
Expected: Bot asks for clear yes/no
```

## 8. Thread Management Tests

### Test Thread Cleanup

```python
# test_cleanup.py
import asyncio
from thread_manager import ThreadManager

async def test_cleanup():
    manager = ThreadManager("test_mappings.json")
    
    # Create old mappings
    await manager.create_mapping(
        "old-conv-1",
        "old-thread-1",
        metadata={"test": True}
    )
    
    # Manually edit JSON to make it old
    import json
    from datetime import datetime, timedelta
    
    with open("test_mappings.json", "r+") as f:
        data = json.load(f)
        old_date = (datetime.utcnow() - timedelta(days=60)).isoformat()
        data["old-conv-1"]["last_activity"] = old_date
        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()
    
    # Reload and cleanup
    manager._load_mappings()
    removed = await manager.cleanup_old_mappings(days=30)
    
    assert removed == 1, "Should remove 1 old mapping"
    print("✅ Cleanup test passed")

if __name__ == "__main__":
    asyncio.run(test_cleanup())
```

## 9. Integration Test Suite

```python
# test_integration.py
import asyncio
import aiohttp

async def test_full_integration():
    """Test complete flow from message to response"""
    
    async with aiohttp.ClientSession() as session:
        # 1. Health check
        async with session.get("http://localhost:3978/health") as resp:
            assert resp.status == 200
            data = await resp.json()
            assert data["status"] == "healthy"
            print("✅ Health check passed")
        
        # 2. Send message
        message = {
            "type": "message",
            "conversation": {"id": "integration-test-1"},
            "from": {"id": "test-user", "name": "Test User"},
            "text": "Hello bot"
        }
        
        async with session.post(
            "http://localhost:3978/api/messages",
            json=message
        ) as resp:
            assert resp.status == 200
            print("✅ Message sent successfully")
        
        # 3. Check thread created
        async with session.get("http://localhost:3978/debug/threads") as resp:
            data = await resp.json()
            assert "integration-test-1" in data["mappings"]
            print("✅ Thread mapping created")
        
        # 4. Send follow-up message
        message["text"] = "Remember my name is Alice"
        async with session.post(
            "http://localhost:3978/api/messages",
            json=message
        ) as resp:
            assert resp.status == 200
            print("✅ Follow-up message sent")
        
        # 5. Test context retention
        message["text"] = "What is my name?"
        async with session.post(
            "http://localhost:3978/api/messages",
            json=message
        ) as resp:
            assert resp.status == 200
            print("✅ Context retention test complete")
    
    print("\n🎉 All integration tests passed!")

if __name__ == "__main__":
    asyncio.run(test_full_integration())
```

Run:
```bash
pip install aiohttp
python test_integration.py
```

## 10. Monitoring and Logging

### Check Logs

```bash
# View bot logs
tail -f teams_2/teams_bot.log

# Filter for errors
grep ERROR teams_2/teams_bot.log

# Filter for approvals
grep "Approval" teams_2/teams_bot.log

# View LangGraph logs (in server terminal)
# Look for graph execution steps
```

### Monitor Performance

```bash
# Watch thread count grow
watch -n 1 'curl -s http://localhost:3978/debug/threads | jq .count'

# Monitor LangGraph server
curl http://localhost:8123/metrics
```

## Test Checklist

Use this checklist before deploying:

- [ ] All health checks pass
- [ ] Bot responds to basic messages
- [ ] Thread creation works
- [ ] Thread persistence works
- [ ] Approval flow works (approve)
- [ ] Approval flow works (reject)
- [ ] Routing works for all agents
- [ ] Error handling graceful
- [ ] Logs are clean (no unexpected errors)
- [ ] Performance acceptable under load
- [ ] Bot reconnects after LangGraph restart
- [ ] Thread mappings persist after bot restart

## Troubleshooting Failed Tests

### Test fails with connection error
```bash
# Ensure both services running
ps aux | grep "langgraph"
ps aux | grep "app.py"
```

### Test fails with timeout
```bash
# Increase timeout in .env
echo "RUN_TIMEOUT=300" >> .env
# Restart bot
```

### Thread mapping issues
```bash
# Reset mappings
rm thread_mappings.json
# Restart bot
```

### Approval flow stuck
```bash
# Check thread state
curl http://localhost:8123/threads/<thread_id>/state
```

## Next Steps

After all tests pass:
1. Deploy to staging environment
2. Run load tests at scale
3. Set up monitoring and alerts
4. Document any known issues
5. Train users on approval workflow
6. Deploy to production

## Continuous Testing

Set up automated testing:
```bash
# Add to CI/CD pipeline
pytest tests/
python test_integration.py
./test_load.sh
```

Good testing! 🧪


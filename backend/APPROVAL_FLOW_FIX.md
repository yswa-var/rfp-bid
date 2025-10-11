# Approval Flow Fix - Summary

## Problem
The approval flow was not triggering for edit operations. The API returned "Processed successfully" but:
1. No approval request was shown
2. The edit was not applied to the document
3. The graph execution wasn't properly detecting interrupts

## Root Causes
1. **Missing Context**: The graph's `call_model` function requires `runtime.context` to access the model configuration, but it wasn't being passed
2. **Missing Checkpointer**: The graph needs to be compiled with a checkpointer to enable interrupt functionality
3. **Incorrect Interrupt Detection**: The code wasn't properly checking for interrupts after graph execution

## Changes Made

### 1. Fixed `agent_runner.py` - Context Initialization
```python
def _init_local_graph(self):
    """Initialize local graph for direct execution"""
    from agent.graph import graph
    from langgraph.checkpoint.memory import MemorySaver
    
    # Create checkpointer for state management
    self._checkpointer = MemorySaver()
    
    # Compile graph with checkpointer to enable interrupts
    self._graph = builder.compile(
        checkpointer=self._checkpointer,
        name="ReAct Agent"
    )
    
    # Store default context
    self._default_context = Context()
```

**Why**: 
- Import `builder` instead of pre-compiled `graph` to add checkpointer
- Create a `Context()` instance to pass model configuration
- Compile with `MemorySaver` checkpointer to enable interrupt handling

### 2. Fixed `_process_local` - Interrupt Detection
```python
async def _process_local(self, thread_id: str, message: str) -> Dict[str, Any]:
    """Process message using local graph"""
    
    # Invoke the graph - it will stop at interrupts
    result = await self._graph.ainvoke(
        input_data,
        config=config,
        context=self._default_context  # Pass context here!
    )
    
    # Check if execution was interrupted (approval needed)
    state = await self._graph.aget_state(config)
    
    # Check for pending tasks (interrupts)
    if state.next:
        if state.tasks:
            for task in state.tasks:
                if task.interrupts:
                    interrupt_data = task.interrupts[0]
                    approval_data = interrupt_data.value
                    
                    return {
                        "message": approval_data.get("description", "Approval required"),
                        "requires_approval": True,
                        "approval_data": approval_data
                    }
```

**Why**:
- Use `ainvoke` instead of `astream` for simpler interrupt handling
- Pass `context=self._default_context` to provide model configuration
- Use `aget_state()` to check if execution was interrupted
- Check `state.tasks` for interrupt data

### 3. Fixed `resume_with_approval` - Resume Execution
```python
async def resume_with_approval(self, session_id, thread_id, approved):
    """Resume agent execution after approval decision"""
    
    approval_response = "yes" if approved else "no"
    
    # Resume the graph execution with the approval response
    result = await self._graph.ainvoke(
        Command(resume=approval_response),
        config=config,
        context=self._default_context
    )
    
    # Extract and return the response
    ...
```

**Why**:
- Use `Command(resume=approval_response)` to continue from interrupt
- Pass context to maintain model configuration

## Required Setup

### 1. Add API Key to `.env`

Edit `/Users/yash/Documents/rfp/DOCX-agent/backend/.env`:

```bash
# Required: Add your actual OpenAI API key
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxx

# Optional: Specify model (defaults to gpt-3.5-turbo)
MODEL=openai/gpt-4o-mini

# Optional: Enable debug mode
DEBUG=true
```

**OR** for Anthropic Claude:

```bash
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxx
MODEL=anthropic/claude-3-5-sonnet-20240620
DEBUG=true
```

### 2. Restart the Backend Server

```bash
cd /Users/yash/Documents/rfp/DOCX-agent/backend
source ../venv/bin/activate
python app.py
```

The server will start on `http://localhost:8080`

## Testing the Approval Flow

### Step 1: Send an Edit Request

```bash
curl -X POST 'http://localhost:8080/api/chat' \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "test_user_123",
    "message": "Change the CEO name in Executive Overview to Tony Stark",
    "platform": "api"
  }'
```

**Expected Response** (with approval required):
```json
{
  "message": "**Edit Operation**\n- Location: [...]\n- New text: Tony Stark...\n\nDo you approve this change? (yes/no)",
  "requires_approval": true,
  "approval_data": {
    "type": "approval_request",
    "tool_name": "apply_edit",
    "tool_call_id": "...",
    "args": {...},
    "description": "..."
  },
  "session_id": "...",
  "status": "waiting_approval"
}
```

### Step 2: Approve the Edit

```bash
curl -X POST 'http://localhost:8080/api/approve' \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "test_user_123",
    "session_id": "<session_id_from_step_1>",
    "approved": true,
    "platform": "api"
  }'
```

**Expected Response**:
```json
{
  "message": "✅ Edit applied successfully! Updated the document.",
  "requires_approval": false,
  "session_id": "...",
  "status": "completed"
}
```

### Step 3: Reject an Edit

```bash
curl -X POST 'http://localhost:8080/api/approve' \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "test_user_123",
    "session_id": "<session_id>",
    "approved": false,
    "platform": "api"
  }'
```

**Expected Response**:
```json
{
  "message": "❌ Operation cancelled by user",
  "requires_approval": false,
  "session_id": "...",
  "status": "completed"
}
```

## How It Works Now

### Approval Flow Diagram

```
User sends edit request
        ↓
Backend receives message → AgentRunner.process_message()
        ↓
Graph starts execution with context
        ↓
call_model node → LLM decides to use apply_edit tool
        ↓
route_model_output → Detects write operation → Routes to approval_node
        ↓
approval_node calls interrupt() → Execution pauses
        ↓
Backend detects interrupt via aget_state()
        ↓
Returns approval request to user
        ↓
User responds with /approve or /reject
        ↓
Backend receives approval → AgentRunner.resume_with_approval()
        ↓
Graph resumes with Command(resume="yes"|"no")
        ↓
If approved: tools node executes apply_edit
If rejected: rejection message added, back to call_model
        ↓
Final response returned to user
```

### Key Components

1. **Checkpointer (MemorySaver)**: Stores graph state at each step, enabling pause/resume
2. **Context**: Provides model configuration (API keys, model name) to the graph
3. **interrupt()**: LangGraph function that pauses execution and waits for input
4. **Command(resume=...)**: Resumes execution from an interrupt point
5. **aget_state()**: Retrieves current graph state including pending interrupts

## Troubleshooting

### Error: "api_key client option must be set"
- **Solution**: Add your OpenAI API key to `.env` file
- Check: `cat /Users/yash/Documents/rfp/DOCX-agent/backend/.env`

### Error: "Import agent could not be resolved"
- **Solution**: This is just a linter warning, it works at runtime
- The code adds the correct path in `sys.path.insert()`

### Approval not triggering
- **Check**: Is the operation a write operation? Only `apply_edit` triggers approval
- **Check**: Is the graph compiled with checkpointer? (Should be fixed now)
- **Check**: Is the context being passed? (Should be fixed now)

### Server not starting
- **Solution**: Activate virtual environment first
  ```bash
  source /Users/yash/Documents/rfp/DOCX-agent/venv/bin/activate
  ```

## Next Steps

1. ✅ **Add your API key** to the `.env` file
2. ✅ **Restart the server** with the virtual environment activated
3. ✅ **Test the approval flow** with the curl commands above
4. Optional: Add more tools to `WRITE_TOOLS` in `graph.py` if needed

## Files Modified

- `/Users/yash/Documents/rfp/DOCX-agent/backend/agent_runner.py`
  - Line 55-78: `_init_local_graph()` - Added checkpointer and context
  - Line 148-211: `_process_local()` - Fixed interrupt detection
  - Line 213-298: `resume_with_approval()` - Fixed resume logic

## Technical Details

### Why ainvoke instead of astream?
- `ainvoke` waits for completion or interrupt, making it easier to detect pauses
- `astream` requires parsing events to detect interrupts, which is more complex
- Both work, but `ainvoke` is simpler for this use case

### Why aget_state()?
- After `ainvoke` returns, the graph may have paused due to an interrupt
- `aget_state()` returns the current state including:
  - `state.next`: List of pending nodes (non-empty if interrupted)
  - `state.tasks`: List of tasks with interrupt data
  - `state.values`: Current state values

### Memory Management
- `MemorySaver` stores state in memory (lost on restart)
- For production, use `SqliteSaver` or `PostgresSaver` for persistence
- Each thread_id maintains separate conversation history

## References

- [LangGraph Interrupts Documentation](https://langchain-ai.github.io/langgraph/concepts/interrupts/)
- [LangGraph Checkpointers](https://langchain-ai.github.io/langgraph/concepts/persistence/)
- [Backend API Documentation](./SWAGGER_GUIDE.md)

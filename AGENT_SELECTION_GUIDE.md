# Agent Selection Feature - Quick Reference

## Overview
The agent selection feature allows users to directly choose which agent handles their message instead of relying on keyword-based routing.

## Architecture Flow

```
User selects agent in UI dropdown
         ↓
Frontend (ChatPanel.tsx) emits Socket.IO message with selected_agent
         ↓
Backend (app.py) receives message, stores selected_agent in session metadata
         ↓
Backend enhances message with "[Route to {agent}]" prefix (if not supervisor)
         ↓
Backend (agent_runner.py) passes selected_agent to LangGraph
         ↓
LangGraph (router.py) checks for selected_agent in state
         ↓
If selected_agent exists → route directly to that agent
If not → use normal keyword-based routing
```

## Available Agents

| UI Display Name | Value | LangGraph Node | Description |
|----------------|-------|----------------|-------------|
| 🤖 Supervisor | `supervisor` | Uses keyword routing | Automatically routes based on message content |
| 📝 DOCX Agent | `docx_agent` | `docx_agent` | Document creation and management |
| 📄 PDF Parser | `pdf_parser` | `pdf_parser` | PDF extraction and analysis |
| 💬 General Assistant | `general_assistant` | `general_assistant` | General questions and assistance |
| 💰 RFP Finance Team | `rfp_finance` | `rfp_supervisor` | Financial analysis and budgeting |
| 🔧 RFP Technical Team | `rfp_technical` | `rfp_supervisor` | Technical requirements and specs |
| ⚖️ RFP Legal Team | `rfp_legal` | `rfp_supervisor` | Legal compliance and contracts |
| ✅ RFP QA Team | `rfp_qa` | `rfp_supervisor` | Quality assurance and testing |
| 🖼️ Image Adder Agent | `image_adder` | `image_adder` | Intelligent image insertion |

## Implementation Details

### Frontend Changes (ChatPanel.tsx)

```typescript
const [selectedAgent, setSelectedAgent] = useState('supervisor');

const agents = [
  { value: 'supervisor', label: '🤖 Supervisor', description: 'Auto-route based on content' },
  { value: 'docx_agent', label: '📝 DOCX Agent', description: 'Document creation' },
  // ... etc
];

// In send message handler:
socket.emit('send_message', {
  session_id: sessionId,
  message: input,
  selected_agent: selectedAgent
});
```

### Backend Changes (app.py)

```python
@sio.on('send_message')
async def handle_send_message(sid, data):
    selected_agent = data.get('selected_agent', 'supervisor')
    
    # Store in session metadata
    session_manager.update_session_metadata(
        session_id,
        {'selected_agent': selected_agent}
    )
    
    # Enhance message for non-supervisor routing
    if selected_agent and selected_agent != "supervisor":
        message = f"[Route to {selected_agent}] {message}"
    
    # Pass to agent runner
    result = await agent_runner.process_message(
        thread_id=thread_id,
        message=message,
        selected_agent=selected_agent
    )
```

### Agent Runner Changes (agent_runner.py)

```python
async def process_message(
    self,
    thread_id: str,
    message: str,
    document_context: Dict[str, Any] = None,
    selected_agent: str = "supervisor"
) -> Dict[str, Any]:
    # Add to config
    config = {
        "configurable": {
            "thread_id": thread_id,
            "selected_agent": selected_agent
        }
    }
    
    # Add to input data
    input_data = {
        "messages": [HumanMessage(content=message)]
    }
    if selected_agent and selected_agent != "supervisor":
        input_data["selected_agent"] = selected_agent
```

### LangGraph Router Changes (router.py)

```python
def supervisor_router(state: MessagesState) -> str:
    # Check for explicit agent selection
    selected_agent = state.get("selected_agent")
    if selected_agent and selected_agent != "supervisor":
        logger.info(f"Direct routing to selected agent: {selected_agent}")
        
        # Map UI agent names to graph node names
        agent_mapping = {
            "docx_agent": "docx_agent",
            "pdf_parser": "pdf_parser",
            "general_assistant": "general_assistant",
            "rfp_finance": "rfp_supervisor",  # RFP teams route through supervisor
            "rfp_technical": "rfp_supervisor",
            "rfp_legal": "rfp_supervisor",
            "rfp_qa": "rfp_supervisor",
            "image_adder": "image_adder"
        }
        return agent_mapping.get(selected_agent, "general_assistant")
    
    # Otherwise use keyword-based routing
    # ... existing routing logic
```

## Session & Thread Management

- **Session ID**: Created by frontend, stored in browser
- **Thread ID**: Created by backend on first message, mapped to session_id
- **Selected Agent**: Stored in session metadata, persists across messages
- **Thread Persistence**: Same thread_id is maintained even when switching agents

## Testing

### Manual Testing
1. Start all services:
   ```bash
   # Terminal 1: LangGraph
   cd main && langgraph dev
   
   # Terminal 2: Backend
   cd backend && python app.py
   
   # Terminal 3: Frontend
   cd frontend && npm run dev
   ```

2. Open http://localhost:5173
3. Select an agent from dropdown
4. Send a message
5. Verify routing in backend logs

### Automated Testing
```bash
# Python test script
python test_agent_selection.py

# Bash integration test
bash test_agent_selection.sh
```

## Debug Tips

### Frontend Debugging
- Open browser console (F12)
- Look for Socket.IO emit logs showing `selected_agent`
- Check Network tab for WebSocket frames

### Backend Debugging
- Check backend logs for: `"Forcing route to: {agent}"`
- Verify session metadata: `GET /api/session/{session_id}`
- Look for message enhancement: `"[Route to {agent}]"`

### LangGraph Debugging
- Check LangGraph logs for: `"Direct routing to selected agent: {agent}"`
- Verify state contains `selected_agent` key
- Confirm routing bypasses keyword matching

## Common Issues

### Issue: Agent selection not working
**Solution**: Verify selected_agent is in Socket.IO emit data (check browser console)

### Issue: Still using keyword routing
**Solution**: Check LangGraph router.py has updated code with agent_mapping

### Issue: Session not persisting
**Solution**: Verify thread_id is consistent across messages in session CSV

### Issue: RFP teams not routing correctly
**Solution**: RFP teams route through rfp_supervisor, which then routes to specific team

## Future Enhancements

1. **Agent History**: Show which agents were used in conversation
2. **Auto-switch**: Automatically switch agent based on context
3. **Multi-agent**: Allow message to be processed by multiple agents
4. **Agent Status**: Show if selected agent is busy/available
5. **Smart Suggestions**: Suggest best agent for user's message

## Files Modified

- ✅ `frontend/src/components/ChatPanel.tsx` - Added dropdown UI
- ✅ `backend/app.py` - Added selected_agent handling
- ✅ `backend/agent_runner.py` - Thread selected_agent parameter
- ✅ `main/src/agent/router.py` - Added direct routing logic

## Related Documentation

- See `AGENT_GUIDE.md` for detailed agent descriptions
- See `backend/README.md` for backend architecture
- See `main/README.md` for LangGraph setup

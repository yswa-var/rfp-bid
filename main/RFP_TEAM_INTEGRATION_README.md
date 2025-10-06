# RFP Proposal Team Integration

## Overview

This document explains the integration of the **RFP Proposal Agent** into the main **LangGraph multi-agent system**. The integration creates a hierarchical team-based workflow where specialized RFP nodes (finance, technical, legal, QA) generate content and automatically route it to the document agent for updates.

## Architecture

### System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      Main Supervisor                             │
│  (Routes to: pdf_parser, docx_agent, rfp_supervisor, general)   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
          ┌─────────────────────────────────────┐
          │      RFP Team Supervisor            │
          │  (Routes to specialized nodes)      │
          └─────────────┬───────────────────────┘
                        │
           ┌────────────┼────────────┬──────────────┐
           ▼            ▼            ▼              ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
    │ Finance  │  │Technical │  │  Legal   │  │    QA    │
    │   Node   │  │   Node   │  │   Node   │  │   Node   │
    └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
         │             │             │             │
         └─────────────┴─────────────┴─────────────┘
                        │
                        ▼
                  ┌─────────────┐
                  │ DOCX Agent  │
                  │  (Write to  │
                  │  document)  │
                  └─────────────┘
```

### Components

#### 1. **State Management** (`state.py`)

Enhanced `MessagesState` with RFP-specific fields:

```python
class MessagesState(TypedDict):
    # Existing fields...
    
    # RFP Proposal Team State
    rfp_content: Dict[str, Any]       # Generated content by node type
    current_rfp_node: Optional[str]   # Current RFP node being processed
    rfp_query: Optional[str]          # Current RFP query
    rfp_team_completed: bool          # Track if RFP team work is completed
    document_path: Optional[str]      # Path to the document to update
```

#### 2. **RFP Proposal Team** (`agents.py`)

New `RFPProposalTeam` class with specialized methods:

- `rfp_supervisor(state)` - Routes to appropriate specialized node
- `finance_node(state)` - Generates finance/budget content
- `technical_node(state)` - Generates technical architecture content
- `legal_node(state)` - Generates legal/compliance content
- `qa_node(state)` - Generates QA/testing content

Each node:
1. Extracts the query from state
2. Calls `RFPProposalAgent` methods with RAG context
3. Updates state with generated content
4. Returns formatted response

#### 3. **Routing Logic** (`router.py`)

Three new routers:

**a. Enhanced Supervisor Router**
```python
def supervisor_router(state: MessagesState) -> str:
    # Routes to: rfp_supervisor, pdf_parser, docx_agent, general_assistant
```

**b. RFP Team Router**
```python
def rfp_team_router(state: MessagesState) -> str:
    # Routes from rfp_supervisor to specialized nodes
    # Based on current_rfp_node in state
```

**c. RFP to DOCX Router**
```python
def rfp_to_docx_router(state: MessagesState) -> str:
    # Routes from RFP nodes to docx_agent or END
    # Checks if content was generated successfully
```

#### 4. **Main Graph** (`graph.py`)

Updated workflow with RFP team nodes:

```python
# Add RFP team nodes
workflow.add_node("rfp_supervisor", rfp_team.rfp_supervisor)
workflow.add_node("rfp_finance", rfp_team.finance_node)
workflow.add_node("rfp_technical", rfp_team.technical_node)
workflow.add_node("rfp_legal", rfp_team.legal_node)
workflow.add_node("rfp_qa", rfp_team.qa_node)

# RFP Team flow
workflow.add_conditional_edges(
    "rfp_supervisor",
    rfp_team_router,
    {...}
)

# After each RFP node, route to docx_agent
workflow.add_conditional_edges(
    "rfp_finance",
    rfp_to_docx_router,
    {"docx_agent": "docx_agent", "__end__": END}
)
```

## Workflow Examples

### Example 1: Finance Content Generation

```python
from langchain_core.messages import HumanMessage
from agent.graph import graph

result = graph.invoke({
    "messages": [HumanMessage(content="Create a 3-year budget for cybersecurity services")],
    "rfp_content": {},
    # ... other state fields
})
```

**Flow:**
1. Main supervisor detects "budget" → routes to `rfp_supervisor`
2. RFP supervisor detects "budget" → sets `current_rfp_node = "finance"`
3. Router directs to `rfp_finance` node
4. Finance node:
   - Queries RAG for budget examples
   - Generates comprehensive budget content
   - Saves to `state["rfp_content"]["finance"]`
5. Router checks content → routes to `docx_agent`
6. DOCX agent writes content to document
7. Workflow ends

### Example 2: Technical Architecture

```python
result = graph.invoke({
    "messages": [HumanMessage(content="Describe technical architecture for SOC")],
    "rfp_content": {},
    # ...
})
```

**Flow:**
1. Main supervisor → `rfp_supervisor`
2. RFP supervisor detects "technical" → `current_rfp_node = "technical"`
3. `rfp_technical` node generates content with RAG
4. Routes to `docx_agent` for document update
5. Workflow ends

### Example 3: Complete Proposal (All Teams)

For a complete proposal, invoke the graph multiple times:

```python
# 1. Finance content
graph.invoke({"messages": [HumanMessage("Create budget breakdown")]})

# 2. Technical content
graph.invoke({"messages": [HumanMessage("Describe technical architecture")]})

# 3. Legal content
graph.invoke({"messages": [HumanMessage("Draft SLA and compliance terms")]})

# 4. QA content
graph.invoke({"messages": [HumanMessage("Define testing procedures")]})
```

Each invocation:
- Generates specialized content
- Writes to document automatically
- Maintains context through RAG databases

## Key Features

### 1. **RAG-Enhanced Generation**

Each specialized node uses RAG to generate high-quality content:

- **RFP Database**: Real RFP examples for context
- **Template Database**: Proposal templates and best practices
- **Session Database**: Custom uploaded documents

### 2. **Automatic Document Updates**

Generated content is automatically routed to `docx_agent`:

```python
# Content flows from RFP node → docx_agent
workflow.add_conditional_edges(
    "rfp_finance",
    rfp_to_docx_router,
    {"docx_agent": "docx_agent", "__end__": END}
)
```

The `docx_agent` receives:
- Generated content in `state["rfp_content"]`
- Node type (finance/technical/legal/qa)
- Metadata (sources, accuracy scores)

### 3. **Hierarchical Team Structure**

Following LangGraph's hierarchical multi-agent pattern:

- **Main Supervisor**: High-level routing (PDF, DOCX, RFP, General)
- **RFP Supervisor**: Specialized routing within RFP team
- **Worker Nodes**: Focused content generation (finance, technical, legal, QA)

### 4. **State Propagation**

State flows through the entire workflow:

```python
User Input → Main Supervisor → RFP Supervisor → Specialized Node → DOCX Agent
    |              |                 |                  |               |
    └── messages   └── messages      └── rfp_query     └── rfp_content └── Write to doc
```

### 5. **Response Tracking**

All RFP responses are tracked in `rfp_team_responses.json`:

```json
{
  "timestamp": "2025-10-06T...",
  "node_type": "finance",
  "query": "Create budget...",
  "response": "...",
  "context": [...],
  "metadata": {...}
}
```

## Usage

### Basic Usage

```python
from langchain_core.messages import HumanMessage
from agent.graph import graph

# Initialize state
initial_state = {
    "messages": [HumanMessage(content="Generate RFP finance content")],
    "chunks": [],
    "pdf_paths": [],
    "task_completed": False,
    "iteration_count": 0,
    "confidence_score": None,
    "follow_up_questions": [],
    "parsed_response": None,
    "rfp_content": {},
    "current_rfp_node": None,
    "rfp_query": None,
    "rfp_team_completed": False,
    "document_path": None
}

# Invoke the graph
result = graph.invoke(initial_state)

# Access generated content
finance_content = result["rfp_content"].get("finance", {})
print(finance_content["content"])
```

### Running Examples

Use the provided example script:

```bash
cd main
export OPENAI_API_KEY='your-api-key'
python integrated_rfp_workflow_example.py
```

This script demonstrates:
- Finance node: Budget generation
- Technical node: Architecture design
- Legal node: Compliance & SLA
- QA node: Testing strategy
- Complete workflow: All teams

### LangGraph Studio

View the workflow in LangGraph Studio:

```bash
cd main
langgraph dev
```

Open in browser to see:
- Interactive graph visualization
- Node execution flow
- State at each step
- Message passing between nodes

## Customization

### Adding New Specialized Nodes

1. **Add method to `RFPProposalTeam`** (`agents.py`):

```python
def risk_assessment_node(self, state: MessagesState) -> Dict[str, Any]:
    """Generate risk assessment content."""
    result = self.rfp_agent.risk_assessment_node(query, k=5)
    # ... process result
    return {"messages": [...], "rfp_content": {...}}
```

2. **Update RFP supervisor routing** (`agents.py`):

```python
def rfp_supervisor(self, state: MessagesState) -> Dict[str, Any]:
    # Add new routing condition
    if any(word in last_message for word in ["risk", "assessment"]):
        return {
            "messages": [...],
            "current_rfp_node": "risk_assessment"
        }
```

3. **Add to graph** (`graph.py`):

```python
workflow.add_node("rfp_risk_assessment", rfp_team.risk_assessment_node)

workflow.add_conditional_edges(
    "rfp_risk_assessment",
    rfp_to_docx_router,
    {"docx_agent": "docx_agent", "__end__": END}
)
```

4. **Update router** (`router.py`):

```python
def rfp_team_router(state: MessagesState) -> str:
    if current_node == "risk_assessment":
        return "rfp_risk_assessment"
```

### Customizing Prompts

Edit system prompts in `RFP_proposal_agent.py`:

```python
def finance_node(self, query: str, k: int = 5) -> Dict[str, Any]:
    system_prompt = """
    You are a financial expert specializing in...
    [Customize this prompt]
    """
```

### Adjusting RAG Context

Control RAG results per node:

```python
# More context for complex nodes
result = self.rfp_agent.technical_node(query, k=10)

# Less context for simple nodes
result = self.rfp_agent.finance_node(query, k=3)
```

## Troubleshooting

### Issue: RFP content not routing to docx_agent

**Solution**: Check `rfp_to_docx_router` logic:

```python
# Ensure content exists in state
rfp_content = state.get("rfp_content", {})
current_node = state.get("current_rfp_node")

if current_node and current_node in rfp_content:
    if rfp_content[current_node].get("content"):
        return "docx_agent"
```

### Issue: Wrong RFP node being selected

**Solution**: Update routing keywords in `rfp_supervisor`:

```python
# Add more specific keywords
if any(word in last_message for word in [
    "finance", "budget", "cost", "pricing", "payment", "financial"
]):
    return {..., "current_rfp_node": "finance"}
```

### Issue: RAG context not found

**Solution**: Verify database paths in `RFP_proposal_agent.py`:

```python
# Check these paths exist
self.rfp_rag_db = "src/agent/demo_rfp_rag.db"
self.template_rag_db = "src/agent/demo_template_rag.db"
```

### Issue: DOCX agent not receiving content

**Solution**: Ensure state updates are returning properly:

```python
return {
    "messages": [AIMessage(content=message)],
    "rfp_content": rfp_content,  # Include updated content
    "current_rfp_node": "finance"
}
```

## Best Practices

1. **State Management**
   - Always initialize all state fields
   - Use `.get()` with defaults when accessing state
   - Return complete state updates from nodes

2. **Error Handling**
   - Wrap node logic in try-except blocks
   - Return error messages in standard format
   - Log errors for debugging

3. **RAG Queries**
   - Use specific, detailed queries for better context
   - Adjust `k` parameter based on complexity
   - Query multiple databases with `database="all"`

4. **Content Generation**
   - Use lower temperature (0.3) for consistency
   - Include metadata in responses
   - Track all responses in JSON file

5. **Routing**
   - Use clear, mutually exclusive routing conditions
   - Provide sensible defaults
   - Test edge cases

## Performance Considerations

### Optimization Tips

1. **Batch Processing**: Generate multiple sections in one run
2. **Caching**: Cache RAG results for similar queries
3. **Parallel Execution**: Use LangGraph's built-in parallelization
4. **Streaming**: Stream long responses for better UX

### Resource Usage

- **Memory**: ~500MB per graph execution
- **API Calls**: 2-5 calls per RFP node (1 for routing, 1-4 for RAG+generation)
- **Latency**: 3-10 seconds per node execution

## Future Enhancements

### Planned Features

1. **Multi-Round Refinement**
   - Generate draft → Review → Refine → Finalize
   - Human-in-the-loop approval

2. **Parallel Team Execution**
   - Run multiple teams simultaneously
   - Merge results intelligently

3. **Conditional Routing**
   - Route based on content quality
   - Retry on low confidence

4. **External Integrations**
   - Pricing databases
   - Compliance checkers
   - Template libraries

5. **Advanced State Management**
   - Persistent state across sessions
   - State versioning
   - Rollback capabilities

## References

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangGraph Multi-Agent Patterns](https://langchain-ai.github.io/langgraph/tutorials/multi_agent/)
- [React Agent Template](https://github.com/langchain-ai/react-agent)
- [RFP Proposal Agent README](./RFP_PROPOSAL_AGENT_README.md)

## Support

For issues or questions:
1. Check this README and troubleshooting section
2. Review the example scripts
3. Examine the test files
4. Check LangGraph Studio visualization

## License

This integration follows the same license as the main project.


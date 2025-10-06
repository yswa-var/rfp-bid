# RFP Proposal Agent

A comprehensive multi-node AI agent for generating RFP (Request for Proposal) content using LangChain and GPT-3.5-turbo with RAG (Retrieval-Augmented Generation) capabilities.

## 🌟 Features

The RFP Proposal Agent provides specialized nodes for different aspects of RFP proposal generation:

- **💬 Chat GPT**: General conversation and queries using GPT-3.5-turbo
- **🔍 Query RAG**: Search across multiple RAG databases (session, RFP examples, templates)
- **💰 Finance Node**: Generate financial content (budgets, pricing, ROI analysis)
- **🔧 Technical Node**: Generate technical specifications and architecture
- **⚖️ Legal Node**: Generate legal compliance and contract terms
- **🧪 QA Node**: Generate testing procedures and quality assurance content
- **💾 Response Tracking**: Automatically track all responses in JSON format

## 📋 Prerequisites

### Required Dependencies

```bash
# Core dependencies (already in requirements.txt)
langgraph>=0.2.6
langchain-core>=0.1.0
langchain-openai>=0.1.0
langchain-milvus>=0.1.0
pymilvus>=2.3.0
python-dotenv>=1.0.1
```

### Environment Setup

```bash
# Set your OpenAI API key
export OPENAI_API_KEY='your-api-key-here'
```

### Database Setup

The agent uses three RAG databases:

1. **Session Database**: Main document database (`session.db`)
2. **RFP Database**: RFP examples database (`demo_rfp_rag.db`)
3. **Template Database**: Template database (`demo_template_rag.db`)

## 🚀 Quick Start

### Basic Usage

```python
from agent.RFP_proposal_agent import RFPProposalAgent

# Initialize the agent
agent = RFPProposalAgent()

# Chat with GPT-3.5-turbo
response = agent.chat_gpt("What are key RFP components?")
print(response)

# Query RAG databases
results = agent.query_rag("cybersecurity requirements", k=5)

# Generate finance content
finance_content = agent.finance_node(
    "Create a 3-year budget for SOC implementation"
)
print(finance_content['response'])
```

### Advanced Usage with Custom Paths

```python
agent = RFPProposalAgent(
    session_db_path="/path/to/session.db",
    rfp_rag_db="/path/to/rfp_rag.db",
    template_rag_db="/path/to/template_rag.db",
    response_file="my_responses.json"
)
```

## 📚 API Reference

### Class: `RFPProposalAgent`

#### Initialization

```python
RFPProposalAgent(
    session_db_path: Optional[str] = None,
    rfp_rag_db: Optional[str] = None,
    template_rag_db: Optional[str] = None,
    response_file: str = "rfp_proposal_responses.json"
)
```

**Parameters:**
- `session_db_path`: Path to main session database
- `rfp_rag_db`: Path to RFP examples database
- `template_rag_db`: Path to template database
- `response_file`: JSON file to track all responses

#### Methods

##### 1. `chat_gpt(message: str, use_history: bool = True) -> str`

Chat with GPT-3.5-turbo using LangChain.

```python
response = agent.chat_gpt(
    "What are the key components of a good RFP proposal?",
    use_history=True  # Include conversation history
)
```

**Parameters:**
- `message`: User message to send
- `use_history`: Whether to include conversation history

**Returns:** AI response as string

---

##### 2. `query_rag(query: str, k: int = 5, database: str = "session") -> List[Dict[str, Any]]`

Query RAG databases and return results.

```python
results = agent.query_rag(
    query="cybersecurity SOC requirements",
    k=5,
    database="all"  # Options: "session", "rfp", "template", "all"
)
```

**Parameters:**
- `query`: Search query
- `k`: Number of results to return
- `database`: Which database to query

**Returns:** List of search results with:
- `content`: Document content
- `metadata`: Document metadata
- `accuracy`: Relevance score
- `source_file`: Source filename
- `page`: Page number
- `database`: Source database

---

##### 3. `finance_node(query: str, k: int = 5) -> Dict[str, Any]`

Generate finance-focused content for RFP proposals.

```python
result = agent.finance_node(
    "Create a detailed 3-year budget for managed SOC service",
    k=5
)

print(result['response'])  # Generated content
print(result['context'])   # RAG context used
```

**Generates:**
- Budget breakdowns and cost estimates
- Pricing models and payment terms
- ROI analysis
- Cost-benefit analysis
- Resource allocation
- Financial risk assessment

**Returns:** Dictionary with:
- `success`: Boolean indicating success
- `response`: Generated content
- `context`: RAG sources used
- `metadata`: Additional information

---

##### 4. `technical_node(query: str, k: int = 5) -> Dict[str, Any]`

Generate technical-focused content for RFP proposals.

```python
result = agent.technical_node(
    "Describe technical architecture for SOC with SIEM integration",
    k=5
)
```

**Generates:**
- Technical architecture and design
- System requirements and specifications
- Technology stack and tools
- Implementation approach
- Integration requirements
- Security architecture

---

##### 5. `legal_node(query: str, k: int = 5) -> Dict[str, Any]`

Generate legal-focused content for RFP proposals.

```python
result = agent.legal_node(
    "Draft SLA for 24/7 security monitoring with 99.9% uptime",
    k=5
)
```

**Generates:**
- Contract terms and conditions
- Legal compliance requirements
- Liability and indemnification
- Intellectual property rights
- Data protection and privacy
- Service level agreements (SLAs)

---

##### 6. `qa_node(query: str, k: int = 5) -> Dict[str, Any]`

Generate QA/testing-focused content for RFP proposals.

```python
result = agent.qa_node(
    "Create testing strategy for SOC security monitoring",
    k=5
)
```

**Generates:**
- Testing strategies and methodologies
- Quality assurance processes
- Test planning and execution
- Acceptance criteria
- Quality metrics and KPIs
- Performance and load testing

---

##### 7. `get_all_responses(node_type: Optional[str] = None) -> List[Dict[str, Any]]`

Get all tracked responses, optionally filtered by node type.

```python
# Get all responses
all_responses = agent.get_all_responses()

# Get only finance responses
finance_responses = agent.get_all_responses(node_type="finance")
```

---

##### 8. `get_response_summary() -> Dict[str, Any]`

Get a summary of all tracked responses.

```python
summary = agent.get_response_summary()
print(f"Total responses: {summary['total']}")
print(f"By node: {summary['by_node']}")
```

---

##### 9. `clear_conversation_history()`

Clear the conversation history for chat_gpt.

```python
agent.clear_conversation_history()
```

## 💾 Response Tracking

All responses are automatically saved to a JSON file with the following structure:

```json
{
  "timestamp": "2025-10-06T10:30:00",
  "node_type": "finance",
  "query": "Create a 3-year budget...",
  "response": "Here is a comprehensive budget...",
  "context": [
    {
      "content": "...",
      "source_file": "example.pdf",
      "page": 5,
      "accuracy": 0.92
    }
  ],
  "metadata": {
    "num_sources": 5,
    "avg_accuracy": 0.88
  }
}
```

## 📖 Complete Example

Run the comprehensive demo:

```bash
# From the main directory
cd /Users/yash/Documents/rfp/rfp-bid/main

# Ensure OpenAI API key is set
export OPENAI_API_KEY='your-api-key-here'

# Run the example
python example_rfp_agent_usage.py
```

This will demonstrate:
1. General chat functionality
2. RAG database queries
3. Finance content generation
4. Technical content generation
5. Legal content generation
6. QA content generation
7. Response tracking and summaries
8. Exporting specific node responses

## 🔧 Integration with Existing System

The RFP Proposal Agent can be integrated into your LangGraph workflow:

```python
from agent.RFP_proposal_agent import RFPProposalAgent
from langgraph.graph import StateGraph

# Create agent instance
rfp_agent = RFPProposalAgent()

# Add as nodes in your graph
workflow = StateGraph(MessagesState)

def finance_node_handler(state):
    query = state['messages'][-1].content
    result = rfp_agent.finance_node(query)
    return {"messages": [AIMessage(content=result['response'])]}

workflow.add_node("finance", finance_node_handler)
# ... add other nodes
```

## 🎯 Use Cases

### 1. Complete RFP Proposal Generation

```python
agent = RFPProposalAgent()

# Generate all sections
executive_summary = agent.chat_gpt("Create executive summary for SOC RFP")
budget = agent.finance_node("Detailed 3-year budget")
architecture = agent.technical_node("SOC technical architecture")
legal = agent.legal_node("SLA and legal terms")
testing = agent.qa_node("Testing and QA procedures")

# All responses are automatically tracked in JSON
```

### 2. Interactive Proposal Builder

```python
agent = RFPProposalAgent()

sections = [
    ("finance", "Budget for 24/7 SOC monitoring"),
    ("technical", "SIEM integration architecture"),
    ("legal", "Data protection compliance"),
    ("qa", "Security testing procedures")
]

for node_type, query in sections:
    if node_type == "finance":
        result = agent.finance_node(query)
    elif node_type == "technical":
        result = agent.technical_node(query)
    # ... handle other types
    
    print(f"Generated {node_type} content")
```

### 3. RAG-Enhanced Research

```python
agent = RFPProposalAgent()

# Search across all databases
research_topics = [
    "managed security service provider qualifications",
    "SOC staffing requirements",
    "incident response procedures"
]

for topic in research_topics:
    results = agent.query_rag(topic, k=5, database="all")
    # Process results...
```

## 🛠️ Troubleshooting

### Issue: Database not found

```python
# Ensure databases exist or create them first
from agent.milvus_ops import MilvusOps

# Create session database from PDFs
milvus_ops = MilvusOps("session.db")
# ... parse PDFs and create database
```

### Issue: OpenAI API key not set

```bash
# Set environment variable
export OPENAI_API_KEY='your-api-key-here'

# Or in Python
import os
os.environ['OPENAI_API_KEY'] = 'your-api-key-here'
```

### Issue: No RAG context found

```python
# Check database status
agent = RFPProposalAgent()
results = agent.query_rag("test query", k=1)
if not results:
    print("No results found - check database connection")
```

## 📊 Best Practices

1. **Use specific queries**: More specific queries yield better RAG results
2. **Adjust k parameter**: Increase `k` for more context, decrease for faster responses
3. **Review tracked responses**: Regularly check the JSON file for quality
4. **Clear history when needed**: Use `clear_conversation_history()` for fresh conversations
5. **Combine nodes**: Use multiple nodes for comprehensive proposal sections

## 🤝 Contributing

To add new node types or functionality:

1. Create a new method following the pattern of existing nodes
2. Use `_generate_node_content()` for consistency
3. Define a specialized system prompt
4. Track responses using `_save_response()`

## 📄 License

Same as the parent project license.

## 🙏 Acknowledgments

Built using:
- [LangChain](https://github.com/langchain-ai/langchain)
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [OpenAI GPT-3.5-turbo](https://openai.com/)
- [Milvus](https://milvus.io/)

---

For questions or issues, please refer to the main project documentation.


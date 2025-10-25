# 🤖 Complete LangGraph Agent System Guide

## **System Architecture Overview**

Your RFP system uses a **Supervisor + Multi-Agent Architecture** with specialized teams:

```
┌─────────────────────────────────────────────────────────────┐
│                    SUPERVISOR SYSTEM                         │
│                  (Main Routing Agent)                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
    ┌────▼────┐   ┌───▼────┐   ┌───▼────────┐
    │ PDF     │   │ DOCX   │   │ RFP        │
    │ Parser  │   │ Agent  │   │ Supervisor │
    │ Agent   │   │        │   │            │
    └─────────┘   └────────┘   └─────┬──────┘
                                      │
                      ┌───────────────┼───────────────┐
                      │               │               │
                 ┌────▼────┐   ┌─────▼─────┐   ┌────▼─────┐
                 │ Finance │   │ Technical │   │ Legal    │
                 │ Team    │   │ Team      │   │ Team     │
                 └─────────┘   └───────────┘   └──────────┘
                      │               │               │
                      └───────────────┼───────────────┘
                                      │
                                ┌─────▼──────┐
                                │ QA Team    │
                                └────────────┘
```

---

## **🎯 Available Agents**

### **1. Supervisor Agent** (Main Router)
**Location**: `main/src/agent/graph.py`
**Purpose**: Routes user queries to the appropriate specialized agent
**Model**: GPT-4o-mini (temperature: 0)

**Routing Logic** (Priority Order):
1. **Explicit agent name** → Direct to that agent
2. **Image operations** → `image_adder`
3. **Document operations** → `docx_agent`
4. **PDF parsing** → `pdf_parser`
5. **RFP proposal generation** → `rfp_supervisor`
6. **General questions** → `general_assistant`

**Trigger Keywords**:
```python
# Image operations
"add images", "insert images", "image_adder"

# Document operations
"docx", ".docx", "word document", "edit document", 
"create document", "update document"

# PDF parsing
"parse pdf", ".pdf", "index pdf"

# RFP proposals
"generate proposal", "create proposal", "rfp proposal",
"finance team", "technical team", "legal team"
```

---

### **2. PDF Parser Agent**
**Location**: `main/src/agent/agents.py` - `PDFParserAgent`
**Purpose**: Parses PDF files and creates text chunks for RAG
**Flow**: `pdf_parser` → `create_rag` → `END`

**How to Use**:
```bash
# Example messages:
"Parse this PDF: /path/to/document.pdf"
"Index these PDFs: /path/doc1.pdf, /path/doc2.pdf"
```

**What It Does**:
1. Extracts absolute PDF paths from user message
2. Parses PDFs using MilvusOps
3. Creates high-quality text chunks
4. Provides chunk quality statistics
5. Automatically creates session.db RAG database

**Output Example**:
```
✅ Parsed 1 PDF(s) and created 245 high-quality chunks.
📊 Quality Stats: 240 cleaned, 180 improved, avg 150 words/chunk
📄 Document Types: cybersecurity_rfp
```

---

### **3. General Assistant Agent**
**Location**: `main/src/agent/agents.py` - `GeneralAssistantAgent`
**Purpose**: Answers questions using RAG database (session.db)
**Model**: GPT-4o-mini (temperature: 0.1)

**Features**:
- **Structured responses** using Pydantic models
- **Confidence scoring** (0-10)
- **Follow-up questions** generation
- **Source citations** with page numbers

**How to Use**:
```bash
# After creating session.db with PDF parser:
"What are the cybersecurity requirements?"
"Summarize the technical specifications"
"What is the project timeline?"
```

**Response Format**:
```python
{
    "answer": "Comprehensive answer...",
    "confidence_score": 8,  # 0-10
    "follow_up_questions": [
        "Would you like details on specific security controls?",
        "Should I explain the compliance requirements?"
    ],
    "sources": [
        {"pdf_name": "RFP-Cybersec.pdf", "page": "8"},
        {"pdf_name": "RFP-Cybersec.pdf", "page": "12"}
    ]
}
```

---

### **4. DOCX Agent** (ReAct Agent)
**Location**: `main/src/react_agent/`
**Purpose**: Complete document management system
**Model**: GPT-4o-mini (configurable)
**Architecture**: ReAct pattern with tool calling

**Prompt**: `main/src/react_agent/prompts.py`
```python
SYSTEM_PROMPT = """You are a helpful AI assistant specialized in 
document management and generation...."""
```

#### **Available Tools** (`tools.py`):

| Tool | Purpose | Auto-Render |
|------|---------|-------------|
| `get_sections()` | List all document sections | No |
| `get_content(section_name)` | Get section content | No |
| `get_content_by_heading(text)` | Find section by heading | No |
| `create_section(name, elements)` | Create new section | No |
| `update_content(section, idx, element)` | Update element | No |
| `insert_content_after_heading(heading, element)` | Insert after heading | No |
| `edit_config(updates)` | Update doc config | No |
| `render_document()` | Generate final DOCX | Yes |
| `search(query)` | Web search (Tavily) | No |
| `add_images_from_csv()` | Auto-insert images | No |

#### **Document Workflow**:
```
1. get_sections() → See what exists
2. create_section() / update_content() → Make changes
3. [Repeat step 2 as needed]
4. render_document() → Generate final .docx file
```

#### **File Structure**:
```
main/test_output/
├── config/
│   ├── config_1730000000.json  # Versioned configs
│   └── config_1730000100.json
├── content/
│   ├── content_1730000000.json # Versioned content
│   └── content_1730000100.json
└── docx/
    ├── output_20251025_140500.docx
    └── output_20251025_141200.docx
```

**Versioning**:
- Config and content files are versioned with Unix timestamps
- Keeps last 10 versions automatically
- Each render creates new timestamped DOCX

#### **Human-in-the-Loop Approval**:
**Location**: `backend/agent_runner.py` + `backend/app.py`

The DOCX agent has approval workflow for edits:
```python
# When agent wants to edit:
if result.get("requires_approval"):
    # Backend sets pending_approval in session
    session_manager.set_pending_approval(session_id, approval_data)
    
    # User responds:
    "yes" / "approve" → Continue with edit
    "no" / "reject" → Cancel edit
```

---

### **5. RFP Proposal Team** (4 Specialized Agents)
**Location**: `main/src/agent/agents.py` - `RFPProposalTeam`
**Purpose**: Generate comprehensive RFP proposals by section
**Model**: GPT-4o-mini (temperature: 0)

#### **Team Structure**:

```
rfp_supervisor (Router)
    ├── rfp_finance (Finance Team)
    ├── rfp_technical (Technical Team)
    ├── rfp_legal (Legal Team)
    └── rfp_qa (QA Team)
```

#### **5.1 Finance Team**
**Node**: `rfp_finance`
**Specialization**: Financial & budgetary content
**RAG Database**: `demo_rfp_rag.db` + `demo_template_rag.db`

**Prompt Focus**:
- Budget breakdowns
- Pricing structures
- Payment terms
- Cost analysis
- ROI calculations

**Example Query**:
```bash
"Generate finance section for cybersecurity RFP with 3-year contract"
"Create budget breakdown for SOC operations"
```

#### **5.2 Technical Team**
**Node**: `rfp_technical`
**Specialization**: Technical architecture & specifications

**Prompt Focus**:
- System architecture
- Technology stack
- Implementation approach
- Integration requirements
- Performance specifications

**Example Query**:
```bash
"Generate technical architecture for SIEM implementation"
"Create technical specifications for SOC platform"
```

#### **5.3 Legal Team**
**Node**: `rfp_legal`
**Specialization**: Legal compliance & contracts

**Prompt Focus**:
- Contract terms
- Compliance requirements
- Liability clauses
- SLA agreements
- Legal obligations

**Example Query**:
```bash
"Generate legal compliance section for government RFP"
"Create contract terms for managed security services"
```

#### **5.4 QA Team**
**Node**: `rfp_qa`
**Specialization**: Quality assurance & testing

**Prompt Focus**:
- Testing procedures
- Quality metrics
- Risk assessment
- Validation processes
- Acceptance criteria

**Example Query**:
```bash
"Generate QA procedures for cybersecurity implementation"
"Create testing strategy for SOC deployment"
```

#### **RFP Team Workflow**:
```
User Query → rfp_supervisor (routes based on keywords)
    ↓
Specialized Team Node (finance/technical/legal/qa)
    ↓
Generate Content using RAG
    ↓
Send to docx_agent with formatted markdown
    ↓
docx_agent creates/updates document section
    ↓
END
```

**Team Routing Logic** (`router.py`):
```python
# Keywords trigger specific teams:
["finance", "budget", "cost", "pricing"] → finance_team
["technical", "architecture", "technology"] → technical_team
["legal", "contract", "compliance"] → legal_team
["qa", "quality", "testing"] → qa_team
```

#### **RFP Content Format**:
Each team generates markdown content like:
```markdown
🔧 **Technical Team Response:**

## System Architecture Overview
Our proposed solution leverages...

### Key Components
1. SIEM Platform
2. SOC Monitoring
3. Incident Response

### Technology Stack
- Platform: Splunk Enterprise
- Integration: REST APIs
- Storage: ElasticSearch
```

This gets sent to docx_agent as:
```
"Edit Docx document with Technical Team Response 
(create a new section if needed) change the content 
from markdown to the docx format: ..."
```

---

### **6. Image Adder Agent**
**Location**: `main/src/agent/image_adder_node.py`
**Purpose**: Intelligently add images to document sections
**Method**: Semantic matching using LLM

**How It Works**:
1. Reads `main/images/image_name_dicription.csv`
2. Gets document sections from content.json
3. Uses LLM to match images to sections semantically
4. Inserts images after appropriate headings

**CSV Format**:
```csv
Image Name,Description
security_diagram.png,Network security architecture diagram
soc_workflow.png,SOC incident response workflow
compliance_chart.png,Compliance framework comparison
```

**Example Usage**:
```bash
"Add images to the document"
"Insert images from CSV"
"Place images in appropriate sections"
```

---

## **🗄️ RAG Databases**

### **Database Files**:
```
main/
├── session.db              # User PDF session database
├── src/agent/
│   ├── demo_rfp_rag.db    # RFP examples database
│   └── demo_template_rag.db # Template database
```

### **How RAG Works**:

1. **Indexing** (via `milvus_ops.py`):
```python
# Parse PDF → Create chunks → Vectorize → Store
MilvusOps.parse_pdf() 
    → MilvusOps.create_chunks()
    → MilvusOps.vectorize_and_store()
```

2. **Querying**:
```python
# Query → Retrieve similar chunks → Generate response
MilvusOps.query_database(query, k=5)
    → Get top 5 most relevant chunks
    → Pass to LLM for answer generation
```

### **Embeddings**:
- **Model**: `text-embedding-3-large` (OpenAI)
- **Vector Store**: Milvus (SQLite backend)
- **Index Type**: FLAT
- **Metric**: L2 distance

---

## **🔧 How to Use Each Agent**

### **Starting the System**:
```bash
# Terminal 1: LangGraph Server
cd main
langgraph dev
# Runs on http://localhost:2024

# Terminal 2: Backend
cd backend
python app.py
# Runs on http://localhost:8000

# Terminal 3: Frontend
cd frontend
npm run dev
# Runs on http://localhost:5173
```

### **Example Conversations**:

#### **1. Index PDFs and Query**:
```
User: "Parse this PDF: C:/docs/rfp-cybersec.pdf"
Agent: [pdf_parser] ✅ Parsed 1 PDF, created 245 chunks
       [create_rag] ✅ Created session.db

User: "What are the security requirements?"
Agent: [general_assistant] 
       Answer: The RFP requires 24/7 SOC monitoring...
       Confidence: 8/10
       Sources: rfp-cybersec.pdf (Page 8, 12)
```

#### **2. Create Document**:
```
User: "Create a proposal document"
Agent: [docx_agent → get_sections]
       Current sections: Introduction

User: "Add Executive Summary section"
Agent: [docx_agent → create_section]
       ✅ Section created

User: "Render the document"
Agent: [docx_agent → render_document]
       ✅ Document: output_20251025_143000.docx
```

#### **3. Generate RFP Proposal**:
```
User: "Generate technical proposal for SOC implementation"
Agent: [rfp_supervisor → rfp_technical]
       🔧 Routing to Technical Team...
       [Generates technical content using RAG]
       [Sends to docx_agent]
       ✅ Technical section added to document
```

#### **4. Add Images**:
```
User: "Add images to the document"
Agent: [image_adder]
       Reading CSV...
       Matching images to sections...
       ✅ Inserted 5 images:
         - security_diagram.png → Security Architecture
         - soc_workflow.png → SOC Operations
```

---

## **📝 Agent State Management**

### **State Schema** (`state.py`):
```python
class MessagesState(TypedDict):
    messages: List[BaseMessage]           # Conversation history
    chunks: List[Document]                # PDF chunks
    pdf_paths: List[str]                  # Parsed PDF paths
    task_completed: bool                  # Task status
    confidence_score: Optional[int]       # Answer confidence
    follow_up_questions: List[str]        # Generated questions
    
    # RFP Team State
    rfp_content: Dict[str, Any]          # Generated RFP content
    current_rfp_node: Optional[str]      # Current team node
    rfp_query: Optional[str]             # RFP query
    document_path: Optional[str]         # Document path
```

---

## **🎨 Customization**

### **Change Agent Models**:
```python
# In agents.py or graph.py:
supervisor_llm = ChatOpenAI(
    model="gpt-4o",  # Change model
    temperature=0.2,  # Adjust creativity
)
```

### **Modify Agent Prompts**:
```python
# In graph.py - supervisor_prompt:
supervisor_prompt = """
You are a supervisor managing agents:
[Customize routing logic here...]
"""

# In react_agent/prompts.py:
SYSTEM_PROMPT = """
You are a document specialist...
[Customize DOCX agent behavior...]
"""
```

### **Add New Tools** (DOCX Agent):
```python
# In react_agent/tools.py:
def my_custom_tool(param: str) -> str:
    """My custom tool description."""
    # Implementation
    return "result"

# Add to TOOLS list:
TOOLS = [
    search,
    get_sections,
    my_custom_tool,  # Your new tool
    # ... other tools
]
```

---

## **🐛 Debugging**

### **Check Agent Routing**:
```python
# In main/src/agent/router.py - add logging:
print(f"Routing decision: {last_supervisor_message}")
```

### **View RAG Database**:
```bash
# Check if session.db exists
ls -l main/session.db

# Check content
sqlite3 main/session.db
> SELECT COUNT(*) FROM default;
```

### **Monitor LangGraph**:
```bash
# LangGraph Studio (if available)
langgraph up --watch

# Or check logs
tail -f main/langgraph.log
```

---

## **📊 Key Files Reference**

| File | Purpose |
|------|---------|
| `main/src/agent/graph.py` | Main supervisor system |
| `main/src/agent/agents.py` | All agent implementations |
| `main/src/agent/router.py` | Routing logic |
| `main/src/agent/state.py` | State schema |
| `main/src/react_agent/graph.py` | DOCX agent (ReAct) |
| `main/src/react_agent/tools.py` | DOCX tools |
| `main/src/react_agent/prompts.py` | DOCX agent prompts |
| `main/src/agent/RFP_proposal_agent.py` | RFP team logic |
| `backend/agent_runner.py` | Agent execution wrapper |
| `backend/app.py` | API endpoints + Socket.IO |

---

## **🚀 Quick Reference**

### **Agent Selection Decision Tree**:
```
User Message Contains...
│
├─ "pdf" or ".pdf" → PDF Parser Agent
├─ "docx" or "document" → DOCX Agent
├─ "add images" → Image Adder Agent
├─ "generate proposal" + "technical" → RFP Technical Team
├─ "generate proposal" + "finance" → RFP Finance Team
├─ "generate proposal" + "legal" → RFP Legal Team
├─ "generate proposal" + "qa" → RFP QA Team
└─ General question → General Assistant Agent
```

### **Common Commands**:
```bash
# Parse PDF and create RAG
"Parse /path/to/doc.pdf"

# Query documents
"What are the requirements?"

# Create document
"Create new proposal document"

# Add section
"Add Technical Architecture section"

# Generate RFP content
"Generate finance section for 3-year SOC contract"

# Render final document
"Render the document"

# Add images
"Add images to the document"
```

---

**Built with**: LangGraph, LangChain, OpenAI, Milvus, FastAPI, React
**Architecture**: Multi-agent supervisor system with specialized teams
**Status**: Production Ready ✅

# Image Adder Node - Architecture Diagram

## System Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER REQUEST                             │
│  "Add images to the document" / "Insert pictures"               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        SUPERVISOR AGENT                          │
│  - Analyzes user intent                                          │
│  - Routes to appropriate agent                                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                     ┌───────┴───────┐
                     │   ROUTER      │
                     │  Priority 2   │
                     │  Image Check  │
                     └───────┬───────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      IMAGE ADDER NODE                            │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  STEP 1: Get Document Structure                          │  │
│  │  - Call docx_manager.get_outline()                       │  │
│  │  - Extract all headings with anchors                     │  │
│  └───────────────────────────┬───────────────────────────────┘  │
│                               ▼                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  STEP 2: Load Image Metadata                             │  │
│  │  - Read CSV file (image_name_dicription.csv)            │  │
│  │  - Validate image files exist                            │  │
│  └───────────────────────────┬───────────────────────────────┘  │
│                               ▼                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  STEP 3: AI-Powered Matching                             │  │
│  │  - Format outline + image list                           │  │
│  │  - Send to LLM (GPT-4o-mini)                            │  │
│  │  - Parse matches: "image.png -> Section 3"              │  │
│  └───────────────────────────┬───────────────────────────────┘  │
│                               ▼                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  STEP 4: Insert Images                                    │  │
│  │  - For each match:                                        │  │
│  │    • Call docx_manager.insert_image()                    │  │
│  │    • Position: after section heading                     │  │
│  │    • Width: 5 inches (default)                           │  │
│  └───────────────────────────┬───────────────────────────────┘  │
│                               ▼                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  STEP 5: Report Results                                   │  │
│  │  - Count successful insertions                            │  │
│  │  - List inserted images + sections                        │  │
│  │  - Report any errors                                      │  │
│  └───────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        END (SUCCESS)                             │
│  Returns AIMessage with detailed results                         │
└─────────────────────────────────────────────────────────────────┘
```

## Component Interaction

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   graph.py   │────▶│  router.py   │────▶│ image_adder_ │
│  (workflow)  │     │  (routing)   │     │   node.py    │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                     ┌────────────────────────────┘
                     │
          ┌──────────▼──────────┐
          │  docx_manager.py    │
          │  ┌──────────────┐   │
          │  │ get_outline()│   │
          │  └──────────────┘   │
          │  ┌──────────────┐   │
          │  │insert_image()│   │
          │  └──────────────┘   │
          └─────────────────────┘
                     │
          ┌──────────▼──────────┐
          │   master.docx       │
          │  (target document)  │
          └─────────────────────┘
```

## Data Flow

```
CSV File                    Document Outline
┌─────────────────────┐    ┌─────────────────────┐
│ Image Name,Desc     │    │ Heading 1: Intro    │
│ img1.png,Security   │    │ Heading 2: Arch     │
│ img2.png,Network    │    │ Heading 3: Security │
└──────────┬──────────┘    └──────────┬──────────┘
           │                          │
           └────────┬─────────────────┘
                    │
                    ▼
           ┌────────────────┐
           │   LLM (GPT)    │
           │ Semantic Match │
           └────────┬───────┘
                    │
                    ▼
           ┌────────────────┐
           │  Match Results │
           │  img1 -> Sec 3 │
           │  img2 -> Sec 2 │
           └────────┬───────┘
                    │
                    ▼
           ┌────────────────┐
           │ Insert Images  │
           │  into Sections │
           └────────────────┘
```

## Routing Logic

```
User Message
     │
     ▼
Contains "add images"?  ────YES───▶ image_adder
     │
     NO
     │
     ▼
Contains "image_adder"? ────YES───▶ image_adder
     │
     NO
     │
     ▼
Contains "insert pictures"? ─YES──▶ image_adder
     │
     NO
     │
     ▼
[Check other agents...]
```

## Edge Connections

```
┌─────────┐
│  START  │
└────┬────┘
     │
     ▼
┌──────────────┐
│ supervisor   │
└──────┬───────┘
       │
       ├─────────────────┐
       │                 │
       ▼                 ▼
┌──────────────┐   ┌──────────────┐
│ docx_agent   │   │ image_adder  │
└──────┬───────┘   └──────┬───────┘
       │                  │
       ▼                  ▼
┌──────────────┐   ┌──────────────┐
│     END      │   │     END      │
└──────────────┘   └──────────────┘

Note: Image Adder has a DIRECT edge to END
      (separate path from other nodes)
```

## State Structure

```
MessagesState
├── messages: List[Message]
│   ├── HumanMessage("Add images")
│   ├── AIMessage(name="supervisor", content="route to image_adder")
│   └── AIMessage(name="image_adder", content="✅ Success...")
│
└── [Other state fields...]
```

## Technology Stack

```
┌─────────────────────────────────────┐
│         Application Layer           │
│  - image_adder_node.py              │
│  - Async/Await pattern              │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│       LangGraph Framework           │
│  - StateGraph                       │
│  - Conditional Edges                │
│  - Message Passing                  │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│         LangChain Layer             │
│  - ChatOpenAI                       │
│  - Message Types                    │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│       Document Processing           │
│  - python-docx (write)              │
│  - docx2python (read)               │
│  - DocxManager (custom)             │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│        File System Layer            │
│  - CSV (metadata)                   │
│  - PNG images                       │
│  - DOCX document                    │
└─────────────────────────────────────┘
```

## Sequence Diagram

```
User          Supervisor      Router      ImageAdder      LLM         DocxManager
 │                │             │              │           │               │
 │─"Add images"──▶│             │              │           │               │
 │                │             │              │           │               │
 │                │──route?────▶│              │           │               │
 │                │◀─image_adder─│             │           │               │
 │                │             │              │           │               │
 │                │────execute──────────────▶  │           │               │
 │                │             │              │           │               │
 │                │             │              │─get_outline()──────────▶  │
 │                │             │              │◀─headings──────────────┘  │
 │                │             │              │           │               │
 │                │             │              │─read CSV──│               │
 │                │             │              │           │               │
 │                │             │              │──match?──▶│               │
 │                │             │              │◀─matches──┘               │
 │                │             │              │           │               │
 │                │             │              │─insert_image()────────▶   │
 │                │             │              │◀─success───────────────┘  │
 │                │             │              │           │               │
 │◀────────result message────────────────────  │           │               │
 │                │             │              │           │               │
```

## Module Dependencies

```
image_adder_node.py
├── os
├── csv
├── pathlib.Path
├── typing (Dict, Any, List)
├── langchain_openai.ChatOpenAI
├── langchain_core.messages (AIMessage, HumanMessage)
└── react_agent.docx_manager.get_docx_manager
        ├── docx2python
        ├── docx (python-docx)
        └── react_agent.docx_indexer
```

## Error Handling Flow

```
Try:
  ┌─────────────────────┐
  │ Get Outline         │
  └──────────┬──────────┘
             │ Error? ──▶ Return "No headings found"
             ▼
  ┌─────────────────────┐
  │ Read CSV            │
  └──────────┬──────────┘
             │ Error? ──▶ Return "CSV not found"
             ▼
  ┌─────────────────────┐
  │ LLM Matching        │
  └──────────┬──────────┘
             │ Error? ──▶ Continue (graceful degradation)
             ▼
  ┌─────────────────────┐
  │ Insert Images       │
  └──────────┬──────────┘
             │ Error? ──▶ Log error, continue with next
             ▼
  ┌─────────────────────┐
  │ Return Results      │
  └─────────────────────┘

Catch:
  Return error message to user
```


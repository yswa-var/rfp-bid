# Agent Routing Guide

## Overview

The multi-agent supervisor system now supports **independent routing** to each agent with **priority-based routing logic** to ensure queries go to the right agent.

## Available Agents

### 1. **docx_agent** - Document Operations Agent
- **Purpose**: Handles ALL Word document operations independently
- **Capabilities**: 
  - Read, search, edit, create, modify DOCX files
  - Update document titles, content, sections
  - Apply formatting and structure
- **Works independently**: YES

### 2. **pdf_parser** - PDF Processing Agent
- **Purpose**: Parses PDF files and creates RAG database
- **Capabilities**:
  - Parse PDF files from provided paths
  - Extract text chunks
  - Automatically create RAG database
- **Works independently**: YES

### 3. **general_assistant** - Knowledge Query Agent
- **Purpose**: Answers questions using the RAG database
- **Capabilities**:
  - Query existing knowledge base
  - Answer questions about indexed documents
  - Provide information from RAG
- **Works independently**: YES

### 4. **rfp_supervisor** - RFP Proposal Team Manager
- **Purpose**: Manages complete RFP proposal generation
- **Capabilities**:
  - Coordinates finance, technical, legal, and QA teams
  - Generates comprehensive RFP proposals
  - Creates structured proposal documents
- **Works independently**: YES

## Routing Priority System

The router checks user queries in the following priority order:

### Priority 1: Explicit Agent Names (HIGHEST)
If you mention an agent name explicitly, it will route directly to that agent:

```
✅ "use docx_agent to update the title"
✅ "docx_agent: edit the document"
✅ "pdf_parser: process these files"
✅ "general_assistant: what is..."
✅ "rfp_supervisor: generate proposal"
```

### Priority 2: DOCX/Document Operations
Any document-related operation routes to `docx_agent`:

```
✅ "update the docx_agent document title to rfp-olools-9903"
✅ "edit the Word document"
✅ "modify document section 2"
✅ "read the docx file"
✅ "create a new Word document"
✅ "update document title"
✅ "change document content"
```

**Important**: Even if "rfp" appears in a filename, document operations go to docx_agent!

### Priority 3: PDF Operations
PDF parsing and indexing routes to `pdf_parser`:

```
✅ "parse this PDF file"
✅ "index PDFs from /path/to/files"
✅ "extract from PDF"
✅ "upload PDF for processing"
```

### Priority 4: RFP Proposal Generation
Only COMPLETE RFP proposal generation routes to `rfp_supervisor`:

```
✅ "generate a new RFP proposal"
✅ "create RFP proposal for cybersecurity services"
✅ "draft a proposal for this RFP"
✅ "prepare an RFP response"
✅ "I need finance team input for the proposal"
```

**Note**: Simply mentioning "rfp" in a filename does NOT trigger rfp_supervisor!

### Priority 5: General Questions
Other queries route to `general_assistant`:

```
✅ "what is the budget mentioned in the documents?"
✅ "tell me about the security requirements"
✅ "what information do we have on..."
```

## Examples: Before vs After Fix

### Example 1: Document Title Update
**Query**: `"update the docx_agent document title to rfp-olools-9903"`

- **Before (WRONG)**: Routed to `rfp_supervisor` ❌ (because "rfp" was detected)
- **After (CORRECT)**: Routed to `docx_agent` ✅ (because "docx_agent" is explicitly mentioned AND "update document title" is a document operation)

### Example 2: Direct Agent Call
**Query**: `"docx_agent read the current document"`

- **Before**: Would check keywords, might route incorrectly
- **After**: Immediately routes to `docx_agent` ✅ (Priority 1: explicit agent name)

### Example 3: PDF Processing
**Query**: `"parse the RFP PDF files"`

- **Before**: Might route to `rfp_supervisor` (because "RFP" was detected first)
- **After**: Routes to `pdf_parser` ✅ (because "parse" and "PDF" indicate PDF processing, even though "RFP" is mentioned)

### Example 4: RFP Proposal Generation
**Query**: `"generate a complete RFP proposal for cybersecurity services"`

- **Before**: Correctly routes to `rfp_supervisor` ✅
- **After**: Still correctly routes to `rfp_supervisor` ✅ (Priority 4: clear intent to generate proposal)

### Example 5: General Knowledge Query
**Query**: `"what is the total budget in the documents?"`

- **Before**: Correctly routes to `general_assistant` ✅
- **After**: Still correctly routes to `general_assistant` ✅ (Priority 5: general question)

## Testing the Routing

You can test each agent independently with these queries:

```python
# Test docx_agent
"docx_agent: create a new document with title 'Test Document'"
"update the document title to rfp-2024-001"
"edit the Word document and add a section"

# Test pdf_parser
"pdf_parser: index all PDFs in /path/to/pdfs"
"parse PDF files from the examples folder"

# Test general_assistant
"general_assistant: what information do we have about security?"
"what is mentioned about pricing in the documents?"

# Test rfp_supervisor
"rfp_supervisor: generate a new RFP proposal for IT services"
"create a complete RFP proposal with finance and technical sections"
```

## Key Improvements

1. ✅ **Explicit agent names take highest priority** - Direct control over routing
2. ✅ **Document operations clearly identified** - No confusion with RFP proposal generation
3. ✅ **Context-aware RFP detection** - Only routes to RFP when GENERATING proposals, not when "rfp" is just part of a name
4. ✅ **Independent agent operation** - All agents can be used directly without cross-interference
5. ✅ **Clear priority order** - Predictable and logical routing behavior

## Troubleshooting

If your query isn't routing correctly:

1. **Use explicit agent names** - Most reliable method: `"docx_agent: your task"`
2. **Check the priority order** - Higher priority keywords override lower ones
3. **Be specific with intent** - "edit document" vs "generate proposal"
4. **Avoid ambiguous keywords** - If both "rfp" and "document" are present, be explicit

## Summary

The routing system now ensures that:
- ✅ Each agent can work **independently**
- ✅ Document operations (even with "rfp" in filenames) go to `docx_agent`
- ✅ PDF operations go to `pdf_parser`
- ✅ RFP proposal generation (the full workflow) goes to `rfp_supervisor`
- ✅ General queries go to `general_assistant`
- ✅ Explicit agent names always take priority


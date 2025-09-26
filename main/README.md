## **Architecture Overview**

The `proposal_supervisor_graph = build_parent_proposal_graph()` creates a **hierarchical two-level architecture**:

### **Level 1: Parent Supervisor** 
- **Single orchestrator node**: `proposal_supervisor` (ProposalSupervisorAgent)
- **Decision maker**: Routes work sequentially to specialized teams  
- **State management**: Tracks team completion, collects all responses
- **Flow control**: Determines when to end (all teams completed)

### **Level 2: Team Subgraphs (4 teams)**
Each team is a **compiled StateGraph as a node**:
- **`technical_team`**: Technical solutions & architecture  
- **`finance_team`**: Pricing & financial analysis
- **`legal_team`**: Terms, compliance & contracts
- **`qa_team`**: Quality assurance & risk management  

### **Flow Pattern: Sequential Execution**
```
START → proposal_supervisor → [team_X] → proposal_supervisor → [team_Y] → ... → proposal_supervisor → final_compose → END
```

**Each subgraph has 2-step flow:**
```
Team subgraph: rag_query → compose_section → END
```

### **Key Architecture Features**
- **Sequential processing**: One team at a time (not parallel)
- **State propagation**: Teams → supervisor → next team  
- **Conditional routing**: Supervisor decides which team next via `proposal_team_router`
- **Bi-directional**: All teams return control to supervisor
- **Specialized agents**: Each team uses team-specific RAG queries and LLM prompts

This creates a **sequential pipeline** where the supervisor orchestrates 4 specialized team subgraphs to build comprehensive RFPs section by section.

## Updated FLOW:

### Template Node
**Role**: Create or refine the template. 
**Input**: 
  - Already present template.json if created for the current section (optional)
  - RFP document application summary and notes as RFP contains ("application should include...")
**Output**: 
  - Template JSON

```json
  {
  "template_metadata": {
    "section_name": "Technical Solution Architecture",
    "rfp_id": "RFP-2024-CYBERSEC-001",
    "created_date": "2024-01-15",
    "version": "1.0",
    "team_assigned": "technical_team"
  },
  "rfp_requirements": {
    "application_should_include": [
      "Detailed technical architecture diagram",
      "Security controls and compliance measures",
      "Scalability and performance specifications",
      "Integration capabilities with existing systems",
      "Disaster recovery and business continuity plans"
    ],
    "mandatory_components": [
      "Network architecture overview",
      "Data protection mechanisms",
      "Monitoring and logging systems",
      "Incident response procedures"
    ],
    "evaluation_criteria": [
      "Technical feasibility (40%)",
      "Security implementation (30%)",
      "Cost-effectiveness (20%)",
      "Innovation and best practices (10%)"
    ]
  },
  "template_structure": {
    "section_title": "Technical Solution Architecture",
    "subsections": [
      {
        "title": "System Architecture Overview",
        "prompts": [
          "Provide a comprehensive overview of the proposed system architecture",
          "Include network diagrams showing component relationships",
          "Explain how the architecture meets scalability requirements",
          "Detail the technology stack and infrastructure components"
        ],
        "required_elements": [
          "Architecture diagrams",
          "Component descriptions",
          "Data flow documentation",
          "Technology specifications"
        ],
        "max_length": 2000
      },
      {
        "title": "Security Implementation",
        "prompts": [
          "Describe security controls and compliance measures",
          "Explain data protection and encryption mechanisms",
          "Detail access control and authentication systems",
          "Address vulnerability management and patching procedures"
        ],
        "required_elements": [
          "Security controls matrix",
          "Compliance certifications",
          "Risk assessment",
          "Security monitoring tools"
        ],
        "max_length": 1500
      },
      {
        "title": "Integration and Compatibility",
        "prompts": [
          "Explain integration capabilities with existing systems",
          "Detail API specifications and protocols",
          "Address data migration and transition planning",
          "Describe third-party service integrations"
        ],
        "required_elements": [
          "Integration architecture",
          "API documentation",
          "Migration timeline",
          "Compatibility matrix"
        ],
        "max_length": 1200
      },
      {
        "title": "Disaster Recovery and Business Continuity",
        "prompts": [
          "Detail disaster recovery procedures and RTO/RPO targets",
          "Explain backup and recovery mechanisms",
          "Describe business continuity planning",
          "Address high availability and redundancy measures"
        ],
        "required_elements": [
          "DR procedures",
          "Backup strategies",
          "BCP documentation",
          "HA implementation"
        ],
        "max_length": 1000
      }
    ]
  },
  "team_guidelines": {
    "technical_team": {
      "focus_areas": [
        "System architecture and design",
        "Technology selection and justification",
        "Performance and scalability",
        "Security implementation"
      ],
      "deliverables": [
        "Technical architecture diagrams",
        "Technology specifications",
        "Performance metrics",
        "Security controls documentation"
      ],
      "rag_queries": [
        "Find similar cybersecurity architecture implementations",
        "Research best practices for SOC operations",
        "Look up compliance requirements for the industry",
        "Find performance benchmarks for security tools"
      ]
    }
  },
  "quality_checklist": [
    "All mandatory components are addressed",
    "Technical feasibility is demonstrated",
    "Security measures are comprehensive",
    "Integration capabilities are clearly explained",
    "Compliance requirements are met",
    "Performance targets are realistic"
  ],
  "output_format": {
    "structure": "markdown",
    "include_diagrams": true,
    "citation_style": "APA",
    "tone": "professional",
    "target_audience": "technical evaluators and procurement team"
  }
}
```

### Section-Specific Content Node

**Goal**: Parse through the template JSON and generate content for each section
**Input**: 
  - Template.json 
  - RFP RAG database
**Output**: Each section is generated (await for approval) and stored in template.json only 

**Human-in-the-loop checks**:
- **Intent**: Handle refinement in particular sections
- **Process**: Get human approval on all sections before finalizing 

**Loop Logic**:
```
if (approval == no): 
    reconstruct the section based on human feedback
if (approval == yes): 
    save the section
```

## Refinement-Request Subgraph
**Goal**: Handle change requests after all sections are approved and PDF is created. First identify the section/possible related sections to change, then make the changes.

#### Build-Context Node
**Goal**: Find path to section/possible related sections to change and prompt for refinement.
**Input**: Template.json cleaned (without prompts and required elements) - only sections
**Output**: Concerned JSON paths to fix and user request.

#### Generate-content
input: context from rag, context from Build-Context Node 
output: Each section is generated (await for approval) and updated in template.json

## Notes:
- We'll keep the sources searched in data file (JSON) for bibliography and easy manual reads
- On each document section content creation/updates, human approval is required (team cards) like Cursor IDE
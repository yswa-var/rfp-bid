"""
Multi-Agent Supervisor System (modular)

Supervisor agent routes queries to worker agents and handles iterative
clarifications as needed.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent

# Ensure 'src' is on sys.path so absolute imports work when loaded by path
_CURRENT_DIR = Path(__file__).resolve().parent
_SRC_DIR = _CURRENT_DIR.parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from agent.state import MessagesState
from agent.agents import PDFParserAgent, CreateRAGAgent, GeneralAssistantAgent 
from agent.tools import create_handoff_tool
from agent.multi_rag_integration import MultiRAGCoordinator

__all__ = ["graph"]

class MultiRAGSetupAgent:
    """Agent to setup the Multi-RAG system."""
    
    def __init__(self):
        self.coordinator = MultiRAGCoordinator()
    
    def setup_multi_rag(self, state: MessagesState) -> Dict[str, Any]:
        """Setup all three RAG databases."""
        try:
            self.coordinator.setup_databases()
            
            response = """✅ **Multi-RAG System Setup Complete!**

📚 **Available RAG Systems:**
- **Template RAG**: Contains proposal templates and structures
- **Examples RAG**: Contains historical RFP examples  
- **Session RAG**: Ready for current RFP documents

🎯 **Next Steps:**
- Say "generate proposal" to create a proposal using all RAG systems
- Or ask questions about templates, RFP examples, or upload current RFP
"""
            
            from langchain_core.messages import AIMessage
            return {
                "messages": [AIMessage(content=response, name="multi_rag_setup")],
                "multi_rag_ready": True
            }
            
        except Exception as e:
            from langchain_core.messages import AIMessage
            return {
                "messages": [AIMessage(content=f"❌ Multi-RAG setup failed: {e}", name="multi_rag_setup")]
            }


class ProposalGeneratorAgent:
    """Agent to generate proposals using Multi-RAG system with parallel processing."""
    
    def __init__(self):
        self.coordinator = MultiRAGCoordinator()
        self.llm = ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            temperature=0.3,
        )
    
    def get_best_template(self, rfp_content: str) -> dict:
        """Automatically select best template based on RFP content analysis."""
        try:
            # Analyze RFP content for template type
            analysis_prompt = f"""
            Analyze this RFP content and determine the best proposal template type:
            
            RFP Content: {rfp_content[:500]}
            
            Available template types:
            - cyber security: For cybersecurity, IT security, network security RFPs
            - software development: For software, application, system development RFPs  
            - consulting: For advisory, consulting, professional services RFPs
            - infrastructure: For IT infrastructure, cloud, hardware RFPs
            
            Return only the template type name.
            """
            
            template_type_response = self.llm.invoke(analysis_prompt)
            template_type = template_type_response.content.strip().lower()
            
            # Template library with multiple types
            templates = {
                "cyber security": {
                    "template-type": "cyber security",
                    "Sections": {
                        "Cover Page": "RFP title, reference number, organization name, submission deadline, vendor details.",
                        "Executive Summary": "High-level overview of the vendor's solution, approach, and unique value.",
                        "Company Information": "Background, legal status, years in business, key personnel, financial stability.",
                        "Understanding of Requirements": "Restatement of the problem/needs and how the vendor interprets the scope.",
                        "Proposed Solution / Approach": "Technical details, methodology, processes, tools, or technologies being proposed.",
                        "Deliverables": "Breakdown of tasks, milestones, timelines, and expected deliverables.",
                        "Timeline": "phases, dependencies, resource allocation.",
                        "Pricing": "Detailed pricing structure, assumptions, optional services, payment terms.",
                        "Experience & Case Studies": "Relevant projects, client references, success metrics.",
                        "Legal": "Terms & conditions, exceptions or clarifications to the RFP contract."
                    }
                },
                "software development": {
                    "template-type": "software development", 
                    "Sections": {
                        "Cover Page": "RFP title, reference number, organization name, submission deadline, vendor details.",
                        "Executive Summary": "High-level overview of development approach and unique value proposition.",
                        "Company Information": "Development team background, technical expertise, years in business.",
                        "Understanding of Requirements": "Analysis of functional and non-functional requirements.",
                        "Technical Architecture": "System design, technology stack, scalability approach.",
                        "Development Methodology": "Agile/waterfall approach, development phases, quality assurance.",
                        "Deliverables & Timeline": "Sprint planning, milestones, testing phases, deployment.",
                        "Pricing": "Development cost breakdown, maintenance pricing, support terms.",
                        "Portfolio & References": "Similar projects, technical case studies, client testimonials.",
                        "Legal": "IP ownership, licensing terms, warranty and support agreements."
                    }
                },
                "infrastructure": {
                    "template-type": "infrastructure",
                    "Sections": {
                        "Cover Page": "RFP title, reference number, organization name, submission deadline, vendor details.",
                        "Executive Summary": "Infrastructure solution overview and business value.",
                        "Company Information": "Infrastructure expertise, certifications, partnerships.",
                        "Understanding of Requirements": "Current state analysis and future state vision.",
                        "Technical Solution": "Architecture design, hardware/software specifications, integration approach.",
                        "Implementation Plan": "Migration strategy, phases, risk mitigation, testing.",
                        "Timeline & Resources": "Project phases, resource allocation, dependencies.",
                        "Pricing": "Hardware costs, software licensing, implementation, ongoing support.",
                        "Experience & Certifications": "Infrastructure projects, vendor partnerships, technical certifications.",
                        "Legal": "SLA terms, warranty, support agreements, compliance requirements."
                    }
                }
            }
            
            selected_template = templates.get(template_type, templates["cyber security"])
            print(f"📋 Selected template type: {selected_template['template-type']}")
            return selected_template
            
        except Exception as e:
            print(f"⚠️  Template selection failed, using default: {e}")
            return templates["cyber security"]
    
    def _generate_section_parallel(self, section_name: str, section_desc: str, rfp_content: str) -> str:
        """Generate a single section with 3-level context (for parallel execution)."""
        try:
            
            contexts = self.coordinator.query_all_rags(f"{section_name} {section_desc}", k=2)
            
            # Enhanced context formatting
            template_context = self._format_context_for_llm(contexts.get('template_context', []))
            examples_context = self._format_context_for_llm(contexts.get('examples_context', []))
            session_context = self._format_context_for_llm(contexts.get('session_context', []))
            
            # Generate section using LLM with structured prompt
            prompt = f"""Generate a professional {section_name} section for an RFP proposal response.

**Section Requirements:** {section_desc}

**CONTEXT LEVELS:**

**Level 1 - Template Context (Structure/Format):**
{template_context}

**Level 2 - Examples Context (Previous RFPs):**
{examples_context}

**Level 3 - Session Context (Current RFP):**
{session_context}

**Current RFP Details:** {rfp_content[:400]}

**INSTRUCTIONS:**
- Generate a comprehensive {section_name} that directly addresses: {section_desc}
- Use the template context for proper structure and format
- Incorporate relevant examples from similar RFPs
- Align closely with the current RFP requirements from session context
- Write in professional proposal language
- Make it specific and actionable, not generic
- Include relevant details that demonstrate understanding

**{section_name.upper()}:**"""

            response = self.llm.invoke(prompt)
            
            # Format the complete section
            section_content = f"""## {section_name}

**Requirements Addressed:** {section_desc}

{response.content}

**Context Sources:**
- Template: {self._get_context_summary(contexts.get('template_context', []))}
- Examples: {self._get_context_summary(contexts.get('examples_context', []))}
- Current RFP: {self._get_context_summary(contexts.get('session_context', []))}
"""
            return section_content
            
        except Exception as e:
            return f"""## {section_name}

**Error generating section:** {str(e)}

**Fallback Content:** This section addresses {section_desc} as outlined in the RFP requirements.
"""
    
    def generate_proposal(self, state: MessagesState) -> Dict[str, Any]:
        """Generate complete proposal using parallel processing and 3-level context."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import time
        
        try:
            messages = state.get("messages", [])
            if not messages:
                from langchain_core.messages import AIMessage
                return {
                    "messages": [AIMessage(content="Please provide RFP requirements to generate a proposal.", name="proposal_generator")]
                }
            
            # Get the last user message as RFP content
            from langchain_core.messages import HumanMessage
            user_messages = [m for m in messages if isinstance(m, HumanMessage)]
            if not user_messages:
                rfp_content = "General cybersecurity services RFP"
            else:
                rfp_content = user_messages[-1].content
            
            print(f"🎯 Starting proposal generation for: {rfp_content[:100]}...")
            start_time = time.time()
            
            # Get best template based on RFP analysis
            template = self.get_best_template(rfp_content)
            
            proposal_parts = [
                f"# 🎯 **PROPOSAL RESPONSE**",
                f"**Template Type:** {template['template-type'].title()}",
                f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
                f"**RFP Analysis:** {rfp_content[:300]}...\n",
                "---\n"
            ]
            
            # Generate sections in parallel
            print(f" Generating {len(template['Sections'])} sections in parallel...")
            
            with ThreadPoolExecutor(max_workers=4) as executor:

                future_to_section = {}
                for section_name, section_desc in template["Sections"].items():
                    future = executor.submit(
                        self._generate_section_parallel, 
                        section_name, 
                        section_desc, 
                        rfp_content
                    )
                    future_to_section[future] = section_name
                
                section_results = {}
                completed = 0
                total_sections = len(future_to_section)
                
                for future in as_completed(future_to_section):
                    section_name = future_to_section[future]
                    completed += 1
                    
                    try:
                        section_content = future.result(timeout=60) 
                        section_results[section_name] = section_content
                        print(f"✅ Completed {section_name} ({completed}/{total_sections})")
                        
                    except Exception as e:
                        error_content = f"## {section_name}\n\n❌ Error: {str(e)}\n"
                        section_results[section_name] = error_content
                        print(f"❌ Failed {section_name}: {str(e)}")
            
            for section_name in template["Sections"].keys():
                if section_name in section_results:
                    proposal_parts.append(section_results[section_name])
                    proposal_parts.append("") 
            
            end_time = time.time()
            generation_time = end_time - start_time
            
            proposal_parts.extend([
                "---",
                "## 📊 **GENERATION SUMMARY**",
                f"- **Sections Generated:** {len(section_results)}/{len(template['Sections'])}",
                f"- **Template Used:** {template['template-type']}",
                f"- **Generation Time:** {generation_time:.2f} seconds",
                f"- **Processing Method:** Parallel execution with 3-level RAG context",
                f"- **Context Sources:** Template RAG + Examples RAG + Session RAG"
            ])
            
            final_proposal = "\n".join(proposal_parts)
            
            from langchain_core.messages import AIMessage
            return {
                "messages": [AIMessage(content=final_proposal, name="proposal_generator")],
                "proposal_generated": True,
                "template_used": template['template-type'],
                "sections_generated": len(section_results),
                "generation_time": generation_time
            }
            
        except Exception as e:
            from langchain_core.messages import AIMessage
            return {
                "messages": [AIMessage(content=f"❌ Proposal generation failed: {e}", name="proposal_generator")]
            }
    
    def _format_context_for_llm(self, context_docs) -> str:
        """Format context documents for LLM processing with enhanced structure."""
        if not context_docs:
            return "No relevant context available."
        
        formatted = []
        for i, result in enumerate(context_docs[:2], 1):  
            if isinstance(result, dict):
                content = result.get('content', result.get('preview', str(result)))[:400]
                source = result.get('source_file', 'Unknown')
                accuracy = result.get('accuracy', 0)
                
                formatted.append(f"""**Source {i}:** {source} (Relevance: {accuracy:.1%})
{content}...""")
            else:
                formatted.append(f"**Source {i}:** {str(result)[:400]}...")
        
        return "\n\n".join(formatted)
    
    def _get_context_summary(self, context_docs) -> str:
        """Get a brief summary of context sources."""
        if not context_docs:
            return "None"
        
        sources = []
        for result in context_docs[:2]:
            if isinstance(result, dict):
                source = result.get('source_file', 'Unknown')
                sources.append(Path(source).name)
            else:
                sources.append("Unknown")
        
        return ", ".join(sources)
    
    def _format_context(self, context_docs):
        """Format context for display (legacy method for compatibility)."""
        if not context_docs:
            return "No relevant context found"
        
        formatted = []
        for i, result in enumerate(context_docs[:1]):
            if isinstance(result, dict):
                content = result.get('content', result.get('preview', str(result)))[:100]
                source = result.get('source_file', 'Unknown')
            else:
                content = str(result)[:100]
                source = 'Unknown'
            formatted.append(f"[{Path(source).name}] {content}...")
        
        return "\n".join(formatted)
    
    
def supervisor_router(state: MessagesState) -> str:
    """Enhanced router to handle Multi-RAG functionality."""
    messages = state.get("messages", [])
    
    if not messages:
        return "general_assistant"
    

    from langchain_core.messages import HumanMessage
    user_messages = [m for m in messages if isinstance(m, HumanMessage)]
    
    if user_messages:
        last_user_content = user_messages[-1].content.lower()
        
        if any(phrase in last_user_content for phrase in [
            "setup multi-rag", "setup rag", "multi rag", "template rag", 
            "setup databases", "multi-rag", "setup multi"
        ]):
            return "multi_rag_setup"
        

        if any(phrase in last_user_content for phrase in [
            "generate proposal", "create proposal", "proposal generation", "rfp response"
        ]):
            return "proposal_generator"
    
    # Check if session database was created - end the session
    last_message = messages[-1].content if hasattr(messages[-1], 'content') else ""
    if "Created Milvus session database 'session.db'" in last_message:
        return "__end__"
    
    if any(phrase in last_message for phrase in [
        "Session DB not found.",
        "Error connecting to session DB:",
        "Error processing your question:",
        "I couldn't find any relevant information"
    ]):
        return "__end__"
    
    # Get the last AI message from supervisor
    supervisor_messages = [msg for msg in messages if hasattr(msg, 'name') and msg.name == 'supervisor']
    if not supervisor_messages:
        return "general_assistant"
    
    last_supervisor_message = supervisor_messages[-1].content.lower()
    
    # Check supervisor's decision
    if "pdf_parser" in last_supervisor_message or "parse" in last_supervisor_message:
        return "pdf_parser"
    else:
        return "general_assistant"

def create_supervisor_system():
    """Create the complete supervisor system with worker agents."""

    supervisor_llm = ChatOpenAI(
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    pdf_parser_agent = PDFParserAgent()
    create_rag_agent = CreateRAGAgent()
    general_assistant = GeneralAssistantAgent()
    
    # New Multi-RAG agents
    multi_rag_setup_agent = MultiRAGSetupAgent()
    proposal_generator_agent = ProposalGeneratorAgent()

    supervisor_prompt = (
        "You are a supervisor managing multiple agents:\n"
        "- pdf_parser: Parses user-provided PDF paths and creates text chunks, then automatically creates the RAG database.\n"
        "- general_assistant: Answers questions using session.db and cites sources.\n"
        "- multi_rag_setup: Sets up the Multi-RAG system with templates, examples, and session databases.\n"
        "- proposal_generator: Generates proposals using all RAG systems with 3-level context.\n\n"
        "ROUTING INSTRUCTIONS:\n"
        "- If user mentions 'setup multi-rag', 'setup databases', 'multi rag', or 'template rag', respond EXACTLY with: 'I will route this to multi_rag_setup'.\n"
        "- If user asks 'generate proposal', 'create proposal', or 'rfp response', respond EXACTLY with: 'I will route this to proposal_generator'.\n"
        "- If user provides PDF files or asks to 'index PDFs', respond EXACTLY with: 'I will route this to pdf_parser'.\n"
        "- For other questions, respond EXACTLY with: 'I will route this to general_assistant'.\n"
        "- IMPORTANT: Always respond with exactly one routing decision using the exact phrases above.\n"
        "- Do not do any work yourself, only route to the appropriate agent."
    )

    supervisor_agent = create_react_agent(
        supervisor_llm,
        tools=[],
        prompt=supervisor_prompt,
        name="supervisor",
    )

    workflow = StateGraph(MessagesState)
    

    workflow.add_node("supervisor", supervisor_agent)
    workflow.add_node("pdf_parser", pdf_parser_agent.parse_pdfs)
    workflow.add_node("create_rag", create_rag_agent.create_rag_database)
    workflow.add_node("general_assistant", general_assistant.query_documents)

    workflow.add_node("multi_rag_setup", multi_rag_setup_agent.setup_multi_rag)
    workflow.add_node("proposal_generator", proposal_generator_agent.generate_proposal)

    workflow.add_edge(START, "supervisor")

    workflow.add_conditional_edges(
        "supervisor",
        supervisor_router,
        {
            "pdf_parser": "pdf_parser",
            "general_assistant": "general_assistant",
            "multi_rag_setup": "multi_rag_setup",      
            "proposal_generator": "proposal_generator",  
            "__end__": END
        }
    )
    
    # Existing flows
    workflow.add_edge("pdf_parser", "create_rag")
    workflow.add_edge("create_rag", END)
    workflow.add_edge("general_assistant", END)
    
    # New Multi-RAG flows
    workflow.add_edge("multi_rag_setup", END)
    workflow.add_edge("proposal_generator", END)

    return workflow.compile()

graph = create_supervisor_system()
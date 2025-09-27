#!/usr/bin/env python3
"""
Generate Structured Proposal JSON
Based on existing RFP-bid codebase to create comprehensive proposal following exact TOC structure.
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

# Add src to path
sys.path.append('src')

from agent.milvus_ops import MilvusOps
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class StructuredProposalGenerator:
    """Generate structured proposal JSON using existing RAG databases."""
    
    def __init__(self):
        """Initialize the generator with databases and LLM."""
        print("🔧 Initializing Structured Proposal Generator...")
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model="gpt-4", 
            temperature=0.3,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Initialize databases
        self.session_db = None
        self.template_db = None
        self.rfp_db = None
        
        self._load_databases()
    
    def _load_databases(self):
        """Load all available databases."""
        try:
            # Load session database
            if os.path.exists("session.db"):
                self.session_db = MilvusOps("session.db")
                print("✅ Session database loaded")
            
            # Load template database
            if os.path.exists("template_rag.db"):
                self.template_db = MilvusOps("template_rag.db")
                print("✅ Template database loaded")
            
            # Load RFP examples database
            if os.path.exists("rfp_rag.db"):
                self.rfp_db = MilvusOps("rfp_rag.db")
                print("✅ RFP examples database loaded")
                
        except Exception as e:
            print(f"⚠️ Database loading error: {e}")
    
    def _query_all_databases(self, query: str, k: int = 5) -> str:
        """Query all available databases and combine results."""
        context_parts = []
        
        # Query session database
        if self.session_db and hasattr(self.session_db, 'vector_store') and self.session_db.vector_store:
            try:
                results = self.session_db.query_database(query, k=k)
                if results:
                    session_context = "\n".join([r['content'] for r in results[:3]])
                    context_parts.append(f"SESSION DATABASE CONTEXT:\n{session_context}")
            except:
                pass
        
        # Query template database
        if self.template_db and hasattr(self.template_db, 'vector_store') and self.template_db.vector_store:
            try:
                results = self.template_db.query_database(query, k=k)
                if results:
                    template_context = "\n".join([r['content'] for r in results[:3]])
                    context_parts.append(f"TEMPLATE DATABASE CONTEXT:\n{template_context}")
            except:
                pass
        
        # Query RFP database
        if self.rfp_db and hasattr(self.rfp_db, 'vector_store') and self.rfp_db.vector_store:
            try:
                results = self.rfp_db.query_database(query, k=k)
                if results:
                    rfp_context = "\n".join([r['content'] for r in results[:3]])
                    context_parts.append(f"RFP EXAMPLES DATABASE CONTEXT:\n{rfp_context}")
            except:
                pass
        
        return "\n\n".join(context_parts) if context_parts else "No relevant context found in databases."
    
    def generate_section(self, section_title: str, section_description: str, subsections: List[str] = None) -> str:
        """Generate content for a specific section using RAG."""
        
        # Create comprehensive query for this section
        query_parts = [section_title, section_description]
        if subsections:
            query_parts.extend(subsections)
        
        query = f"{section_title} {section_description} " + " ".join(subsections or [])
        
        # Get context from all databases
        context = self._query_all_databases(query, k=5)
        
        # Create prompt for content generation
        prompt = PromptTemplate(
            template="""You are a professional proposal writer creating a comprehensive section for an RFP response.

SECTION TITLE: {section_title}
SECTION DESCRIPTION: {section_description}
SUBSECTIONS TO COVER: {subsections}

RELEVANT CONTEXT FROM DATABASES:
{context}

Create a detailed, professional section that:
1. Directly addresses the section title and description
2. Covers all specified subsections comprehensively
3. Uses information from the provided context when relevant
4. Maintains professional tone and structure
5. Provides specific, actionable content
6. Uses proper markdown formatting with headers and bullet points
7. Includes concrete examples and details where appropriate

Generate comprehensive content (aim for 800-1200 words) that would be suitable for a winning RFP proposal.
""",
            input_variables=["section_title", "section_description", "subsections", "context"]
        )
        
        # Generate content
        try:
            response = self.llm.invoke(
                prompt.format(
                    section_title=section_title,
                    section_description=section_description,
                    subsections=", ".join(subsections) if subsections else "None specified",
                    context=context
                )
            )
            return response.content
        except Exception as e:
            return f"Error generating content for {section_title}: {str(e)}"
    
    def generate_complete_proposal(self) -> Dict[str, Any]:
        """Generate the complete structured proposal following the exact TOC."""
        
        print("🚀 Starting comprehensive proposal generation...")
        
        # Define the exact structure from your TOC
        proposal_structure = {
            "1_summary": {
                "title": "1. Summary",
                "description": "Executive summary of the proposal, key points, and value proposition",
                "subsections": [
                    "Executive Overview",
                    "Key Benefits",
                    "Competitive Advantages",
                    "Success Metrics"
                ]
            },
            "2_about_cpx": {
                "title": "2. About CPX",
                "description": "Company overview, capabilities, and organizational information",
                "subsections": [
                    "2.1. CPX Purpose & Value",
                    "2.2. Key Information",
                    "2.3. Certifications & Accreditations",
                    "2.4. Organizational Structure",
                    "2.5. Team Composition"
                ]
            },
            "3_understanding_requirements": {
                "title": "3. Understanding of Requirements",
                "description": "Demonstration of comprehension of client needs and project scope",
                "subsections": [
                    "3.1. Project Scope Analysis",
                    "3.2. Stakeholder Requirements",
                    "3.3. Success Criteria",
                    "3.4. Risk Assessment"
                ]
            },
            "4_proposed_solution": {
                "title": "4. Proposed Solution",
                "description": "Detailed technical solution and approach methodology",
                "subsections": [
                    "4.1. Technical Architecture",
                    "4.2. Implementation Approach", 
                    "4.3. Solution Components",
                    "4.4. Integration Strategy"
                ]
            },
            "5_implementation_plan": {
                "title": "5. Implementation Plan",
                "description": "Project timeline, phases, milestones, and delivery schedule",
                "subsections": [
                    "5.1. Project Phases",
                    "5.2. Timeline & Milestones",
                    "5.3. Resource Allocation",
                    "5.4. Quality Assurance"
                ]
            },
            "6_team_experience": {
                "title": "6. Team and Experience",
                "description": "Team qualifications, past experience, and relevant expertise",
                "subsections": [
                    "6.1. Core Team Members",
                    "6.2. Relevant Experience",
                    "6.3. Similar Projects",
                    "6.4. Client References"
                ]
            },
            "7_pricing": {
                "title": "7. Pricing",
                "description": "Comprehensive cost breakdown and pricing model",
                "subsections": [
                    "7.1. Cost Breakdown",
                    "7.2. Pricing Model",
                    "7.3. Payment Terms",
                    "7.4. Value Analysis"
                ]
            },
            "8_terms_conditions": {
                "title": "8. Terms and Conditions",
                "description": "Legal terms, conditions, and contractual obligations",
                "subsections": [
                    "8.1. Contractual Terms",
                    "8.2. Service Level Agreements",
                    "8.3. Liability & Warranty",
                    "8.4. Intellectual Property"
                ]
            },
            "9_additional_services": {
                "title": "9. Additional Services",
                "description": "Optional services, add-ons, and future enhancements",
                "subsections": [
                    "9.1. Optional Modules",
                    "9.2. Future Enhancements",
                    "9.3. Support Services",
                    "9.4. Training Programs"
                ]
            },
            "10_appendices": {
                "title": "10. Appendices",
                "description": "Supporting documentation, certifications, and detailed technical specifications",
                "subsections": [
                    "10.1. Technical Specifications",
                    "10.2. Certifications",
                    "10.3. Case Studies",
                    "10.4. Additional Documentation"
                ]
            }
        }
        
        # Generate complete proposal
        complete_proposal = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "generator": "CPX Structured Proposal Generator",
                "version": "1.0",
                "total_sections": len(proposal_structure)
            },
            "proposal": {}
        }
        
        # Generate each section
        for section_key, section_info in proposal_structure.items():
            print(f"📝 Generating: {section_info['title']}")
            
            content = self.generate_section(
                section_info['title'],
                section_info['description'],
                section_info.get('subsections', [])
            )
            
            complete_proposal["proposal"][section_key] = {
                "title": section_info['title'],
                "description": section_info['description'],
                "subsections": section_info.get('subsections', []),
                "content": content,
                "generated_at": datetime.now().isoformat()
            }
        
        return complete_proposal

def main():
    """Main function to generate and save structured proposal."""
    
    print("=" * 60)
    print("🎯 CPX STRUCTURED PROPOSAL GENERATOR")
    print("=" * 60)
    
    try:
        # Initialize generator
        generator = StructuredProposalGenerator()
        
        # Generate complete proposal
        proposal = generator.generate_complete_proposal()
        
        # Save to file
        output_file = f"structured_proposal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(proposal, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Complete structured proposal saved to: {output_file}")
        print(f"📊 Generated {len(proposal['proposal'])} sections")
        print(f"📝 Total proposal size: {len(json.dumps(proposal, indent=2))} characters")
        
        # Print summary
        print("\n📋 SECTIONS GENERATED:")
        for section_key, section_data in proposal["proposal"].items():
            print(f"  ✓ {section_data['title']}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
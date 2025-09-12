#!/usr/bin/env python3
"""
Proposal Generation Orchestrator
"""

import sys
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.agent.multi_rag_integration import MultiRAGCoordinator

# Template structure for cybersecurity
CYBERSECURITY_TEMPLATE = {
    "template-type": "cyber security",
    "Sections": {
        "Cover Page": "RFP title, reference number, organization name, submission deadline, vendor details.",
        "Executive Summary": "High-level overview of the vendor's solution, approach, and unique value.",
        "Company Information": "Background, legal status, years in business, key personnel, financial stability.",
        "Understanding of Requirements": "Restatement of the problem/needs and how the vendor interprets the scope.",
        "Proposed Solution / Approach": "Technical details, methodology, processes, tools, or technologies being proposed.",
        "Experience & Case Studies": "Relevant projects, client references, success metrics."
    }
}

class ProposalGenerator:
    """Generates proposals using multi-RAG system."""
    
    def __init__(self):
        self.coordinator = MultiRAGCoordinator()
        
    def generate_section(self, section_name: str, section_requirements: str, rfp_content: str) -> str:
        """Generate a single section using 3-level context."""
        try:
            contexts = self.coordinator.query_all_rags(f"{section_name} {section_requirements}", k=2)
            
            section_content = f"""## {section_name}

**Requirements**: {section_requirements}

**Template Context**:
{self._format_context(contexts['template_context'])}

**Examples Context**:
{self._format_context(contexts['examples_context'])}

**Session Context**:
{self._format_context(contexts['session_context']) if contexts['session_context'] else "No current RFP loaded"}

**Generated Response**:
Based on the requirements and available context, this section addresses: {section_requirements}

Key points from RFP: {rfp_content[:200]}...

[This would be enhanced with actual LLM generation in production]
"""
            return section_content
            
        except Exception as e:
            return f"## {section_name}\n\nError generating section: {e}"
    
    def _format_context(self, context_docs):
        """Format context documents for display."""
        if not context_docs:
            return "No relevant context found."
        
        formatted = []
        for i, result in enumerate(context_docs[:2]):
            if isinstance(result, dict):
                content = result.get('content', result.get('preview', str(result)))[:150]
                source = result.get('source_file', 'Unknown')
            else:
                content = str(result)[:150]
                source = 'Unknown'
            
            formatted.append(f"- [{Path(source).name}] {content}...")
        
        return "\n".join(formatted)
    
    def generate_proposal(self, rfp_content: str, current_rfp_file: str = None) -> str:
        """Generate complete proposal."""

        if current_rfp_file and Path(current_rfp_file).exists():
            print(f"📄 Adding current RFP to session: {current_rfp_file}")
            self.coordinator.add_session_rfp(current_rfp_file)
        
        sections = []
        template = CYBERSECURITY_TEMPLATE
        
        sections.append(f"# PROPOSAL RESPONSE")
        sections.append(f"**Template Type**: {template['template-type']}")
        sections.append(f"**Generated**: {Path(__file__).parent}")
        sections.append("")
        
        # Generate each section
        for section_name, requirements in template["Sections"].items():
            print(f"🔧 Generating: {section_name}")
            section_content = self.generate_section(section_name, requirements, rfp_content)
            sections.append(section_content)
            sections.append("")
        
        return "\n".join(sections)

def main():
    """Main orchestration function."""
    
    print("🚀 Multi-RAG Proposal Generation System")
    print("=" * 50)
    
    generator = ProposalGenerator()
    
    print("\n📚 Setting up RAG databases...")
    generator.coordinator.setup_databases()
    
    rfp_content = """
    RFP for Cybersecurity Services - RFP-2025-CYBER-001
    
    REQUIREMENTS:
    - 24/7 Security Operations Center (SOC) monitoring
    - Advanced threat detection and response
    - Vulnerability management and penetration testing  
    - Compliance reporting (SOX, PCI-DSS)
    - Security incident response planning
    - Employee security awareness training
    
    TIMELINE: 12 months with 3-year extension option
    BUDGET: $500,000 - $1,000,000 annually
    ORGANIZATION: Financial Services Corp
    SUBMISSION DEADLINE: March 30, 2025
    """
    
    current_rfp_file = None
    
    print("\n📝 Generating proposal...")
    proposal = generator.generate_proposal(rfp_content, current_rfp_file)
    
    print("\n" + "="*50)
    print("📋 GENERATED PROPOSAL")
    print("="*50)
    print(proposal)

    output_file = "generated_proposal.md"
    with open(output_file, "w") as f:
        f.write(proposal)
    
    print(f"\n✅ Proposal saved to: {output_file}")
    print(f"📁 Full path: {Path(output_file).absolute()}")

if __name__ == "__main__":
    main()
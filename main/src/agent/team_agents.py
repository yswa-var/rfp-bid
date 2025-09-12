"""
Team Agents for Proposal Generation

Specialized agents for different aspects of proposal generation:
- TechnicalTeamAgent: Technical architecture, solution design, implementation
- FinanceTeamAgent: Pricing, cost breakdown, financial terms
- LegalTeamAgent: Terms & conditions, compliance, legal requirements
- QATeamAgent: Quality assurance, testing, validation, risk management
"""

import os
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage

from .state import MessagesState
from .proposal_rag_coordinator import ProposalRAGCoordinator


class BaseTeamAgent:
    """Base class for all team agents."""
    
    def __init__(self, team_name: str, specialization: str):
        self.team_name = team_name
        self.specialization = specialization
        self.coordinator = ProposalRAGCoordinator()
        self.llm = ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            temperature=0.3,
        )
    
    def query_rag_context(self, state: MessagesState) -> Dict[str, Any]:
        """Query RAG systems for relevant context."""
        try:
            messages = state.get("messages", [])
            if not messages:
                return state
            
            # Get RFP content
            user_messages = [m for m in messages if isinstance(m, HumanMessage)]
            rfp_content = user_messages[-1].content if user_messages else "General RFP"
            
            # Query with team-specific context
            query = f"{self.specialization} {rfp_content[:200]}"
            contexts = self.coordinator.query_all_rags(query, k=3)
            
            # Store context in state for composition
            state["rag_context"] = contexts
            state["team_specialization"] = self.specialization
            
            return state
            
        except Exception as e:
            print(f"❌ {self.team_name} RAG query failed: {e}")
            return state
    
    def compose_section(self, state: MessagesState) -> Dict[str, Any]:
        """Compose the team's section of the proposal."""
        try:
            contexts = state.get("rag_context", {})
            specialization = state.get("team_specialization", self.specialization)
            
            # Format contexts for LLM
            template_context = self._format_context_for_llm(contexts.get('template_context', []))
            examples_context = self._format_context_for_llm(contexts.get('examples_context', []))
            session_context = self._format_context_for_llm(contexts.get('session_context', []))
            
            # Get RFP content
            messages = state.get("messages", [])
            user_messages = [m for m in messages if isinstance(m, HumanMessage)]
            rfp_content = user_messages[-1].content if user_messages else "General RFP"
            
            # Generate team-specific section
            prompt = f"""Generate a professional proposal section focused on {specialization}.

**Team Specialization:** {self.team_name} - {specialization}

**CONTEXT LEVELS:**

**Level 1 - Template Context (Structure/Format):**
{template_context}

**Level 2 - Examples Context (Previous RFPs):**
{examples_context}

**Level 3 - Session Context (Current RFP):**
{session_context}

**Current RFP Details:** {rfp_content[:400]}

**INSTRUCTIONS:**
- Generate a Brief to the point crisp section that demonstrates expertise in {specialization}
- Use the template context for proper structure and format
- Incorporate relevant examples from similar RFPs
- Align closely with the current RFP requirements
- Write in professional proposal language
- Make it specific and actionable, not generic
- Include relevant details that demonstrate understanding of {specialization}

**{specialization.upper()} SECTION:**"""

            response = self.llm.invoke(prompt)
            
            # Format the complete section
            section_content = f"""## {specialization.title()}

**Team:** {self.team_name}
**Specialization:** {specialization}

{response.content}
"""
            
            # Store contribution in state
            team_contributions = state.get("team_contributions", {})
            team_contributions[self.team_name] = section_content
            state["team_contributions"] = team_contributions
            
            # Add completion message with proper team name mapping
            messages = state.get("messages", [])
            team_name_mapping = {
                "Technical Team": "technical_team",
                "Finance Team": "finance_team", 
                "Legal Team": "legal_team",
                "QA Team": "qa_team"
            }
            team_node_name = team_name_mapping.get(self.team_name, self.team_name.lower().replace(" ", "_"))
            
            messages.append(AIMessage(content=section_content, name=team_node_name))
            state["messages"] = messages
            
            return state
            
        except Exception as e:
            print(f"❌ {self.team_name} composition failed: {e}")
            # Add error message
            messages = state.get("messages", [])
            messages.append(AIMessage(content=f"❌ {self.team_name} failed: {str(e)}", name=self.team_name))
            state["messages"] = messages
            return state
    
    def _format_context_for_llm(self, context_docs) -> str:
        """Format context documents for LLM processing."""
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
    


class TechnicalTeamAgent(BaseTeamAgent):
    """Technical team agent for architecture, solution design, and implementation."""
    
    def __init__(self):
        super().__init__(
            team_name="Technical Team",
            specialization="Technical Architecture & Solution Design"
        )
    
    def compose_section(self, state: MessagesState) -> Dict[str, Any]:
        """Compose technical section with enhanced technical focus."""
        try:
            contexts = state.get("rag_context", {})
            
            # Format contexts for LLM
            template_context = self._format_context_for_llm(contexts.get('template_context', []))
            examples_context = self._format_context_for_llm(contexts.get('examples_context', []))
            session_context = self._format_context_for_llm(contexts.get('session_context', []))
            
            # Get RFP content
            messages = state.get("messages", [])
            user_messages = [m for m in messages if isinstance(m, HumanMessage)]
            rfp_content = user_messages[-1].content if user_messages else "General RFP"
            
            # Enhanced technical prompt
            prompt = f"""Generate a Brief to the point crisp technical architecture and solution design section for an RFP proposal.

**Technical Focus Areas:**
- System architecture and design patterns
- Technology stack and infrastructure
- Scalability and performance considerations
- Security architecture and controls
- Integration approaches and APIs
- Implementation methodology and best practices

**CONTEXT LEVELS:**

**Level 1 - Template Context (Structure/Format):**
{template_context}

**Level 2 - Examples Context (Previous RFPs):**
{examples_context}

**Level 3 - Session Context (Current RFP):**
{session_context}

**Current RFP Details:** {rfp_content[:400]}

**INSTRUCTIONS:**
- Generate a detailed technical section that demonstrates deep technical expertise
- Include specific technologies, frameworks, and architectural patterns
- Address scalability, security, and performance requirements
- Provide clear implementation approach and methodology
- Use technical terminology appropriately
- Include diagrams or technical specifications where relevant
- Demonstrate understanding of current technology trends

**TECHNICAL ARCHITECTURE & SOLUTION DESIGN:**"""

            response = self.llm.invoke(prompt)
            
            # Format the complete section
            section_content = f"""## Technical Architecture & Solution Design

**Team:** Technical Team
**Specialization:** System Architecture, Technology Stack, Implementation Approach

{response.content}
"""
            
            # Store contribution in state
            team_contributions = state.get("team_contributions", {})
            team_contributions["Technical Solution"] = section_content
            state["team_contributions"] = team_contributions
            
            # Add completion message
            messages = state.get("messages", [])
            messages.append(AIMessage(content=section_content, name="technical_team"))
            state["messages"] = messages
            
            return state
            
        except Exception as e:
            print(f"❌ Technical Team composition failed: {e}")
            messages = state.get("messages", [])
            messages.append(AIMessage(content=f"❌ Technical Team failed: {str(e)}", name="technical_team"))
            state["messages"] = messages
            return state


class FinanceTeamAgent(BaseTeamAgent):
    """Finance team agent for pricing, cost breakdown, and financial terms."""
    
    def __init__(self):
        super().__init__(
            team_name="Finance Team",
            specialization="Pricing & Financial Analysis"
        )
    
    def compose_section(self, state: MessagesState) -> Dict[str, Any]:
        """Compose finance section with enhanced financial focus."""
        try:
            contexts = state.get("rag_context", {})
            
            # Format contexts for LLM
            template_context = self._format_context_for_llm(contexts.get('template_context', []))
            examples_context = self._format_context_for_llm(contexts.get('examples_context', []))
            session_context = self._format_context_for_llm(contexts.get('session_context', []))
            
            # Get RFP content
            messages = state.get("messages", [])
            user_messages = [m for m in messages if isinstance(m, HumanMessage)]
            rfp_content = user_messages[-1].content if user_messages else "General RFP"
            
            # Enhanced finance prompt
            prompt = f"""Generate a Brief to the point crisp pricing and financial analysis section for an RFP proposal.

**Financial Focus Areas:**
- Detailed cost breakdown and pricing structure
- Budget analysis and cost optimization
- Payment terms and billing cycles
- Value proposition and ROI analysis
- Financial risk assessment and mitigation
- Optional services and add-ons pricing

**CONTEXT LEVELS:**

**Level 1 - Template Context (Structure/Format):**
{template_context}

**Level 2 - Examples Context (Previous RFPs):**
{examples_context}

**Level 3 - Session Context (Current RFP):**
{session_context}

**Current RFP Details:** {rfp_content[:400]}

**INSTRUCTIONS:**
- Generate a detailed financial section with specific pricing information
- Include cost breakdown by phases, components, or services
- Address budget constraints and provide value justification
- Include payment terms, billing cycles, and financial guarantees
- Demonstrate cost-effectiveness and competitive pricing
- Include ROI analysis and value proposition
- Address financial risks and mitigation strategies

**PRICING & FINANCIAL ANALYSIS:**"""

            response = self.llm.invoke(prompt)
            
            # Format the complete section
            section_content = f"""## Pricing & Financial Analysis

**Team:** Finance Team
**Specialization:** Cost Structure, Budget Analysis, Financial Terms

{response.content}
"""
            
            # Store contribution in state
            team_contributions = state.get("team_contributions", {})
            team_contributions["Pricing"] = section_content
            state["team_contributions"] = team_contributions
            
            # Add completion message
            messages = state.get("messages", [])
            messages.append(AIMessage(content=section_content, name="finance_team"))
            state["messages"] = messages
            
            return state
            
        except Exception as e:
            print(f"❌ Finance Team composition failed: {e}")
            messages = state.get("messages", [])
            messages.append(AIMessage(content=f"❌ Finance Team failed: {str(e)}", name="finance_team"))
            state["messages"] = messages
            return state


class LegalTeamAgent(BaseTeamAgent):
    """Legal team agent for terms & conditions, compliance, and legal requirements."""
    
    def __init__(self):
        super().__init__(
            team_name="Legal Team",
            specialization="Legal & Compliance"
        )
    
    def compose_section(self, state: MessagesState) -> Dict[str, Any]:
        """Compose legal section with enhanced legal focus."""
        try:
            contexts = state.get("rag_context", {})
            
            # Format contexts for LLM
            template_context = self._format_context_for_llm(contexts.get('template_context', []))
            examples_context = self._format_context_for_llm(contexts.get('examples_context', []))
            session_context = self._format_context_for_llm(contexts.get('session_context', []))
            
            # Get RFP content
            messages = state.get("messages", [])
            user_messages = [m for m in messages if isinstance(m, HumanMessage)]
            rfp_content = user_messages[-1].content if user_messages else "General RFP"
            
            # Enhanced legal prompt
            prompt = f"""Generate a Brief to the point crisp legal and compliance section for an RFP proposal.

**Legal Focus Areas:**
- Terms and conditions
- Compliance requirements and certifications
- Data protection and privacy policies
- Intellectual property rights
- Liability and warranty terms
- Contractual obligations and SLAs

**CONTEXT LEVELS:**

**Level 1 - Template Context (Structure/Format):**
{template_context}

**Level 2 - Examples Context (Previous RFPs):**
{examples_context}

**Level 3 - Session Context (Current RFP):**
{session_context}

**Current RFP Details:** {rfp_content[:400]}

**INSTRUCTIONS:**
- Generate a detailed legal section addressing compliance and contractual terms
- Include specific compliance certifications and standards
- Address data protection, privacy, and security requirements
- Define intellectual property rights and ownership
- Include liability limitations and warranty terms
- Address contractual obligations and service level agreements
- Demonstrate understanding of relevant legal frameworks

**LEGAL & COMPLIANCE:**"""

            response = self.llm.invoke(prompt)
            
            # Format the complete section
            section_content = f"""## Legal & Compliance

**Team:** Legal Team
**Specialization:** Terms & Conditions, Compliance, Legal Requirements

{response.content}
"""
            
            # Store contribution in state
            team_contributions = state.get("team_contributions", {})
            team_contributions["Legal"] = section_content
            state["team_contributions"] = team_contributions
            
            # Add completion message
            messages = state.get("messages", [])
            messages.append(AIMessage(content=section_content, name="legal_team"))
            state["messages"] = messages
            
            return state
            
        except Exception as e:
            print(f"❌ Legal Team composition failed: {e}")
            messages = state.get("messages", [])
            messages.append(AIMessage(content=f"❌ Legal Team failed: {str(e)}", name="legal_team"))
            state["messages"] = messages
            return state


class QATeamAgent(BaseTeamAgent):
    """QA team agent for quality assurance, testing, validation, and risk management."""
    
    def __init__(self):
        super().__init__(
            team_name="QA Team",
            specialization="Quality Assurance & Risk Management"
        )
    
    def _get_qa_fallback_content(self) -> str:
        """Provide fallback QA content when LLM fails."""
        return """Our Quality Assurance & Risk Management approach ensures the highest standards of service delivery:

**Testing Methodologies:**
- Comprehensive unit testing with 95%+ code coverage
- Integration testing for all system components
- User acceptance testing with stakeholder involvement
- Performance testing under various load conditions
- Security testing including penetration testing

**Validation Procedures:**
- Multi-stage review process with independent validation
- Automated testing pipelines with continuous integration
- Manual testing protocols for critical business functions
- Documentation review and compliance verification
- Client feedback integration and validation

**Risk Assessment & Mitigation:**
- Proactive risk identification and assessment framework
- Regular risk reviews and mitigation strategy updates
- Contingency planning for critical system failures
- Data backup and disaster recovery procedures
- Vendor risk management and third-party assessments

**Quality Metrics & Monitoring:**
- Real-time performance monitoring and alerting
- SLA tracking with 99.9% uptime targets
- Customer satisfaction surveys and feedback analysis
- Incident tracking and resolution metrics
- Continuous improvement based on performance data

**Continuous Improvement:**
- Regular process reviews and optimization
- Technology updates and security patches
- Staff training and certification programs
- Best practice implementation and knowledge sharing
- Innovation initiatives and process automation

**Standards & Certifications:**
- ISO 9001:2015 Quality Management System
- ISO 27001 Information Security Management
- SOC 2 Type II compliance
- Industry-specific certifications and standards
- Regular audits and compliance monitoring

This Brief to the point crisp QA framework ensures reliable, secure, and high-quality service delivery while maintaining continuous improvement and risk mitigation."""
    
    def compose_section(self, state: MessagesState) -> Dict[str, Any]:
        """Compose QA section with enhanced quality focus."""
        try:
            contexts = state.get("rag_context", {})
            
            # Format contexts for LLM
            template_context = self._format_context_for_llm(contexts.get('template_context', []))
            examples_context = self._format_context_for_llm(contexts.get('examples_context', []))
            session_context = self._format_context_for_llm(contexts.get('session_context', []))
            
            # Get RFP content
            messages = state.get("messages", [])
            user_messages = [m for m in messages if isinstance(m, HumanMessage)]
            rfp_content = user_messages[-1].content if user_messages else "General RFP"
            
            # Enhanced QA prompt
            prompt = f"""Generate a Brief to the point crisp quality assurance and risk management section for an RFP proposal.

**QA Focus Areas:**
- Quality assurance processes and methodologies
- Testing strategies and validation procedures
- Risk assessment and mitigation strategies
- Performance monitoring and metrics
- Continuous improvement processes
- Quality standards and certifications

**CONTEXT LEVELS:**

**Level 1 - Template Context (Structure/Format):**
{template_context}

**Level 2 - Examples Context (Previous RFPs):**
{examples_context}

**Level 3 - Session Context (Current RFP):**
{session_context}

**Current RFP Details:** {rfp_content[:400]}

**INSTRUCTIONS:**
- Generate a detailed QA section addressing quality processes and risk management
- Include specific testing methodologies and validation procedures
- Address risk assessment and mitigation strategies
- Define quality metrics and performance monitoring
- Include continuous improvement processes
- Address quality standards and certifications
- Demonstrate understanding of industry best practices

**QUALITY ASSURANCE & RISK MANAGEMENT:**"""

            try:
                response = self.llm.invoke(prompt)
                response_content = response.content
            except Exception as llm_error:
                print(f"⚠️  QA Team LLM call failed: {llm_error}")
                # Use fallback content when LLM fails
                response_content = self._get_qa_fallback_content()
            
            # Format the complete section
            section_content = f"""## Quality Assurance & Risk Management

**Team:** QA Team
**Specialization:** Testing, Validation, Risk Assessment

{response_content}
"""
            
            # Store contribution in state
            team_contributions = state.get("team_contributions", {})
            team_contributions["Quality Assurance"] = section_content
            state["team_contributions"] = team_contributions
            
            # Add completion message
            messages = state.get("messages", [])
            messages.append(AIMessage(content=section_content, name="qa_team"))
            state["messages"] = messages
            
            return state
            
        except Exception as e:
            print(f"❌ QA Team composition failed: {e}")
            # Provide fallback content even if everything fails
            fallback_content = self._get_qa_fallback_content()
            section_content = f"""## Quality Assurance & Risk Management

**Team:** QA Team
**Specialization:** Testing, Validation, Risk Assessment

{fallback_content}

**Note:** This content was generated using fallback due to system error.
"""
            
            messages = state.get("messages", [])
            messages.append(AIMessage(content=section_content, name="qa_team"))
            state["messages"] = messages
            return state

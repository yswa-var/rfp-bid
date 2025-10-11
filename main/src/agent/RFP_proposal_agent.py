"""
RFP Proposal Agent - Multi-node agent for generating RFP proposal content.

This agent provides specialized nodes for different aspects of RFP proposal generation:
- Finance Node: Financial and budgetary content
- Technical Node: Technical specifications and requirements
- Legal Node: Legal compliance and contract terms
- QA Node: Quality assurance and testing procedures

All responses are tracked in a JSON file for audit and review purposes.
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import OpenAIEmbeddings
from langchain_milvus import Milvus

from .milvus_ops import MilvusOps
from .rfp_rag import RFPRAG
from .template_rag import TemplateRAG


class RFPProposalAgent:
    """
    Multi-node RFP Proposal Agent with specialized content generation capabilities.
    
    Features:
    - Chat with GPT-3.5-turbo for general queries
    - Query RAG databases (RFP examples and templates)
    - Generate specialized proposal content (finance, technical, legal, QA)
    - Track all responses in JSON format
    """
    
    def __init__(
        self, 
        session_db_path: Optional[str] = None,
        rfp_rag_db: Optional[str] = None,
        template_rag_db: Optional[str] = None,
        response_file: str = "rfp_proposal_responses.json"
    ):
        """
        Initialize the RFP Proposal Agent.
        
        Args:
            session_db_path: Path to the main session database
            rfp_rag_db: Path to RFP examples database
            template_rag_db: Path to template database
            response_file: JSON file to track all responses
        """
        # Initialize OpenAI API key
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        # Initialize LLM for ChatGPT
        self.chat_llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.7,
            api_key=self.api_key
        )
        
        # Initialize specialized LLMs for different nodes (lower temperature for consistency)
        self.node_llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.3,
            api_key=self.api_key
        )
        
        # Set up database paths
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.session_db_path = session_db_path or os.path.join(base_dir, "session.db")
        self.rfp_rag_db = rfp_rag_db or os.path.join(base_dir, "src/agent/demo_rfp_rag.db")
        self.template_rag_db = template_rag_db or os.path.join(base_dir, "src/agent/demo_template_rag.db")
        
        # Initialize RAG systems
        self.milvus_ops: Optional[MilvusOps] = None
        self.rfp_rag: Optional[RFPRAG] = None
        self.template_rag: Optional[TemplateRAG] = None
        
        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-large",
            api_key=self.api_key
        )
        
        # Response tracking
        self.response_file = response_file
        self.responses: List[Dict[str, Any]] = []
        self._load_responses()
        
        # Initialize conversation history
        self.conversation_history: List[Any] = []
    
    def _load_responses(self):
        """Load existing responses from JSON file."""
        if os.path.exists(self.response_file):
            try:
                with open(self.response_file, 'r') as f:
                    self.responses = json.load(f)
                print(f"✅ Loaded {len(self.responses)} existing responses from {self.response_file}")
            except Exception as e:
                print(f"⚠️ Could not load response file: {e}")
                self.responses = []
        else:
            self.responses = []
    
    def _save_response(self, node_type: str, query: str, response: str, 
                       context: Optional[List[Dict]] = None, metadata: Optional[Dict] = None):
        """
        Save a response to the JSON tracking file.
        
        Args:
            node_type: Type of node (chat, finance, technical, legal, qa)
            query: The input query
            response: The generated response
            context: RAG context used (if any)
            metadata: Additional metadata
        """
        response_entry = {
            "timestamp": datetime.now().isoformat(),
            "node_type": node_type,
            "query": query,
            "response": response,
            "context": context or [],
            "metadata": metadata or {}
        }
        
        self.responses.append(response_entry)
        
        # Save to file
        try:
            with open(self.response_file, 'w') as f:
                json.dump(self.responses, f, indent=2)
            print(f"💾 Saved response to {self.response_file}")
        except Exception as e:
            print(f"⚠️ Could not save response: {e}")
    
    def _connect_to_vector_store(self, db_path: str) -> Optional[Milvus]:
        """
        Connect to a Milvus vector store.
        
        Args:
            db_path: Path to the Milvus database
            
        Returns:
            Milvus vector store instance or None if connection fails
        """
        try:
            if not os.path.exists(db_path):
                print(f"⚠️ Database not found: {db_path}")
                return None
            
            vector_store = Milvus(
                embedding_function=self.embeddings,
                connection_args={"uri": db_path},
                index_params={"index_type": "FLAT", "metric_type": "L2"},
            )
            print(f"✅ Connected to database: {db_path}")
            return vector_store
        except Exception as e:
            print(f"❌ Error connecting to database {db_path}: {e}")
            return None
    
    def chat_gpt(self, message: str, use_history: bool = True) -> str:
        """
        Chat with GPT-3.5-turbo using LangChain.
        
        Args:
            message: User message to send
            use_history: Whether to include conversation history
            
        Returns:
            AI response as string
        """
        try:
            if use_history:
                # Add user message to history
                self.conversation_history.append(HumanMessage(content=message))
                
                # Get response with history
                response = self.chat_llm.invoke(self.conversation_history)
                
                # Add AI response to history
                self.conversation_history.append(response)
            else:
                # Single message without history
                response = self.chat_llm.invoke([HumanMessage(content=message)])
            
            response_text = response.content
            
            # Save to tracking file
            self._save_response(
                node_type="chat",
                query=message,
                response=response_text,
                metadata={"use_history": use_history}
            )
            
            return response_text
            
        except Exception as e:
            error_msg = f"Error in chat_gpt: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg
    
    def query_rag(
        self, 
        query: str, 
        k: int = 5, 
        database: str = "session"
    ) -> List[Dict[str, Any]]:
        """
        Query RAG database and return results.
        
        Args:
            query: Search query
            k: Number of results to return
            database: Which database to query ("session", "rfp", "template", "all")
            
        Returns:
            List of search results with content, metadata, and scores
        """
        all_results = []
        
        try:
            # Query session database
            if database in ["session", "all"]:
                if not self.milvus_ops:
                    self.milvus_ops = MilvusOps(self.session_db_path)
                    self.milvus_ops.vector_store = self._connect_to_vector_store(self.session_db_path)
                
                if self.milvus_ops.vector_store:
                    session_results = self.milvus_ops.query_database(query, k)
                    for result in session_results:
                        result['database'] = 'session'
                    all_results.extend(session_results)
            
            # Query RFP database
            if database in ["rfp", "all"]:
                if not self.rfp_rag:
                    self.rfp_rag = RFPRAG(self.rfp_rag_db)
                
                if os.path.exists(self.rfp_rag_db):
                    rfp_results = self.rfp_rag.query_data(query, k)
                    for result in rfp_results:
                        result['database'] = 'rfp'
                    all_results.extend(rfp_results)
            
            # Query template database
            if database in ["template", "all"]:
                if not self.template_rag:
                    self.template_rag = TemplateRAG(self.template_rag_db)
                
                if os.path.exists(self.template_rag_db):
                    template_results = self.template_rag.query_data(query, k)
                    for result in template_results:
                        result['database'] = 'template'
                    all_results.extend(template_results)
            
            # Sort by accuracy if we have results from multiple databases
            if len(all_results) > k:
                all_results = sorted(all_results, key=lambda x: x.get('accuracy', 0), reverse=True)[:k]
            
            print(f"✅ Found {len(all_results)} total results for query: '{query}'")
            return all_results
            
        except Exception as e:
            print(f"❌ Error querying RAG: {str(e)}")
            return []
    
    def _generate_node_content(
        self, 
        node_type: str, 
        query: str, 
        system_prompt: str,
        k: int = 5
    ) -> Dict[str, Any]:
        """
        Internal method to generate content for specialized nodes.
        
        Args:
            node_type: Type of node (finance, technical, legal, qa)
            query: User query/requirement
            system_prompt: System prompt for the specific node
            k: Number of RAG results to use
            
        Returns:
            Dictionary with response and context
        """
        try:
            # Query RAG for context
            rag_results = self.query_rag(query, k=k, database="all")
            
            if not rag_results:
                print(f"⚠️ No RAG context found for {node_type} node")
                context_text = "No relevant context found in the database."
            else:
                # Format context from RAG results
                context_parts = []
                for i, result in enumerate(rag_results[:3], 1):
                    source = result.get('source_file', 'Unknown')
                    page = result.get('page', 'Unknown')
                    content = result.get('content', '')
                    accuracy = result.get('accuracy', 0)
                    db = result.get('database', 'unknown')
                    
                    context_parts.append(
                        f"Source {i} [{db}] ({source}, Page {page}, Accuracy: {accuracy:.2f}):\n{content}"
                    )
                
                context_text = "\n\n---\n\n".join(context_parts)
            
            # Create prompt template
            prompt = PromptTemplate(
                template="""
{system_prompt}

CONTEXT FROM RAG DATABASE:
{context}

USER REQUIREMENT:
{query}

Please generate comprehensive, professional content for the RFP proposal addressing the above requirement. 
Be specific, detailed, and ensure the content aligns with industry best practices.

RESPONSE:
""",
                input_variables=["system_prompt", "context", "query"]
            )
            
            # Generate response
            formatted_prompt = prompt.format(
                system_prompt=system_prompt,
                context=context_text,
                query=query
            )
            
            response = self.node_llm.invoke([HumanMessage(content=formatted_prompt)])
            response_text = response.content
            
            # Save to tracking file
            self._save_response(
                node_type=node_type,
                query=query,
                response=response_text,
                context=rag_results,
                metadata={
                    "num_sources": len(rag_results),
                    "avg_accuracy": sum(r.get('accuracy', 0) for r in rag_results) / len(rag_results) if rag_results else 0
                }
            )
            
            return {
                "success": True,
                "response": response_text,
                "context": rag_results,
                "metadata": {
                    "node_type": node_type,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            error_msg = f"Error in {node_type}_node: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "response": error_msg,
                "context": [],
                "metadata": {}
            }
    
    def finance_node(self, query: str, k: int = 5) -> Dict[str, Any]:
        """
        Generate finance-focused content for RFP proposal.
        
        Args:
            query: Financial requirement or question
            k: Number of RAG results to use for context
            
        Returns:
            Dictionary with response and context
        """
        system_prompt = """
You are a financial expert specializing in RFP proposals and budgeting. Your role is to generate 
comprehensive financial content for RFP proposals, including:

- Budget breakdowns and cost estimates
- Pricing models and payment terms
- Financial justifications and ROI analysis
- Cost-benefit analysis
- Resource allocation
- Financial risk assessment
- Payment schedules and milestones

Ensure all financial content is:
- Accurate and well-justified
- Compliant with industry standards
- Transparent and detailed
- Aligned with the client's requirements

DOCUMENT FORMATTING INSTRUCTIONS:
Your response will be used to update a DOCX document. Please format your content as follows:
- Start with a clear section heading (e.g., "# Financial Proposal" or "# Budget Overview")
- Use hierarchical headers (## for subsections, ### for sub-subsections)
- Use bullet points or numbered lists where appropriate
- Include tables for budget breakdowns using markdown table format
- Ensure the content is well-structured and ready for direct insertion into a Word document
- Each major section should be clearly labeled and easy to identify for document editing
"""
        
        return self._generate_node_content("finance", query, system_prompt, k)
    
    def technical_node(self, query: str, k: int = 5) -> Dict[str, Any]:
        """
        Generate technical-focused content for RFP proposal.
        
        Args:
            query: Technical requirement or question
            k: Number of RAG results to use for context
            
        Returns:
            Dictionary with response and context
        """
        system_prompt = """
You are a technical expert specializing in RFP proposals and technical specifications. Your role is to 
generate comprehensive technical content for RFP proposals, including:

- Technical architecture and design
- System requirements and specifications
- Technology stack and tools
- Implementation approach and methodology
- Integration requirements
- Scalability and performance considerations
- Security architecture
- Technical standards and compliance

Ensure all technical content is:
- Detailed and specific
- Based on current best practices
- Technically sound and feasible
- Aligned with industry standards

DOCUMENT FORMATTING INSTRUCTIONS:
Your response will be used to update a DOCX document. Please format your content as follows:
- Start with a clear section heading (e.g., "# Technical Approach" or "# Technical Architecture")
- Use hierarchical headers (## for subsections, ### for sub-subsections)
- Use bullet points or numbered lists for requirements and specifications
- Include diagrams descriptions or tables where technical details need to be organized
- Use markdown table format for technical specifications and comparisons
- Ensure the content is well-structured and ready for direct insertion into a Word document
- Each major section should be clearly labeled and easy to identify for document editing
"""
        
        return self._generate_node_content("technical", query, system_prompt, k)
    
    def legal_node(self, query: str, k: int = 5) -> Dict[str, Any]:
        """
        Generate legal-focused content for RFP proposal.
        
        Args:
            query: Legal requirement or question
            k: Number of RAG results to use for context
            
        Returns:
            Dictionary with response and context
        """
        system_prompt = """
You are a legal expert specializing in RFP proposals and contract law. Your role is to generate 
comprehensive legal content for RFP proposals, including:

- Contract terms and conditions
- Legal compliance requirements
- Liability and indemnification clauses
- Intellectual property rights
- Data protection and privacy
- Regulatory compliance
- Service level agreements (SLAs)
- Termination and dispute resolution

Ensure all legal content is:
- Legally sound and compliant
- Clear and unambiguous
- Protective of both parties' interests
- Aligned with relevant regulations and standards

DOCUMENT FORMATTING INSTRUCTIONS:
Your response will be used to update a DOCX document. Please format your content as follows:
- Start with a clear section heading (e.g., "# Legal Terms and Compliance" or "# Contractual Obligations")
- Use hierarchical headers (## for subsections, ### for sub-subsections)
- Use numbered lists for terms and conditions, clauses, and legal requirements
- Organize compliance requirements in clear, structured sections
- Use markdown table format for SLA metrics and compliance matrices
- Ensure the content is well-structured and ready for direct insertion into a Word document
- Each major section should be clearly labeled and easy to identify for document editing
"""
        
        return self._generate_node_content("legal", query, system_prompt, k)
    
    def qa_node(self, query: str, k: int = 5) -> Dict[str, Any]:
        """
        Generate QA/testing-focused content for RFP proposal.
        
        Args:
            query: QA/testing requirement or question
            k: Number of RAG results to use for context
            
        Returns:
            Dictionary with response and context
        """
        system_prompt = """
You are a QA and testing expert specializing in RFP proposals and quality assurance. Your role is to 
generate comprehensive QA content for RFP proposals, including:

- Testing strategies and methodologies
- Quality assurance processes
- Test planning and execution
- Acceptance criteria and testing procedures
- Quality metrics and KPIs
- Bug tracking and resolution processes
- Performance and load testing
- Security testing and compliance
- User acceptance testing (UAT)

Ensure all QA content is:
- Comprehensive and detailed
- Based on industry best practices
- Measurable and verifiable
- Aligned with quality standards

DOCUMENT FORMATTING INSTRUCTIONS:
Your response will be used to update a DOCX document. Please format your content as follows:
- Start with a clear section heading (e.g., "# Quality Assurance Plan" or "# Testing Methodology")
- Use hierarchical headers (## for subsections, ### for sub-subsections)
- Use numbered lists for test procedures, methodologies, and acceptance criteria
- Use bullet points for quality metrics and KPIs
- Use markdown table format for test plans, test cases, and quality metrics matrices
- Ensure the content is well-structured and ready for direct insertion into a Word document
- Each major section should be clearly labeled and easy to identify for document editing
"""
        
        return self._generate_node_content("qa", query, system_prompt, k)
    
    def get_all_responses(self, node_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all tracked responses, optionally filtered by node type.
        
        Args:
            node_type: Filter by node type (None for all)
            
        Returns:
            List of response entries
        """
        if node_type:
            return [r for r in self.responses if r.get('node_type') == node_type]
        return self.responses
    
    def clear_conversation_history(self):
        """Clear the conversation history for chat_gpt."""
        self.conversation_history = []
        print("✅ Conversation history cleared")
    
    def get_response_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all tracked responses.
        
        Returns:
            Dictionary with summary statistics
        """
        if not self.responses:
            return {"total": 0, "by_node": {}}
        
        by_node = {}
        for response in self.responses:
            node_type = response.get('node_type', 'unknown')
            by_node[node_type] = by_node.get(node_type, 0) + 1
        
        return {
            "total": len(self.responses),
            "by_node": by_node,
            "first_response": self.responses[0].get('timestamp') if self.responses else None,
            "last_response": self.responses[-1].get('timestamp') if self.responses else None
        }


# Example usage and testing
if __name__ == "__main__":
    print("=" * 60)
    print("RFP Proposal Agent - Initialization")
    print("=" * 60)
    
    # Initialize agent
    agent = RFPProposalAgent()
    
    # Test chat_gpt
    print("\n📱 Testing chat_gpt:")
    response = agent.chat_gpt("What are the key components of a good RFP proposal?")
    print(f"Response: {response[:200]}...")
    
    # Test query_rag
    print("\n🔍 Testing query_rag:")
    results = agent.query_rag("cybersecurity requirements", k=3)
    print(f"Found {len(results)} results")
    
    # Test finance_node
    print("\n💰 Testing finance_node:")
    finance_response = agent.finance_node("Create a budget breakdown for a 3-year cybersecurity project")
    print(f"Success: {finance_response['success']}")
    print(f"Response: {finance_response['response'][:200]}...")
    
    # Test technical_node
    print("\n🔧 Testing technical_node:")
    tech_response = agent.technical_node("Describe the technical architecture for a SOC solution")
    print(f"Success: {tech_response['success']}")
    print(f"Response: {tech_response['response'][:200]}...")
    
    # Get summary
    print("\n📊 Response Summary:")
    summary = agent.get_response_summary()
    print(json.dumps(summary, indent=2))
    
    print("\n✅ All tests completed!")


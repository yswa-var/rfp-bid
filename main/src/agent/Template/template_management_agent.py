#!/usr/bin/env python3
"""
Template Management AI Agent
A CLI-based agent that processes sessions, classifies documents, selects templates,
and iterates through template processing with JSON output.
"""

import json
import os
import hashlib
import argparse
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

# LangChain imports
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.schema import BaseOutputParser
from langchain_openai import OpenAI

# For environment variables
from dotenv import load_dotenv
from pydantic import SecretStr

load_dotenv()

class DocumentType(Enum):
    """Document classification types"""
    RFP_TECHNICAL = "rfp_technical"
    RFP_FINANCIAL = "rfp_financial" 
    RFP_GENERAL = "rfp_general"
    PROPOSAL_RESPONSE = "proposal_response"
    TEMPLATE_QUERY = "template_query"
    GENERIC_RFP = "generic_rfp"
    UNKNOWN = "unknown"

class TemplateCategory(Enum):
    """Template categories for selection"""
    TECHNICAL_PROPOSAL = "technical_proposal_template"
    FINANCIAL_PROPOSAL = "financial_proposal_template"
    COMPANY_PROFILE = "company_profile_template"
    PROJECT_METHODOLOGY = "project_methodology_template"
    GENERIC_RFP = "generic_rfp_template"
    CUSTOM = "custom_template"

@dataclass
class SessionContext:
    """Session context information"""
    session_id: str
    created_at: str
    last_updated: str
    query_count: int
    document_type: str
    template_category: str
    processing_history: List[Dict]

@dataclass
class ProcessingResult:
    """Result of agent processing"""
    session_id: str
    query_id: str
    timestamp: str
    original_query: str
    document_classification: Dict
    template_selection: Dict
    template_iteration: Dict
    final_output: Dict

class JSONOutputParser(BaseOutputParser):
    """Custom parser for JSON outputs"""

    def parse(self, text: str) -> Dict:
        try:
            start_idx = text.find('{')
            end_idx = text.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                json_str = text[start_idx:end_idx]
                return json.loads(json_str)
            else:
                return {
                    "raw_response": text.strip(),
                    "parsed": True,
                    "confidence": 0.5
                }
        except json.JSONDecodeError:
            return {
                "raw_response": text.strip(),
                "parsed": False,
                "error": "JSON parsing failed"
            }

class TemplateManagementAgent:
    """Main agent class for template management workflow"""

    def __init__(self, openai_api_key: Optional[str] = None):
        """Initialize the Template Management Agent"""
        self.api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key or not isinstance(self.api_key, str):
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass it directly.")

        # Initialize LLM
        self.llm = OpenAI(
            temperature=0,
            api_key=SecretStr(self.api_key),
        )

        # Initialize components
        self.json_parser = JSONOutputParser()
        self.sessions_file = "agent_sessions.json"
        self.outputs_file = "agent_outputs.json"

        # Load stored data
        self.sessions = self._load_sessions()
        self.outputs = self._load_outputs()

        # Setup LangChain chains
        self._setup_chains()

    def _setup_chains(self):
        """Setup LangChain chains for different processing steps"""

        session_prompt = PromptTemplate(
            input_variables=["query", "existing_sessions"],
            template="""
            Analyze the following query and determine which session it belongs to based on existing sessions.
            If it's a new session, generate a new session ID.

            Query: {query}
            Existing Sessions: {existing_sessions}

            Return a JSON response with:
            {{
                "session_id": "session_identifier",
                "is_new_session": true/false,
                "confidence": 0.0-1.0,
                "reasoning": "explanation of session assignment"
            }}
            """
        )
        self.session_chain = LLMChain(
            llm=self.llm,
            prompt=session_prompt,
            output_parser=self.json_parser
        )

        classification_prompt = PromptTemplate(
            input_variables=["query"],
            template="""
            Classify the following query/document into one of these categories:
            - rfp_technical
            - rfp_financial
            - rfp_general
            - proposal_response
            - template_query
            - generic_rfp
            - unknown

            Query: {query}

            Return a JSON response with:
            {{
                "document_type": "category_name",
                "confidence": 0.0-1.0,
                "key_indicators": ["list", "of", "keywords", "found"],
                "reasoning": "explanation of classification"
            }}
            """
        )
        self.classification_chain = LLMChain(
            llm=self.llm,
            prompt=classification_prompt,
            output_parser=self.json_parser
        )

        template_prompt = PromptTemplate(
            input_variables=["document_type", "query"],
            template="""
            Based on the document type and query content, select the most appropriate template:
            - technical_proposal_template
            - financial_proposal_template
            - company_profile_template
            - project_methodology_template
            - generic_rfp_template
            - custom_template

            Document Type: {document_type}
            Query: {query}

            Return a JSON response with:
            {{
                "selected_template": "template_name",
                "confidence": 0.0-1.0,
                "template_parameters": {{"key": "value"}},
                "customization_needed": true/false,
                "reasoning": "explanation of template selection"
            }}
            """
        )
        self.template_chain = LLMChain(
            llm=self.llm,
            prompt=template_prompt,
            output_parser=self.json_parser
        )

        iteration_prompt = PromptTemplate(
            input_variables=["template_info", "query", "previous_iterations"],
            template="""
            Iterate and refine the template based on the query requirements and previous iterations.

            Template Info: {template_info}
            Original Query: {query}
            Previous Iterations: {previous_iterations}

            Return a JSON response with:
            {{
                "iteration_number": 1,
                "refined_template": {{"structure": "template_structure"}},
                "improvements_made": ["list", "of", "improvements"],
                "completion_status": "in_progress/completed",
                "next_steps": ["suggested", "next", "actions"]
            }}
            """
        )
        self.iteration_chain = LLMChain(
            llm=self.llm,
            prompt=iteration_prompt,
            output_parser=self.json_parser
        )

    def _load_sessions(self) -> Dict:
        if os.path.exists(self.sessions_file):
            try:
                with open(self.sessions_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {}
        return {}

    def _load_outputs(self) -> List[Dict]:
        if os.path.exists(self.outputs_file):
            try:
                with open(self.outputs_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return []
        return []

    def _save_sessions(self):
        with open(self.sessions_file, 'w') as f:
            json.dump(self.sessions, f, indent=2)

    def _save_outputs(self):
        with open(self.outputs_file, 'w') as f:
            json.dump(self.outputs, f, indent=2)

    def _generate_session_id(self, query: str) -> str:
        timestamp = datetime.now().isoformat()
        content = f"{query[:50]}{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def _generate_query_id(self) -> str:
        timestamp = datetime.now().isoformat()
        return hashlib.md5(timestamp.encode()).hexdigest()[:8]

    def process_query(self, query: str) -> ProcessingResult:

        # Step 1: Session Processing
        existing_sessions_summary = {
            sid: {
                "type": session.get("document_type", "unknown"),
                "queries": session.get("query_count", 0)
            } for sid, session in self.sessions.items()
        }
        session_result = self.session_chain.invoke({
            "query": query,
            "existing_sessions": json.dumps(existing_sessions_summary, indent=2)
        })

        session_id = session_result.get("session_id") or self._generate_session_id(query)

        # Step 2: Document Classification
        classification_result = self.classification_chain.invoke({"query": query})
        document_type = classification_result.get("document_type", "unknown")

        # Step 3: Template Selection
        template_result = self.template_chain.invoke({
            "document_type": document_type,
            "query": query
        })
        selected_template = template_result.get("selected_template", "generic_rfp_template")

        # Step 4: Template Iteration
        previous_iterations = []
        if session_id in self.sessions:
            previous_iterations = self.sessions[session_id].get("processing_history", [])

        iteration_result = self.iteration_chain.invoke({
            "template_info": json.dumps(template_result, indent=2),
            "query": query,
            "previous_iterations": json.dumps(previous_iterations[-3:], indent=2)
        })

        # Final Result
        query_id = self._generate_query_id()
        timestamp = datetime.now().isoformat()
        result = ProcessingResult(
            session_id=session_id,
            query_id=query_id,
            timestamp=timestamp,
            original_query=query,
            document_classification=classification_result,
            template_selection=template_result,
            template_iteration=iteration_result,
            final_output={
                "session_id": session_id,
                "query_id": query_id,
                "document_type": document_type,
                "selected_template": selected_template,
                "processing_complete": iteration_result.get('completion_status') == 'completed',
                "context_db_ready": True,
                "metadata": {
                    "timestamp": timestamp,
                    "confidence_score": (
                        classification_result.get('confidence', 0.0) +
                        template_result.get('confidence', 0.0) + 0.8
                    ) / 3,
                    "iteration_count": iteration_result.get('iteration_number', 1)
                }
            }
        )

        # Update session
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "created_at": timestamp,
                "query_count": 0,
                "document_type": document_type,
                "template_category": selected_template,
                "processing_history": []
            }

        self.sessions[session_id]["last_updated"] = timestamp
        self.sessions[session_id]["query_count"] += 1
        self.sessions[session_id]["processing_history"].append({
            "query_id": query_id,
            "timestamp": timestamp,
            "query": query[:100] + "..." if len(query) > 100 else query,
            "result_summary": {
                "document_type": document_type,
                "template": selected_template,
                "status": iteration_result.get('completion_status', 'in_progress')
            }
        })

        # Save
        self.outputs.append(asdict(result))
        self._save_sessions()
        self._save_outputs()
        return result

    def get_session_summary(self, session_id: Optional[str] = None) -> Dict:
        if session_id:
            return self.sessions.get(session_id, {})
        return {
            "total_sessions": len(self.sessions),
            "sessions": self.sessions
        }

    def get_latest_outputs(self, limit: int = 5) -> List[Dict]:
        return self.outputs[-limit:] if len(self.outputs) >= limit else self.outputs

def run_agent(query: str, api_key: Optional[str] = None) -> Dict:
    """
    Helper function to process a query using TemplateManagementAgent
    and return the final output.
    """
    try:
        agent = TemplateManagementAgent()
        result = agent.process_query(query)
        return result.final_output
    except Exception as e:
        return {
            "error": str(e),
            "hint": "Check if your OPENAI_API_KEY is set correctly."
        }


def main():
    """
    Simplified main function — edit this if you want to hardcode a test query.
    """
    # Example usage: change this line or call run_agent() directly in your code
    test_query = "We need a financial proposal template for an RFP"
    output = run_agent(test_query)
    return json.dumps(output, indent=2)


if __name__ == "__main__":
    main()

"""Worker agent node implementations."""

import os
from typing import Dict, Any, List
from pydantic import BaseModel, Field

from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from .state import MessagesState
from .milvus_ops import MilvusOps

from .template_rag import TemplateRAG
from .rfp_rag import RFPRAG
import subprocess
import sys


class DocumentResponse(BaseModel):
    """Pydantic model for structured document analysis response."""
    answer: str = Field(description="Comprehensive answer based on the document context")
    confidence_score: int = Field(description="Integer from 0-10 (10 = highest confidence, 0 = lowest confidence)")
    follow_up_questions: List[str] = Field(description="List of follow-up questions if you want to ask the user to clarify the question and have a meening full conversations, empty list if none")
    document_references: List[str] = Field(description="List of source documents with pdf_name and page")
    sources: List[Dict[str, str]] = Field(description="List of source documents with pdf_name and page")


class PDFParserAgent:
    """Agent specialized in parsing PDF documents using MilvusOps."""

    def __init__(self):
        self.milvus_ops: MilvusOps | None = None

    def parse_pdfs(self, state: MessagesState) -> Dict[str, Any]:
        user_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
        if not user_messages:
            return {"messages": [AIMessage(content="Please provide PDF file path(s).")]}

        query = user_messages[-1].content

        # Extract potential PDF paths
        candidates: List[str] = []
        for token in query.replace("\n", " ").split():
            token = token.strip().strip('"\'')
            if token.lower().endswith(".pdf"):
                candidates.append(token)
        for segment in query.split(','):
            seg = segment.strip().strip('"\'')
            if seg.lower().endswith('.pdf'):
                candidates.append(seg)

        seen = set()
        pdf_paths = []
        for path in candidates:
            if path in seen:
                continue
            seen.add(path)
            if os.path.exists(path):
                pdf_paths.append(path)

        if not pdf_paths:
            return {
                "messages": [
                    AIMessage(
                        content=(
                            "I couldn't find valid PDF paths. Please paste absolute path(s), "
                            "separated by commas if multiple."
                        )
                    )
                ]
            }

        self.milvus_ops = MilvusOps("temp_chunks.db")
        all_chunks = []
        parsed_files = []

        for path in pdf_paths:
            try:
                documents = self.milvus_ops.parse_pdf(path)
                chunks = self.milvus_ops.create_chunks(documents)
                all_chunks.extend(chunks)
                parsed_files.append(path)
            except Exception as e:
                return {"messages": [AIMessage(content=f"Error parsing {path}: {e}")]}

        # Get chunk quality statistics
        quality_stats = self.milvus_ops.get_chunk_quality_stats(all_chunks)
        
        summary = (
            f"✅ Parsed {len(parsed_files)} PDF(s) and created {len(all_chunks)} high-quality chunks.\n"
            f"📊 Quality Stats: {quality_stats['cleaned_chunks']} cleaned, "
            f"{quality_stats['quality_improved_chunks']} improved, "
            f"avg {quality_stats['average_word_count']:.0f} words/chunk\n"
            f"📄 Document Types: {', '.join(quality_stats['document_types'].keys())}\n\n"
            "Say 'create rag' to build a session database (session.db), or provide more PDFs."
        )
        return {"messages": [AIMessage(content=summary)], "chunks": all_chunks, "pdf_paths": parsed_files}


class CreateRAGAgent:
    """Agent to create Milvus database from parsed chunks (session.db)."""

    def __init__(self):
        self.milvus_ops: MilvusOps | None = None

    def create_rag_database(self, state: MessagesState) -> Dict[str, Any]:
        chunks = state.get("chunks", [])
        if not chunks:
            return {
                "messages": [AIMessage(content="No chunks found. Please parse PDFs first (use the pdf_parser).")] 
            }

        try:
            self.milvus_ops = MilvusOps("src/agent/session.db")
            self.milvus_ops.vectorize_and_store(chunks)
            return {"messages": [AIMessage(content="✅ Created Milvus session database 'session.db'. End the session.")]}
        except Exception as e:
            return {"messages": [AIMessage(content=f"Error creating session DB: {e}")]}


class GeneralAssistantAgent:
    """Agent for querying the session.db and providing conversational answers with references."""

    def __init__(self):
        self.milvus_ops: MilvusOps | None = None
        self.llm = ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            temperature=0.1,
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        # Initialize Pydantic parser
        self.parser = PydanticOutputParser(pydantic_object=DocumentResponse)

    def query_documents(self, state: MessagesState) -> Dict[str, Any]:
        # Create MilvusOps instance and check if session.db exists
        # Use dynamic path resolution instead of hard-coded path
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        session_db_path = os.path.join(base_dir, "session.db")
        self.milvus_ops = MilvusOps(session_db_path)
        
        if not os.path.exists(self.milvus_ops.db_path):
            return {"messages": [AIMessage(content="Session DB not found. Please run create_rag after parsing PDFs.")]}

        # Connect to the existing vector store
        try:
            from langchain_milvus import Milvus
            from langchain_openai import OpenAIEmbeddings
            
            # Initialize embeddings
            embeddings = OpenAIEmbeddings(
                model="text-embedding-3-large",
                api_key=os.getenv("OPENAI_API_KEY")
            )
            
            # Connect to existing Milvus database
            self.milvus_ops.vector_store = Milvus(
                embedding_function=embeddings,
                connection_args={"uri": self.milvus_ops.db_path},
                index_params={"index_type": "FLAT", "metric_type": "L2"},
            )
            
        except Exception as e:
            return {"messages": [AIMessage(content=f"Error connecting to session DB: {e}")]}

        user_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
        if not user_messages:
            return {"messages": [AIMessage(content="Please provide a question to search the documents.")]}

        question = user_messages[-1].content
        
        try:
            # Retrieve relevant chunks
            results = self.milvus_ops.query_database(question, k=5)  # Get more chunks for better context
            if not results:
                return {"messages": [AIMessage(content="I couldn't find any relevant information in the documents to answer your question.")]}

            # Prepare context from retrieved chunks
            context_parts = []
            sources = []
            
            for i, result in enumerate(results[:3]):  # Use top 3 results
                context_parts.append(f"Source {i+1}:\n{result['content']}")
                sources.append(f"Source {i+1}: {result['source_file']} (Page {result['page']})")
            
            context = "\n\n".join(context_parts)
            source_references = "\n".join(sources)
            
            # Create prompt template with format instructions
            prompt_template = PromptTemplate(
                template="""You are an expert document analysis assistant. Based on the provided context from documents, provide a comprehensive and accurate answer to the user's question.

CONTEXT FROM DOCUMENTS:
{context}

USER'S QUESTION: {question}

INSTRUCTIONS:
- Analyze the provided context carefully
- Provide a thorough, accurate answer based solely on the document content
- If the context doesn't contain enough information to fully answer the question, indicate this in your response
- Generate follow-up questions that would help clarify or expand on the answer
- Return your response in the exact JSON format specified below

{format_instructions}

IMPORTANT: 
- Only use information from the provided context
- Be specific and cite relevant details from the documents
- Ensure your confidence_score reflects how well the context supports your answer
- Include all relevant source documents and page numbers in the sources array
- For sources, use the actual PDF filenames from the context""",
                input_variables=["context", "question"],
                partial_variables={"format_instructions": self.parser.get_format_instructions()}
            )

            # Create the chain: prompt -> llm -> parser
            chain = prompt_template | self.llm | self.parser
            
            # Generate structured response
            try:
                structured_response = chain.invoke({
                    "context": context,
                    "question": question
                })
                
                # Format sources for display
                sources_display = []
                for source in structured_response.sources:
                    pdf_name = source.get("pdf_name", "Unknown")
                    page = source.get("page", "Unknown")
                    sources_display.append(f"📄 {pdf_name} (Page {page})")
                
                sources_text = "\n".join(sources_display) if sources_display else "No sources provided"
                
                # Format follow-up questions
                follow_up_text = ""
                if structured_response.follow_up_questions and len(structured_response.follow_up_questions) > 0:
                    follow_up_text = f"\n\n❓ **Follow-up Questions:**\n" + "\n".join([f"• {q}" for q in structured_response.follow_up_questions])
                
                # Create formatted response
                final_answer = f"**Answer:** {structured_response.answer}\n\n**Confidence Score:** {structured_response.confidence_score}/10\n\n📚 **Sources:**\n{sources_text}{follow_up_text}"
                
                return {
                    "messages": [AIMessage(content=final_answer)],
                    "confidence_score": structured_response.confidence_score,
                    "follow_up_questions": structured_response.follow_up_questions,
                    "parsed_response": structured_response
                }
                
            except Exception as parse_error:
                # Fallback if JSON parsing fails
                fallback_response = self.llm.invoke(f"""
Based on the following context, answer the user's question:

CONTEXT: {context}
QUESTION: {question}

Provide a comprehensive answer based on the document content.
""")
                
                final_answer = f"{fallback_response.content}\n\n📚 **Sources:**\n{source_references}"
                
                return {
                    "messages": [AIMessage(content=final_answer)],
                    "confidence_score": 0,
                    "follow_up_questions": [],
                    "parsed_response": None
                }
            
        except Exception as e:
            return {"messages": [AIMessage(content=f"Error processing your question: {e}")]}


class RAGEditorAgent:
    """Agent for launching the AI Dynamic Editor with RAG Integration."""
    
    def __init__(self):
        # Dynamic path resolution for portability
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.project_root = os.path.dirname(self.base_dir)
        self.script_dir = os.path.join(self.project_root, "Mcp_client_word")
        self.launcher_script = "launch_rag_editor.py"
    
    def launch_rag_editor(self, state: MessagesState) -> Dict[str, Any]:
        """Launch the RAG-enhanced AI Dynamic Editor."""
        try:
            # Get the last user message to check for document name
            user_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
            document_name = "proposal_20250927_142039.docx"  # Default document
            
            if user_messages:
                last_message = user_messages[-1].content.lower()
                # Look for document name in the message
                if ".docx" in last_message:
                    import re
                    doc_match = re.search(r'(\w+\.docx)', last_message)
                    if doc_match:
                        document_name = doc_match.group(1)
            
            # Check if launcher script exists
            launcher_path = os.path.join(self.script_dir, self.launcher_script)
            if not os.path.exists(launcher_path):
                return {
                    "messages": [
                        AIMessage(
                            content=f"❌ RAG Editor launcher not found at: {launcher_path}\n"
                                   f"Please ensure the Mcp_client_word directory is present in the project root."
                        )
                    ]
                }
            
            # Prepare the launch command
            launch_cmd = [sys.executable, launcher_path]
            
            # Set up environment with dynamic paths
            env = os.environ.copy()
            src_dir = os.path.join(self.base_dir, "src")
            pythonpath = src_dir
            if 'PYTHONPATH' in env:
                pythonpath = f"{src_dir}:{env['PYTHONPATH']}"
            env['PYTHONPATH'] = pythonpath
            
            # Launch the editor
            print(f"🚀 Launching AI Dynamic Editor with RAG Integration")
            print(f"📁 Script directory: {self.script_dir}")
            print(f"📄 Document: {document_name}")
            print(f"🐍 PYTHONPATH: {pythonpath}")
            print("=" * 60)
            
            # Start the process
            process = subprocess.Popen(
                launch_cmd,
                cwd=self.script_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait a moment to see if it starts successfully
            import time
            time.sleep(2)
            
            if process.poll() is None:
                # Process is still running
                return {
                    "messages": [
                        AIMessage(
                            content=f"✅ Successfully launched AI Dynamic Editor with RAG Integration!\n"
                                   f"📄 Working with document: {document_name}\n"
                                   f"🔧 RAG databases are ready for enhanced document editing\n"
                                   f"💡 The editor is now running in a separate process\n\n"
                                   f"**Features available:**\n"
                                   f"- AI-powered document editing with RAG context\n"
                                   f"- Template and example database integration\n"
                                   f"- Interactive editing with AI assistance\n"
                                   f"- Real-time proposal enhancement\n\n"
                                   f"Check the terminal where the editor was launched for interactive commands."
                        )
                    ]
                }
            else:
                # Process exited, get error output
                stdout, stderr = process.communicate()
                error_msg = stderr if stderr else stdout
                return {
                    "messages": [
                        AIMessage(
                            content=f"❌ Failed to launch RAG Editor: {error_msg}\n"
                                   f"Please check the dependencies and try again."
                        )
                    ]
                }
                
        except Exception as e:
            return {
                "messages": [
                    AIMessage(
                        content=f"❌ Error launching RAG Editor: {e}\n"
                               f"Make sure all dependencies are installed and paths are correct."
                    )
                ]
            }

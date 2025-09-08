"""
LangGraph RAG Agent

A retrieval-augmented generation (RAG) agent built with LangGraph that combines
document retrieval with language model generation to answer questions.
"""

import os
from typing import Dict, List, Optional, Any
from typing_extensions import TypedDict

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_milvus import Milvus

from langgraph.graph import StateGraph, START, END


class State(TypedDict):
    """State schema for the RAG agent."""
    question: str
    context: List[Document]
    answer: str
    sources: List[Dict[str, Any]]
    error: Optional[str]


class RAGAgent:
    """RAG Agent implementation using LangGraph."""
    
    def __init__(self):
        """Initialize the RAG agent with necessary components."""
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
        self.llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.max_docs = int(os.getenv("MAX_DOCS_RETRIEVE", "4"))
        self.vector_store = None
        self.embeddings = None
        self.llm = None
        self.milvus_uri = os.getenv("MILVUS_DB_PATH")
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant that answers questions based on the provided context. "
                      "If the context doesn't contain relevant information, say so clearly."),
            ("human", "Context:\n{context}\n\nQuestion: {question}")
        ])
    
    def _initialize_components(self):
        """Lazy initialization of components that require API keys."""
        if self.embeddings is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "OPENAI_API_KEY environment variable is required. "
                    "Please set it in your .env file or environment."
                )
            
            self.embeddings = OpenAIEmbeddings(
                model=self.embedding_model,
                api_key=api_key
            )
        
        if self.vector_store is None:
            self.vector_store = Milvus(
                embedding_function=self.embeddings,
                connection_args={"uri": self.milvus_uri},
                index_params={"index_type": "FLAT", "metric_type": "L2"},
            )
        
        if self.llm is None:
            api_key = os.getenv("OPENAI_API_KEY")
            self.llm = ChatOpenAI(
                model=self.llm_model,
                temperature=0,
                api_key=api_key
            )
    
    def retrieve(self, state: State) -> Dict[str, Any]:
        """
        Retrieve relevant documents based on the question.
        
        Args:
            state: Current state containing the question
            
        Returns:
            Updated state with retrieved context documents
        """
        try:
            self._initialize_components()
            
            question = state.get("question", "")
            if not question.strip():
                return {"error": "Question cannot be empty"}
            
            retrieved_docs = self.vector_store.similarity_search(
                question, 
                k=self.max_docs
            )
            sources = []
            for doc in retrieved_docs:
                source_info = {
                    "file": doc.metadata.get('source', 'Unknown').split('/')[-1],
                    "page": doc.metadata.get('page_label', doc.metadata.get('page', 'Unknown')),
                    "author": doc.metadata.get('author', 'Unknown'),
                    "content_preview": doc.page_content[:100] + "..." if len(doc.page_content) > 100 else doc.page_content
                }
                sources.append(source_info)
            return {"context": retrieved_docs, "sources": sources, "error": None}
        except Exception as e:
            return {"error": f"Error during retrieval: {str(e)}"}
    
    def generate(self, state: State) -> Dict[str, Any]:
        """
        Generate an answer based on the retrieved context and question.
        
        Args:
            state: Current state containing question and context
        Returns:
            Updated state with generated answer
        """
        try:
            self._initialize_components()
            
            if state.get("error"):
                return {"answer": f"Cannot generate answer due to error: {state['error']}"}
            
            question = state.get("question", "")
            context_docs = state.get("context", [])
            
            if not context_docs:
                return {"answer": "No relevant context found to answer the question."}
            
            context_with_sources = []
            for i, doc in enumerate(context_docs):
                source_file = doc.metadata.get('source', 'Unknown').split('/')[-1]
                page_num = doc.metadata.get('page_label', doc.metadata.get('page', 'Unknown'))
                content_with_source = f"[Source: {source_file}, Page {page_num}]\nDocument {i+1}: {doc.page_content}"
                context_with_sources.append(content_with_source)
            context_text = "\n\n".join(context_with_sources)
            messages = self.prompt.invoke({
                "question": question,
                "context": context_text
            })
            
            response = self.llm.invoke(messages)
            sources_info = state.get("sources", [])
            sources_text = "\n\n--- Sources ---\n"
            for i, source in enumerate(sources_info):
                sources_text += f"Source {i+1}: {source['file']}, Page {source['page']}\n"
            
            final_answer = response.content + sources_text
            return {"answer": final_answer, "error": None}
            
        except Exception as e:
            return {"answer": f"Error generating response: {str(e)}", "error": str(e)}
    
    def should_continue(self, state: State) -> str:
        """
        Determine whether to continue processing or end.
        
        Args:
            state: Current state
            
        Returns:
            Next node to execute or END
        """
        if state.get("error"):
            return END
        return "generate"
    
    def create_graph(self) -> StateGraph:
        """
        Create and compile the LangGraph workflow.
        
        Returns:
            Compiled StateGraph
        """
        workflow = StateGraph(State)
        
        workflow.add_node("retrieve", self.retrieve)
        workflow.add_node("generate", self.generate)
        
        workflow.add_edge(START, "retrieve")
        workflow.add_conditional_edges(
            "retrieve",
            self.should_continue,
            {
                "generate": "generate",
                END: END
            }
        )
        workflow.add_edge("generate", END)
        
        return workflow.compile()


rag_agent = RAGAgent()
graph = rag_agent.create_graph()
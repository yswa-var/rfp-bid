#!/usr/bin/env python3
"""
Chunk Summarizer and Updater for RAG Quality Improvement
Provides iterative improvement of document chunks during the session.
"""

import os
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_milvus import Milvus
from dotenv import load_dotenv

# Load environment
load_dotenv()

logger = logging.getLogger(__name__)

@dataclass
class ChunkSummary:
    """Summary information for a document chunk."""
    chunk_id: str
    original_content: str
    summary: str
    key_topics: List[str]
    quality_score: float
    last_updated: datetime
    metadata: Dict[str, Any]

@dataclass
class UpdateResult:
    """Result from chunk update operation."""
    success: bool
    chunks_processed: int
    chunks_updated: int
    summaries_created: int
    error: Optional[str] = None
    processing_time: float = 0.0

class ChunkSummarizer:
    """
    Handles summarization and quality improvement of document chunks.
    Provides callable methods for iterative improvement during sessions.
    """
    
    def __init__(self, vector_store: Optional[Milvus] = None):
        self.vector_store = vector_store
        self.llm = None
        self._initialize_llm()
        
        # Prompt for chunk summarization
        self.summary_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert document analyzer. Your task is to:
1. Create a concise summary of the document chunk
2. Extract key topics and concepts
3. Assess the quality and relevance of the content
4. Suggest improvements if needed

Provide a JSON response with:
- summary: A 2-3 sentence summary
- key_topics: List of main topics (max 5)
- quality_score: Score from 0-1 (1 = highest quality)
- relevance: How relevant this chunk is for RFP/business documents
- suggested_improvements: Any suggestions for better chunking"""),
            ("human", """Document Chunk to Analyze:
Source: {source}
Page: {page}
Content: {content}

Please analyze this chunk and provide the requested JSON response.""")
        ])
        
        # Prompt for chunk improvement
        self.improvement_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a document processing expert. Improve the given text chunk by:
1. Fixing formatting issues
2. Clarifying unclear references
3. Adding context where needed
4. Ensuring coherent structure
5. Maintaining all important information

Return only the improved text, no explanation."""),
            ("human", """Original chunk to improve:
{content}

Context from document:
Source: {source}
Page: {page}
Adjacent content: {context}

Provide the improved version:""")
        ])
    
    def _initialize_llm(self):
        """Initialize the language model."""
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment")
            
            self.llm = ChatOpenAI(
                model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
                temperature=0,
                api_key=api_key
            )
            logger.info("LLM initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            raise
    
    async def summarize_chunks(self, documents: List[Document]) -> List[ChunkSummary]:
        """
        Create summaries for a list of document chunks.
        """
        summaries = []
        
        logger.info(f"Starting summarization for {len(documents)} chunks")
        
        for i, doc in enumerate(documents):
            try:
                # Prepare inputs for summarization
                content = doc.page_content
                metadata = doc.metadata
                
                # Generate summary using LLM
                messages = self.summary_prompt.invoke({
                    "content": content,
                    "source": metadata.get("source", "Unknown"),
                    "page": metadata.get("page", "Unknown")
                })
                
                response = self.llm.invoke(messages)
                
                # Parse the response (assuming JSON format)
                try:
                    import json
                    analysis = json.loads(response.content)
                except:
                    # Fallback if JSON parsing fails
                    analysis = {
                        "summary": response.content[:200] + "...",
                        "key_topics": ["general"],
                        "quality_score": 0.7,
                        "relevance": "medium",
                        "suggested_improvements": "None"
                    }
                
                # Create chunk summary
                chunk_summary = ChunkSummary(
                    chunk_id=metadata.get("chunk_id", f"chunk_{i}"),
                    original_content=content,
                    summary=analysis.get("summary", ""),
                    key_topics=analysis.get("key_topics", []),
                    quality_score=analysis.get("quality_score", 0.5),
                    last_updated=datetime.now(),
                    metadata={
                        **metadata,
                        "analysis": analysis
                    }
                )
                
                summaries.append(chunk_summary)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Processed {i + 1}/{len(documents)} chunks")
                    
            except Exception as e:
                logger.error(f"Failed to summarize chunk {i}: {e}")
                continue
        
        logger.info(f"Summarization complete: {len(summaries)} summaries created")
        return summaries
    
    async def improve_chunk_quality(self, 
                                   chunk: Document, 
                                   context_chunks: List[Document] = None) -> Document:
        """
        Improve the quality of a single chunk using LLM.
        """
        try:
            # Prepare context from adjacent chunks
            context = ""
            if context_chunks:
                context = "\n".join([doc.page_content[:200] for doc in context_chunks])
            
            # Generate improved version
            messages = self.improvement_prompt.invoke({
                "content": chunk.page_content,
                "source": chunk.metadata.get("source", "Unknown"),
                "page": chunk.metadata.get("page", "Unknown"),
                "context": context
            })
            
            response = self.llm.invoke(messages)
            improved_content = response.content.strip()
            
            # Create improved document
            improved_metadata = chunk.metadata.copy()
            improved_metadata.update({
                "improved": True,
                "improvement_timestamp": datetime.now().isoformat(),
                "original_length": len(chunk.page_content),
                "improved_length": len(improved_content)
            })
            
            return Document(
                page_content=improved_content,
                metadata=improved_metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to improve chunk: {e}")
            return chunk  # Return original if improvement fails
    
    async def update_session_rag(self, 
                                documents: List[Document],
                                vector_store: Optional[Milvus] = None) -> UpdateResult:
        """
        Update the session RAG with improved chunks and summaries.
        This is the main callable for iterative improvement.
        """
        import time
        start_time = time.time()
        
        try:
            # Use provided vector store or default
            store = vector_store or self.vector_store
            if not store:
                raise ValueError("No vector store available")
            
            logger.info(f"Starting RAG update for {len(documents)} documents")
            
            # Step 1: Create summaries
            summaries = await self.summarize_chunks(documents)
            
            # Step 2: Identify low-quality chunks for improvement
            low_quality_chunks = []
            for i, summary in enumerate(summaries):
                if summary.quality_score < 0.6:  # Threshold for improvement
                    low_quality_chunks.append((i, documents[i]))
            
            logger.info(f"Identified {len(low_quality_chunks)} chunks for improvement")
            
            # Step 3: Improve low-quality chunks
            improved_documents = documents.copy()
            chunks_updated = 0
            
            for i, (doc_index, doc) in enumerate(low_quality_chunks):
                try:
                    # Get context chunks (adjacent chunks)
                    context_start = max(0, doc_index - 2)
                    context_end = min(len(documents), doc_index + 3)
                    context_chunks = documents[context_start:context_end]
                    
                    # Improve the chunk
                    improved_doc = await self.improve_chunk_quality(doc, context_chunks)
                    improved_documents[doc_index] = improved_doc
                    chunks_updated += 1
                    
                    logger.info(f"Improved chunk {doc_index} ({i+1}/{len(low_quality_chunks)})")
                    
                except Exception as e:
                    logger.error(f"Failed to improve chunk {doc_index}: {e}")
                    continue
            
            # Step 4: Update vector store with improved documents
            try:
                # Remove old documents if they exist
                # (This would need vector store-specific implementation)
                
                # Add improved documents
                document_ids = store.add_documents(improved_documents)
                logger.info(f"Added {len(document_ids)} improved documents to vector store")
                
            except Exception as e:
                logger.error(f"Failed to update vector store: {e}")
                raise
            
            processing_time = time.time() - start_time
            
            result = UpdateResult(
                success=True,
                chunks_processed=len(documents),
                chunks_updated=chunks_updated,
                summaries_created=len(summaries),
                processing_time=processing_time
            )
            
            logger.info(f"RAG update completed successfully in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            error_msg = f"Failed to update session RAG: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            return UpdateResult(
                success=False,
                chunks_processed=len(documents),
                chunks_updated=0,
                summaries_created=0,
                error=error_msg,
                processing_time=time.time() - start_time
            )
    
    def get_quality_metrics(self, summaries: List[ChunkSummary]) -> Dict[str, Any]:
        """
        Calculate quality metrics for the chunk summaries.
        """
        if not summaries:
            return {"error": "No summaries provided"}
        
        quality_scores = [s.quality_score for s in summaries]
        
        metrics = {
            "total_chunks": len(summaries),
            "average_quality": sum(quality_scores) / len(quality_scores),
            "min_quality": min(quality_scores),
            "max_quality": max(quality_scores),
            "low_quality_count": len([s for s in quality_scores if s < 0.6]),
            "high_quality_count": len([s for s in quality_scores if s > 0.8]),
            "topics_distribution": self._get_topic_distribution(summaries)
        }
        
        return metrics
    
    def _get_topic_distribution(self, summaries: List[ChunkSummary]) -> Dict[str, int]:
        """Get distribution of topics across chunks."""
        topic_counts = {}
        
        for summary in summaries:
            for topic in summary.key_topics:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        # Sort by frequency
        return dict(sorted(topic_counts.items(), key=lambda x: x[1], reverse=True))

# Utility functions for easy calling
async def update_and_summarize_chunks(documents: List[Document], 
                                    vector_store: Optional[Milvus] = None) -> UpdateResult:
    """
    Convenience function for updating and summarizing chunks.
    This is the main callable mentioned in Arun's requirements.
    """
    summarizer = ChunkSummarizer(vector_store)
    return await summarizer.update_session_rag(documents, vector_store)

def create_quality_report(summaries: List[ChunkSummary]) -> str:
    """
    Create a human-readable quality report.
    """
    summarizer = ChunkSummarizer()
    metrics = summarizer.get_quality_metrics(summaries)
    
    report = f"""
📊 RAG Quality Report
====================
Total Chunks: {metrics['total_chunks']}
Average Quality: {metrics['average_quality']:.2f}
Quality Range: {metrics['min_quality']:.2f} - {metrics['max_quality']:.2f}

Low Quality Chunks: {metrics['low_quality_count']} (< 0.6)
High Quality Chunks: {metrics['high_quality_count']} (> 0.8)

Top Topics:
{chr(10).join([f"  - {topic}: {count}" for topic, count in list(metrics['topics_distribution'].items())[:5]])}
"""
    
    return report

# Example usage
async def main():
    """Test the chunk summarizer."""
    from src.agent.fetch_agent import FetchAgent
    
    # Test with sample documents
    sample_docs = [
        Document(
            page_content="This is a sample RFP document about green energy projects...",
            metadata={"source": "test.pdf", "page": 1, "chunk_id": "test_1"}
        )
    ]
    
    # Test summarization
    summarizer = ChunkSummarizer()
    summaries = await summarizer.summarize_chunks(sample_docs)
    
    print("📋 Summaries created:")
    for summary in summaries:
        print(f"  - {summary.chunk_id}: {summary.summary}")
        print(f"    Topics: {summary.key_topics}")
        print(f"    Quality: {summary.quality_score}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

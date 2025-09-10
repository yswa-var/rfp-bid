
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv
from src.agent.graph import graph
import uvicorn

# Load environment variables
load_dotenv()

app = FastAPI(
    title="RFP RAG Agent API",
    description="A Retrieval-Augmented Generation agent for document querying",
    version="1.0.0"
)

class QueryRequest(BaseModel):
    question: str
    max_docs: Optional[int] = 4

class Source(BaseModel):
    file: str
    page: str
    author: str
    content_preview: str

class QueryResponse(BaseModel):
    answer: str
    sources: List[Source]
    error: Optional[str] = None

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "RFP RAG Agent API",
        "version": "1.0.0",
        "endpoints": {
            "query": "/query",
            "health": "/health",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    api_key_status = "configured" if os.getenv("OPENAI_API_KEY") else "missing"
    db_path = os.getenv("MILVUS_DB_PATH", "./milvus_example.db")
    db_exists = os.path.exists(db_path)
    
    return {
        "status": "healthy" if api_key_status == "configured" and db_exists else "unhealthy",
        "openai_api_key": api_key_status,
        "database_exists": db_exists,
        "database_path": db_path
    }

@app.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Query documents using the RAG agent."""
    try:
        # Validate input
        if not request.question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty")
        
        # Check if API key is configured
        if not os.getenv("OPENAI_API_KEY"):
            raise HTTPException(
                status_code=500, 
                detail="OpenAI API key not configured"
            )
        
        # Process the question
        result = graph.invoke({"question": request.question})
        
        # Handle errors
        if result.get("error"):
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Format response
        sources = []
        for source_data in result.get("sources", []):
            sources.append(Source(
                file=source_data.get("file", "Unknown"),
                page=source_data.get("page", "Unknown"),
                author=source_data.get("author", "Unknown"),
                content_preview=source_data.get("content_preview", "")
            ))
        
        return QueryResponse(
            answer=result.get("answer", "No answer generated"),
            sources=sources,
            error=None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/examples")
async def get_examples():
    """Get example questions."""
    return {
        "examples": [
            "What are the estimates for green hydrogen production cost according to KPMG?",
            "What are the benefits of the National Green Hydrogen Mission?",
            "What are the policy recommendations for green hydrogen?",
            "Who are the key stakeholders in green hydrogen development?",
            "What are the challenges in green hydrogen production?"
        ]
    }

if __name__ == "__main__":
    # Check environment setup
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not found in environment variables")
        print("Please add your OpenAI API key to the .env file")
        exit(1)
    
    print("🚀 Starting RFP RAG Agent API server...")
    print("📚 API Documentation: http://127.0.0.1:8000/docs")
    print("🔍 Interactive docs: http://127.0.0.1:8000/redoc")
    
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)

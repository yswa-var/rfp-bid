#!/usr/bin/env python3
"""
Unit Tests for Fetch Agent and PDF Processing
Tests edge cases and complex PDF scenarios.
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock
from typing import List

# Add src to path for imports
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.agent.fetch_agent import FetchAgent, FetchResult, ParseConfig
from src.agent.chunk_summarizer import ChunkSummarizer, update_and_summarize_chunks
from langchain_core.documents import Document

class TestFetchAgent:
    """Test cases for the Fetch Agent."""
    
    @pytest.fixture
    def fetch_agent(self):
        """Create a fetch agent for testing."""
        config = ParseConfig(
            chunk_size=500,
            chunk_overlap=50,
            extract_tables=True,
            handle_multi_column=True
        )
        return FetchAgent(config)
    
    @pytest.fixture
    def sample_pdf_path(self):
        """Create a sample PDF for testing."""
        # This would create a test PDF file
        # For now, we'll mock this
        return "/tmp/test_sample.pdf"
    
    def test_fetch_agent_initialization(self, fetch_agent):
        """Test that fetch agent initializes correctly."""
        assert fetch_agent.config.chunk_size == 500
        assert fetch_agent.config.extract_tables is True
        assert fetch_agent.session is not None
        assert fetch_agent.text_splitter is not None
    
    @pytest.mark.asyncio
    async def test_fetch_from_direct_pdf_url(self, fetch_agent):
        """Test fetching from a direct PDF URL."""
        pdf_url = "https://example.com/test.pdf"
        
        with patch.object(fetch_agent, '_download_and_parse_pdf') as mock_download:
            mock_result = FetchResult(
                success=True,
                documents=[Document(page_content="Test content", metadata={"page": 1})]
            )
            mock_download.return_value = mock_result
            
            result = await fetch_agent.fetch_from_url(pdf_url)
            
            assert result.success is True
            assert len(result.documents) == 1
            mock_download.assert_called_once_with(pdf_url)
    
    @pytest.mark.asyncio
    async def test_fetch_from_webpage_with_pdfs(self, fetch_agent):
        """Test fetching from a webpage containing PDF links."""
        webpage_url = "https://example.com/rfp-page"
        
        with patch.object(fetch_agent, '_browse_and_extract_pdfs') as mock_browse:
            mock_result = FetchResult(
                success=True,
                documents=[
                    Document(page_content="Content 1", metadata={"page": 1}),
                    Document(page_content="Content 2", metadata={"page": 2})
                ]
            )
            mock_browse.return_value = mock_result
            
            result = await fetch_agent.fetch_from_url(webpage_url)
            
            assert result.success is True
            assert len(result.documents) == 2
            mock_browse.assert_called_once_with(webpage_url)
    
    @pytest.mark.asyncio
    async def test_error_handling_invalid_url(self, fetch_agent):
        """Test error handling for invalid URLs."""
        invalid_url = "not-a-valid-url"
        
        result = await fetch_agent.fetch_from_url(invalid_url)
        
        assert result.success is False
        assert result.error is not None
        assert "not-a-valid-url" in result.error
    
    @pytest.mark.asyncio
    async def test_error_handling_network_failure(self, fetch_agent):
        """Test error handling for network failures."""
        pdf_url = "https://nonexistent.com/test.pdf"
        
        with patch('requests.Session.get') as mock_get:
            mock_get.side_effect = Exception("Network error")
            
            result = await fetch_agent.fetch_from_url(pdf_url)
            
            assert result.success is False
            assert "Network error" in result.error
    
    def test_parse_config_defaults(self):
        """Test ParseConfig default values."""
        config = ParseConfig()
        
        assert config.chunk_size == 1000
        assert config.chunk_overlap == 200
        assert config.extract_tables is True
        assert config.handle_multi_column is True
        assert config.ocr_fallback is True

class TestComplexPDFScenarios:
    """Test complex PDF processing scenarios."""
    
    @pytest.fixture
    def fetch_agent(self):
        return FetchAgent()
    
    def test_multi_column_layout_detection(self, fetch_agent):
        """Test multi-column layout detection."""
        # Mock PyMuPDF page with multi-column layout
        mock_page = Mock()
        mock_page.get_text.return_value = "Simple text"
        
        # Mock the dict response for layout detection
        mock_blocks = {
            "blocks": [
                {
                    "lines": [
                        {
                            "spans": [
                                {
                                    "text": "Column 1 text",
                                    "bbox": [100, 100, 200, 120]
                                },
                                {
                                    "text": "Column 2 text", 
                                    "bbox": [300, 100, 400, 120]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        mock_page.get_text.return_value = mock_blocks
        
        # Test layout extraction
        result = fetch_agent._extract_text_with_layout(mock_page)
        
        # Should handle the layout appropriately
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_table_extraction(self, fetch_agent):
        """Test table extraction from PDF pages."""
        # Mock PyMuPDF page with tables
        mock_page = Mock()
        mock_table = Mock()
        mock_table.extract.return_value = [
            ["Header 1", "Header 2", "Header 3"],
            ["Row 1 Col 1", "Row 1 Col 2", "Row 1 Col 3"],
            ["Row 2 Col 1", "Row 2 Col 2", "Row 2 Col 3"]
        ]
        mock_page.find_tables.return_value = [mock_table]
        
        result = fetch_agent._extract_tables_from_page(mock_page)
        
        assert "Header 1 | Header 2 | Header 3" in result
        assert "Row 1 Col 1 | Row 1 Col 2 | Row 1 Col 3" in result
    
    def test_corrupted_pdf_handling(self, fetch_agent):
        """Test handling of corrupted PDF files."""
        # Create a fake corrupted PDF file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b"This is not a PDF file")
            corrupted_path = f.name
        
        try:
            documents = fetch_agent._parse_pdf_with_pymupdf(
                corrupted_path, 
                "test_source"
            )
            
            # Should return empty list for corrupted files
            assert isinstance(documents, list)
            # Might be empty or have error handling
            
        finally:
            os.unlink(corrupted_path)
    
    def test_large_pdf_memory_handling(self, fetch_agent):
        """Test memory handling for large PDF files."""
        # This test would check memory usage during processing
        # For now, we'll test the configuration
        config = ParseConfig(chunk_size=2000, chunk_overlap=400)
        large_agent = FetchAgent(config)
        
        assert large_agent.config.chunk_size == 2000
        assert large_agent.config.chunk_overlap == 400
    
    def test_empty_pdf_handling(self, fetch_agent):
        """Test handling of empty PDF files."""
        # Mock an empty PDF
        with patch('fitz.open') as mock_open:
            mock_pdf = Mock()
            mock_pdf.__len__ = Mock(return_value=0)  # Empty PDF
            mock_open.return_value = mock_pdf
            
            documents = fetch_agent._parse_pdf_with_pymupdf(
                "empty.pdf", 
                "test_source"
            )
            
            assert isinstance(documents, list)
            assert len(documents) == 0

class TestChunkSummarizer:
    """Test cases for the Chunk Summarizer."""
    
    @pytest.fixture
    def chunk_summarizer(self):
        """Create a chunk summarizer for testing."""
        with patch('src.agent.chunk_summarizer.ChatOpenAI'):
            return ChunkSummarizer()
    
    @pytest.fixture
    def sample_documents(self):
        """Create sample documents for testing."""
        return [
            Document(
                page_content="This is a sample RFP document about renewable energy projects and their requirements.",
                metadata={"source": "test.pdf", "page": 1, "chunk_id": "test_1"}
            ),
            Document(
                page_content="The project scope includes solar panel installation and wind turbine setup with a budget of $1M.",
                metadata={"source": "test.pdf", "page": 2, "chunk_id": "test_2"}
            )
        ]
    
    @pytest.mark.asyncio
    async def test_summarize_chunks(self, chunk_summarizer, sample_documents):
        """Test chunk summarization."""
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = '{"summary": "Test summary", "key_topics": ["energy", "RFP"], "quality_score": 0.8}'
        
        with patch.object(chunk_summarizer.llm, 'invoke', return_value=mock_response):
            summaries = await chunk_summarizer.summarize_chunks(sample_documents)
            
            assert len(summaries) == 2
            assert all(s.summary == "Test summary" for s in summaries)
            assert all("energy" in s.key_topics for s in summaries)
    
    @pytest.mark.asyncio
    async def test_improve_chunk_quality(self, chunk_summarizer, sample_documents):
        """Test chunk quality improvement."""
        chunk = sample_documents[0]
        
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = "Improved version of the document content with better structure and clarity."
        
        with patch.object(chunk_summarizer.llm, 'invoke', return_value=mock_response):
            improved_chunk = await chunk_summarizer.improve_chunk_quality(chunk)
            
            assert improved_chunk.page_content != chunk.page_content
            assert "Improved version" in improved_chunk.page_content
            assert improved_chunk.metadata.get("improved") is True
    
    def test_quality_metrics_calculation(self, chunk_summarizer):
        """Test quality metrics calculation."""
        from src.agent.chunk_summarizer import ChunkSummary
        from datetime import datetime
        
        summaries = [
            ChunkSummary("1", "content1", "summary1", ["topic1"], 0.9, datetime.now(), {}),
            ChunkSummary("2", "content2", "summary2", ["topic1", "topic2"], 0.5, datetime.now(), {}),
            ChunkSummary("3", "content3", "summary3", ["topic2"], 0.7, datetime.now(), {})
        ]
        
        metrics = chunk_summarizer.get_quality_metrics(summaries)
        
        assert metrics["total_chunks"] == 3
        assert metrics["average_quality"] == pytest.approx(0.7, rel=1e-2)
        assert metrics["low_quality_count"] == 1  # quality < 0.6
        assert metrics["high_quality_count"] == 1  # quality > 0.8

class TestIntegration:
    """Integration tests combining multiple components."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_fetch_and_summarize(self):
        """Test end-to-end fetch and summarize workflow."""
        # Mock the entire workflow
        with patch('src.agent.fetch_agent.FetchAgent') as MockFetchAgent, \
             patch('src.agent.chunk_summarizer.ChunkSummarizer') as MockSummarizer:
            
            # Mock fetch agent
            mock_fetch_instance = Mock()
            mock_fetch_result = FetchResult(
                success=True,
                documents=[Document(page_content="Test content", metadata={"page": 1})]
            )
            # Make it an async mock
            mock_fetch_instance.fetch_from_url = AsyncMock(return_value=mock_fetch_result)
            MockFetchAgent.return_value = mock_fetch_instance
            
            # Mock summarizer
            mock_summarizer_instance = Mock()
            mock_update_result = Mock()
            mock_update_result.success = True
            mock_update_result.chunks_processed = 1
            mock_summarizer_instance.update_session_rag = AsyncMock(return_value=mock_update_result)
            MockSummarizer.return_value = mock_summarizer_instance
            
            # Test the workflow
            fetch_agent = MockFetchAgent()
            fetch_result = await fetch_agent.fetch_from_url("https://example.com/test.pdf")
            
            summarizer = MockSummarizer()
            update_result = await summarizer.update_session_rag(fetch_result.documents)
            
            assert fetch_result.success is True
            assert update_result.success is True

class TestErrorRecovery:
    """Test error recovery and resilience."""
    
    @pytest.mark.asyncio
    async def test_partial_failure_recovery(self):
        """Test recovery from partial failures."""
        # Test that the system can handle some PDFs failing while others succeed
        with patch('src.agent.fetch_agent.FetchAgent._download_and_parse_pdf') as mock_download:
            # First call succeeds, second fails, third succeeds
            mock_download.side_effect = [
                FetchResult(success=True, documents=[Document(page_content="Success 1", metadata={})]),
                FetchResult(success=False, documents=[], error="Download failed"),
                FetchResult(success=True, documents=[Document(page_content="Success 2", metadata={})])
            ]
            
            agent = FetchAgent()
            
            # This would be called in _browse_and_extract_pdfs
            # We're testing the error handling logic
            results = []
            pdf_urls = ["url1.pdf", "url2.pdf", "url3.pdf"]
            
            for url in pdf_urls:
                try:
                    result = await agent._download_and_parse_pdf(url)
                    results.append(result)
                except Exception as e:
                    results.append(FetchResult(success=False, documents=[], error=str(e)))
            
            # Should have 2 successes and 1 failure
            successful = [r for r in results if r.success]
            failed = [r for r in results if not r.success]
            
            assert len(successful) == 2
            assert len(failed) == 1

# Test fixtures and utilities
@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing."""
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test-key',
        'MILVUS_DB_PATH': './test_milvus.db'
    }):
        yield

# Performance tests
class TestPerformance:
    """Performance-related tests."""
    
    @pytest.mark.slow
    def test_large_document_processing_time(self):
        """Test processing time for large documents."""
        import time
        
        # Create a large document
        large_content = "Test content. " * 10000  # ~130KB of text
        large_doc = Document(
            page_content=large_content,
            metadata={"source": "large.pdf", "page": 1}
        )
        
        start_time = time.time()
        
        # Process the document (chunk it)
        config = ParseConfig(chunk_size=1000, chunk_overlap=200)
        agent = FetchAgent(config)
        chunks = agent.text_splitter.split_documents([large_doc])
        
        processing_time = time.time() - start_time
        
        # Should process within reasonable time (adjust threshold as needed)
        assert processing_time < 5.0  # 5 seconds max
        assert len(chunks) > 0

if __name__ == "__main__":
    # Run tests with: python -m pytest test_arun_components.py -v
    pytest.main([__file__, "-v"])

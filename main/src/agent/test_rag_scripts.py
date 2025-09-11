#!/usr/bin/env python3
"""
Test Script for RAG Systems

This script tests the basic functionality of both Template RAG and RFP RAG systems.

Usage:
    python test_rag_scripts.py
"""

import os
import sys
from pathlib import Path

# Add the current directory to the path to import the RAG modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from template_rag import TemplateRAG
from rfp_rag import RFPRAG


def test_template_rag():
    """Test Template RAG functionality."""
    print("🧪 Testing Template RAG...")
    
    try:
        # Initialize Template RAG
        template_rag = TemplateRAG("test_template_rag.db")
        print("✅ Template RAG initialized successfully")
        
        # Test database info (should show no database loaded)
        info = template_rag.get_database_info()
        print(f"📊 Database info: {info}")
        
        # Test query without data (should return empty list)
        results = template_rag.query_data("test query", k=3)
        print(f"🔍 Query results (no data): {len(results)} results")
        
        print("✅ Template RAG tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Template RAG test failed: {str(e)}")
        return False


def test_rfp_rag():
    """Test RFP RAG functionality."""
    print("\n🧪 Testing RFP RAG...")
    
    try:
        # Initialize RFP RAG
        rfp_rag = RFPRAG("test_rfp_rag.db")
        print("✅ RFP RAG initialized successfully")
        
        # Test database info (should show no database loaded)
        info = rfp_rag.get_database_info()
        print(f"📊 Database info: {info}")
        
        # Test query without data (should return empty list)
        results = rfp_rag.query_data("test query", k=3)
        print(f"🔍 Query results (no data): {len(results)} results")
        
        # Test RFP list (should return empty list)
        rfp_list = rfp_rag.get_rfp_list()
        print(f"📋 RFP list (no data): {len(rfp_list)} documents")
        
        print("✅ RFP RAG tests passed")
        return True
        
    except Exception as e:
        print(f"❌ RFP RAG test failed: {str(e)}")
        return False


def test_milvus_ops_import():
    """Test if milvus_ops can be imported."""
    print("\n🧪 Testing milvus_ops import...")
    
    try:
        from milvus_ops import MilvusOps
        print("✅ milvus_ops imported successfully")
        
        # Test MilvusOps initialization
        milvus_ops = MilvusOps("test_db.db")
        print("✅ MilvusOps initialized successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ milvus_ops import test failed: {str(e)}")
        return False


def cleanup_test_files():
    """Clean up test database files."""
    print("\n🧹 Cleaning up test files...")
    
    test_files = [
        "test_template_rag.db",
        "test_rfp_rag.db",
        "test_db.db"
    ]
    
    for file in test_files:
        if os.path.exists(file):
            try:
                os.remove(file)
                print(f"✅ Removed {file}")
            except Exception as e:
                print(f"⚠️ Could not remove {file}: {str(e)}")


def main():
    """Main test function."""
    print("🚀 RAG System Test Suite")
    print("=" * 50)
    
    # Run tests
    tests = [
        test_milvus_ops_import,
        test_template_rag,
        test_rfp_rag
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    # Clean up
    cleanup_test_files()
    
    # Results
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed! RAG systems are working correctly.")
        print("\nNext steps:")
        print("1. Add your PDF documents using the add_data commands")
        print("2. Query the databases using the query_data commands")
        print("3. Use interactive mode for real-time querying")
    else:
        print("❌ Some tests failed. Please check the error messages above.")
        print("\nTroubleshooting:")
        print("1. Make sure all dependencies are installed")
        print("2. Check that milvus_ops.py is in the same directory")
        print("3. Verify your Python environment is set up correctly")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

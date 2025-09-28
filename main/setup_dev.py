#!/usr/bin/env python3
"""
Development Setup Script for RFP-Bid LangGraph System
Sets up the environment for running with 'langgraph dev' command
"""

import os
import sys
import subprocess
from pathlib import Path

def setup_environment():
    """Set up the development environment for langgraph dev"""
    
    # Get the project root directory
    script_dir = Path(__file__).parent.absolute()
    project_root = script_dir.parent
    
    print("🚀 Setting up RFP-Bid LangGraph Development Environment")
    print(f"📁 Project root: {project_root}")
    print(f"📁 Main directory: {script_dir}")
    print("=" * 60)
    
    # Check if Mcp_client_word exists
    mcp_dir = project_root / "Mcp_client_word"
    if not mcp_dir.exists():
        print(f"❌ Mcp_client_word directory not found at: {mcp_dir}")
        print("Please ensure the Mcp_client_word directory is present in the project root.")
        return False
    
    print(f"✅ Found Mcp_client_word directory: {mcp_dir}")
    
    # Check if .env file exists
    env_file = script_dir / ".env"
    if not env_file.exists():
        print(f"⚠️  .env file not found at: {env_file}")
        print("Please create a .env file with your OpenAI API key:")
        print("OPENAI_API_KEY=your_api_key_here")
        print("LLM_MODEL=gpt-4o-mini")
        return False
    
    print(f"✅ Found .env file: {env_file}")
    
    # Check Python version
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    print(f"🐍 Python version: {python_version}")
    
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        return False
    
    # Check if requirements.txt exists
    requirements_file = script_dir / "requirements.txt"
    if not requirements_file.exists():
        print(f"❌ requirements.txt not found at: {requirements_file}")
        return False
    
    print(f"✅ Found requirements.txt: {requirements_file}")
    
    # Install dependencies
    print("\n📦 Installing dependencies...")
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
        ], check=True)
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False
    
    # Install langgraph-cli
    print("\n📦 Installing LangGraph CLI...")
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "langgraph-cli[all]"
        ], check=True)
        print("✅ LangGraph CLI installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install LangGraph CLI: {e}")
        return False
    
    # Test import
    print("\n🧪 Testing imports...")
    try:
        from src.agent.graph import graph
        print("✅ Graph imported successfully")
        print(f"Available nodes: {list(graph.get_graph().nodes.keys())}")
    except Exception as e:
        print(f"❌ Failed to import graph: {e}")
        return False
    
    print("\n🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Run: langgraph dev")
    print("2. Open LangGraph Studio in your browser")
    print("3. Test the RAG editor agent with: 'launch rag editor'")
    
    return True

if __name__ == "__main__":
    success = setup_environment()
    sys.exit(0 if success else 1)

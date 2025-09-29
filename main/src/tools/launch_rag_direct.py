#!/usr/bin/env python3
"""
Direct RAG Editor Launcher for LangGraph Studio

This script provides a direct way to launch the RAG editor from within
LangGraph Studio or as a standalone command.
"""

import os
import sys
import subprocess
from pathlib import Path

def launch_rag_editor():
    """Launch the RAG editor with beautiful interface."""
    
    # Get the current script directory and navigate to MCP client
    current_dir = Path(__file__).resolve().parent
    mcp_client_dir = current_dir.parent.parent / "Mcp_client_word"
    launch_script = mcp_client_dir / "launch_rag_editor.py"
    
    print("🚀 **RAG Editor Launcher for LangGraph Studio**")
    print("=" * 60)
    print(f"📁 Current directory: {current_dir}")
    print(f"📁 MCP client directory: {mcp_client_dir}")
    print(f"🎯 Launch script: {launch_script}")
    
    # Check if the launch script exists
    if not launch_script.exists():
        print(f"❌ Launch script not found: {launch_script}")
        return False
    
    print("\n🔧 **Launching Interactive RAG Editor...**")
    print("This will provide the same beautiful interface you saw with:")
    print("• RAG database initialization")
    print("• Document analysis and metadata")
    print("• Interactive editing commands")
    print("• AI-powered content enhancement")
    print("• MCP server with 54 tools")
    
    try:
        # Change to the MCP client directory and launch
        os.chdir(mcp_client_dir)
        print(f"\n📂 Changed to directory: {mcp_client_dir}")
        
        # Launch the RAG editor
        print("\n🚀 Starting RAG Editor...")
        print("-" * 50)
        
        # Execute the launch script
        result = subprocess.run([
            sys.executable, "launch_rag_editor.py"
        ], cwd=mcp_client_dir)
        
        if result.returncode == 0:
            print("✅ RAG Editor session completed successfully!")
        else:
            print(f"⚠️ RAG Editor exited with code: {result.returncode}")
            
        return result.returncode == 0
        
    except KeyboardInterrupt:
        print("\n⏹️ RAG Editor launch interrupted by user")
        return False
    except Exception as e:
        print(f"❌ Failed to launch RAG Editor: {e}")
        return False

def main():
    """Main entry point."""
    print("🎯 RAG Editor Direct Launcher")
    print("=" * 40)
    
    success = launch_rag_editor()
    
    if success:
        print("\n✨ RAG Editor launch completed!")
    else:
        print("\n❌ RAG Editor launch failed!")
        
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
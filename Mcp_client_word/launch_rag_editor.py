#!/usr/bin/env python3
"""
Launcher for AI Dynamic Editor with RAG Integration
Sets up environment and launches the editor
"""

import os
import sys
import subprocess

def main():
    """Launch the AI Dynamic Editor with proper environment setup"""
    
    # Set up the environment
    script_dir = "/home/arun/Pictures/rfp-bid/Mcp_client_word"
    main_dir = "/home/arun/Pictures/rfp-bid/main"
    src_dir = "/home/arun/Pictures/rfp-bid/main/src"
    
    # Set PYTHONPATH
    pythonpath = src_dir
    if 'PYTHONPATH' in os.environ:
        pythonpath = f"{src_dir}:{os.environ['PYTHONPATH']}"
    
    # Create environment
    env = os.environ.copy()
    env['PYTHONPATH'] = pythonpath
    
    # Launch the editor
    editor_script = os.path.join(script_dir, "ai_dynamic_editor_with_rag.py")
    
    print("🚀 Launching AI Dynamic Editor with RAG Integration")
    print(f"📁 Script directory: {script_dir}")
    print(f"📁 RFP main directory: {main_dir}")  
    print(f"🐍 PYTHONPATH: {pythonpath}")
    print("=" * 60)
    
    try:
        # Launch the main script
        result = subprocess.run(
            [sys.executable, editor_script],
            cwd=script_dir,
            env=env
        )
        return result.returncode
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted by user")
        return 0
    except Exception as e:
        print(f"❌ Launch failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
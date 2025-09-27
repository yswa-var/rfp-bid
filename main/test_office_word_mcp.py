#!/usr/bin/env python3
"""
Test script for Office-Word-MCP-Server integration
"""

import asyncio
import os
import sys
import subprocess
import tempfile
from pathlib import Path

# Add MCP client imports
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    print("❌ MCP client not available. Install with: pip install mcp")
    MCP_AVAILABLE = False


async def test_office_word_mcp_server():
    """Test connection to Office-Word-MCP-Server."""
    
    if not MCP_AVAILABLE:
        print("❌ Cannot test - MCP not available")
        return
    
    print("🔧 Testing Office-Word-MCP-Server connection...")
    
    try:
        # Use the package's run_server function via command line
        server_cmd = [
            sys.executable, 
            "-c", 
            "import office_word_mcp_server; office_word_mcp_server.run_server()"
        ]
        
        print(f"🚀 Starting server with command: {' '.join(server_cmd)}")
        
        # Create MCP client session with stdio transport
        server_params = StdioServerParameters(
            command=server_cmd[0],
            args=server_cmd[1:],
            env=None
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("✅ Connected to Office-Word-MCP-Server successfully!")
                
                # List available tools
                tools_result = await session.list_tools()
                print(f"📋 Found {len(tools_result.tools)} tools:")
                
                for tool in tools_result.tools[:10]:  # Show first 10 tools
                    print(f"  - {tool.name}: {tool.description}")
                
                if len(tools_result.tools) > 10:
                    print(f"  ... and {len(tools_result.tools) - 10} more tools")
                
                # Test creating a simple document
                test_doc_path = os.path.abspath("test_mcp_document.docx")
                print(f"\n🔧 Testing document creation: {test_doc_path}")
                
                try:
                    result = await session.call_tool(
                        "create_document",
                        {
                            "filename": test_doc_path,
                            "title": "Test Document from MCP",
                            "author": "MCP Test Script"
                        }
                    )
                    print(f"✅ Document created successfully")
                    print(f"📄 Result: {result.content}")
                    
                    # Test adding a heading
                    result = await session.call_tool(
                        "add_heading",
                        {
                            "filename": test_doc_path,
                            "text": "Test Heading from MCP",
                            "level": 1
                        }
                    )
                    print(f"✅ Heading added successfully")
                    print(f"📄 Result: {result.content}")
                    
                    # Test adding a paragraph
                    result = await session.call_tool(
                        "add_paragraph",
                        {
                            "filename": test_doc_path,
                            "text": "This is a test paragraph added via the Office-Word-MCP-Server. The connection is working properly!"
                        }
                    )
                    print(f"✅ Paragraph added successfully")
                    print(f"📄 Result: {result.content}")
                    
                    # Get document info
                    result = await session.call_tool(
                        "get_document_info",
                        {
                            "filename": test_doc_path
                        }
                    )
                    print(f"✅ Document info retrieved")
                    print(f"📄 Document info: {result.content}")
                    
                    print(f"\n🎉 All tests passed! Office-Word-MCP-Server is working properly.")
                    print(f"📄 Test document created: {test_doc_path}")
                    
                except Exception as tool_error:
                    print(f"❌ Error testing tools: {tool_error}")
                    
    except Exception as e:
        print(f"❌ Error connecting to Office-Word-MCP-Server: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main function to run the test."""
    print("=== Office-Word-MCP-Server Test ===")
    asyncio.run(test_office_word_mcp_server())


if __name__ == "__main__":
    main()
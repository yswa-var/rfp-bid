#!/usr/bin/env python3
"""
Test command parsing for the RAG Editor Agent
"""

def test_command_parsing():
    """Test how commands are parsed by the system."""
    
    # Test commands
    test_commands = [
        "add context form rfp to 3. Understanding of Requirements 2",
        "add context from rfp to Understanding of Requirements 2",
        "add context from rfp to Understanding of Requirements",
        "add context from rfp to Executive Summary all",
        "load document.docx",
        "find some text"
    ]
    
    for command in test_commands:
        print(f"\n🔍 Testing command: '{command}'")
        
        # Parse command like the RAG editor does
        parts = command.split()
        print(f"   Split parts: {parts}")
        
        if parts:
            cmd = parts[0].lower()
            args = parts[1:] if len(parts) > 1 else []
            print(f"   Command: '{cmd}'")
            print(f"   Args: {args}")
            
            if cmd == "add":
                content = " ".join(args)
                print(f"   Add content: '{content}'")
                
                # Check for context-aware (handle typos like "form" instead of "from")
                if "context" in content.lower() and (("from rfp" in content.lower() or "form rfp" in content.lower()) or ("from rag" in content.lower() or "form rag" in content.lower())):
                    print(f"   ✅ Context-aware command detected")
                    
                    # Check for choice number at end
                    import re
                    choice_match = re.search(r"'(\d+)'$|(\d+)$", content.strip())
                    if choice_match:
                        choice = choice_match.group(1) or choice_match.group(2)
                        base_command = content[:choice_match.start()].strip()
                        print(f"   📍 Choice found: '{choice}'")
                        print(f"   📍 Base command: '{base_command}'")
                    else:
                        print(f"   ⚠️ No choice number found at end")
                else:
                    print(f"   ❌ Not context-aware command")
        else:
            print(f"   ❌ No parts found")

if __name__ == "__main__":
    test_command_parsing()
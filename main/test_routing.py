"""
Test script to verify the routing logic works correctly for independent agent access.

This script tests that:
1. docx_agent can be accessed independently
2. pdf_parser can be accessed independently  
3. general_assistant can be accessed independently
4. rfp_supervisor only triggers for actual RFP proposal generation
"""

import sys
from pathlib import Path

# Add src to path
_CURRENT_DIR = Path(__file__).resolve().parent
_SRC_DIR = _CURRENT_DIR / "src"
sys.path.insert(0, str(_SRC_DIR))

from agent.state import MessagesState
from agent.router import supervisor_router
from langchain_core.messages import HumanMessage


def test_routing(query: str, expected_route: str):
    """Test a single routing case."""
    state = MessagesState(
        messages=[HumanMessage(content=query)]
    )
    
    actual_route = supervisor_router(state)
    status = "✅ PASS" if actual_route == expected_route else "❌ FAIL"
    
    print(f"{status}: '{query}'")
    print(f"   Expected: {expected_route}")
    print(f"   Got: {actual_route}")
    print()
    
    return actual_route == expected_route


def main():
    """Run routing tests."""
    print("=" * 80)
    print("TESTING INDEPENDENT AGENT ROUTING")
    print("=" * 80)
    print()
    
    results = []
    
    # Test Priority 1: Explicit agent names
    print("--- Priority 1: Explicit Agent Names ---")
    results.append(test_routing(
        "docx_agent: update the title",
        "docx_agent"
    ))
    results.append(test_routing(
        "use pdf_parser to index files",
        "pdf_parser"
    ))
    results.append(test_routing(
        "general_assistant: what is the budget?",
        "general_assistant"
    ))
    results.append(test_routing(
        "rfp_supervisor: create proposal",
        "rfp_supervisor"
    ))
    
    # Test Priority 2: DOCX Operations (including the problematic case)
    print("--- Priority 2: DOCX Operations ---")
    results.append(test_routing(
        "update the docx_agent document title to rfp-olools-9903",
        "docx_agent"
    ))
    results.append(test_routing(
        "edit the Word document",
        "docx_agent"
    ))
    results.append(test_routing(
        "modify document section 2",
        "docx_agent"
    ))
    results.append(test_routing(
        "read the docx file named rfp-2024.docx",
        "docx_agent"
    ))
    results.append(test_routing(
        "create a new document",
        "docx_agent"
    ))
    results.append(test_routing(
        "update document title to anything",
        "docx_agent"
    ))
    
    # Test Priority 3: PDF Operations
    print("--- Priority 3: PDF Operations ---")
    results.append(test_routing(
        "parse PDF files from /path/to/pdfs",
        "pdf_parser"
    ))
    results.append(test_routing(
        "index pdf documents",
        "pdf_parser"
    ))
    results.append(test_routing(
        "extract from PDF",
        "pdf_parser"
    ))
    
    # Test Priority 4: RFP Proposal Generation (only when GENERATING proposals)
    print("--- Priority 4: RFP Proposal Generation ---")
    results.append(test_routing(
        "generate a new RFP proposal",
        "rfp_supervisor"
    ))
    results.append(test_routing(
        "create RFP proposal for cybersecurity services",
        "rfp_supervisor"
    ))
    results.append(test_routing(
        "draft a proposal",
        "rfp_supervisor"
    ))
    results.append(test_routing(
        "prepare an RFP response",
        "rfp_supervisor"
    ))
    results.append(test_routing(
        "I need finance team input for the proposal",
        "rfp_supervisor"
    ))
    
    # Test Priority 5: General Assistant
    print("--- Priority 5: General Questions ---")
    results.append(test_routing(
        "what is the budget mentioned in the documents?",
        "general_assistant"
    ))
    results.append(test_routing(
        "tell me about the security requirements",
        "general_assistant"
    ))
    results.append(test_routing(
        "summarize the contract terms",
        "general_assistant"
    ))
    
    # Edge cases - RFP in filename should NOT trigger rfp_supervisor
    print("--- Edge Cases: RFP in Filenames ---")
    results.append(test_routing(
        "open the file rfp-2024-001.docx",
        "docx_agent"
    ))
    results.append(test_routing(
        "edit rfp-report.docx",
        "docx_agent"
    ))
    results.append(test_routing(
        "update the rfp document title",
        "docx_agent"
    ))
    
    # Summary
    print("=" * 80)
    print(f"RESULTS: {sum(results)}/{len(results)} tests passed")
    print("=" * 80)
    
    if sum(results) == len(results):
        print("✅ All routing tests passed!")
        return 0
    else:
        print(f"❌ {len(results) - sum(results)} tests failed")
        return 1


if __name__ == "__main__":
    exit(main())


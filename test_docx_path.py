#!/usr/bin/env python3
"""
Simple test script to verify DOCX path resolution works correctly.
"""

import os
import sys
from pathlib import Path

# Add the main/src directory to the path
current_dir = Path(__file__).resolve().parent
main_dir = current_dir / "main"
src_dir = main_dir / "src"
rct_agent_dir = src_dir / "rct_agent"

if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

try:
    from rct_agent.docx_manager import get_docx_manager, reset_docx_manager

    def test_docx_path_resolution():
        """Test that the DOCX manager can resolve the path to master.docx correctly."""

        print("=" * 80)
        print("Testing DOCX Path Resolution")
        print("=" * 80)

        # Reset any existing manager
        reset_docx_manager()

        try:
            # Get the DOCX manager (should use default path resolution)
            manager = get_docx_manager()

            # Check if the document path exists
            docx_path = manager.docx_path
            print(f"Resolved DOCX path: {docx_path}")
            print(f"Path exists: {os.path.exists(docx_path)}")
            print(f"Is absolute path: {os.path.isabs(docx_path)}")

            if os.path.exists(docx_path):
                print("✅ SUCCESS: DOCX file found at resolved path!")

                # Try to read some basic info from the document
                try:
                    doc = manager.doc
                    paragraphs = len(doc.paragraphs)
                    print(f"Document has {paragraphs} paragraphs")

                    # Try to get headings
                    headings = []
                    for paragraph in doc.paragraphs:
                        if paragraph.style.name.startswith('Heading'):
                            headings.append(paragraph.text.strip())

                    print(f"Found {len(headings)} headings:")
                    for i, heading in enumerate(headings[:5], 1):  # Show first 5
                        print(f"  {i}. {heading}")

                    if len(headings) > 5:
                        print(f"  ... and {len(headings) - 5} more")

                    return True

                except Exception as e:
                    print(f"❌ Error reading document: {e}")
                    return False

            else:
                print("❌ FAILURE: DOCX file not found at resolved path")
                return False

        except Exception as e:
            print(f"❌ ERROR: {e}")
            return False

    if __name__ == "__main__":
        success = test_docx_path_resolution()
        print("\n" + "=" * 80)
        if success:
            print("🎉 DOCX Path Resolution Test PASSED")
        else:
            print("💥 DOCX Path Resolution Test FAILED")
        print("=" * 80)
        sys.exit(0 if success else 1)

except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure the required dependencies are installed.")
    sys.exit(1)

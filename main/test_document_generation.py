#!/usr/bin/env python3
"""
Test script for the document generation functionality
"""

import sys
import json
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent / "src"))

from agent.document_generator import DocumentGenerator

def test_document_generation():
    """Test the document generation with sample team responses"""
    
    # Sample team responses (using existing structure)
    sample_team_responses = {
        "finance_team": {
            "content": "## Financial Analysis\n\nOur comprehensive financial analysis demonstrates exceptional value proposition through strategic cost optimization and ROI maximization.",
            "timestamp": "2025-09-27 14:00:00",
            "team": "finance_team"
        },
        "technical_team": {
            "content": "## Technical Architecture\n\nWe propose a cloud-native, microservices architecture built on modern containerization platforms with automated CI/CD pipelines.",
            "timestamp": "2025-09-27 14:01:00", 
            "team": "technical_team"
        },
        "legal_team": {
            "content": "## Legal & Compliance\n\nFull adherence to all regulatory requirements including GDPR, HIPAA, and industry-specific compliance standards.",
            "timestamp": "2025-09-27 14:02:00",
            "team": "legal_team"
        },
        "qa_team": {
            "content": "## Quality Assurance\n\nComprehensive testing strategy including automated unit testing, integration testing, and performance validation.",
            "timestamp": "2025-09-27 14:03:00",
            "team": "qa_team"
        }
    }
    
    print("🧪 Testing Document Generation")
    print("=" * 50)
    
    # Initialize document generator
    doc_gen = DocumentGenerator()
    
    # Create output directory
    output_dir = Path("test_output")
    output_dir.mkdir(exist_ok=True)
    
    try:
        # Generate all document formats
        generated_files = doc_gen.generate_all_formats(sample_team_responses, output_dir)
        
        print("\n✅ Document generation completed successfully!")
        print("\n📁 Generated files:")
        
        for format_type, file_path in generated_files.items():
            print(f"   {format_type.upper()}: {file_path}")
            
            # Check if file exists and get size
            if file_path.exists():
                size = file_path.stat().st_size
                print(f"      ✓ File exists ({size:,} bytes)")
            else:
                print(f"      ❌ File not found!")
        
        # Display some content from the Markdown file
        if "markdown" in generated_files:
            markdown_file = generated_files["markdown"]
            with open(markdown_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                print(f"\n📖 Preview of Markdown content (first 20 lines):")
                print("-" * 60)
                for i, line in enumerate(lines[:20]):
                    print(f"{i+1:2d}: {line}")
                if len(lines) > 20:
                    print(f"    ... and {len(lines)-20} more lines")
        
        print(f"\n🎉 Test completed! Check the '{output_dir}' directory for generated files.")
        
    except Exception as e:
        print(f"❌ Error during document generation: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_document_generation()
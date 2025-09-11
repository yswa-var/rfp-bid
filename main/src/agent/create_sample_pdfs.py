#!/usr/bin/env python3
"""
Create Sample PDFs Script

This script converts the sample text files to PDF format for testing the RAG systems.

Usage:
    python3 create_sample_pdfs.py
"""

import os
import sys
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def create_pdf_from_text(text_file_path, output_pdf_path):
    """Convert a text file to PDF format."""
    try:
        # Read the text file
        with open(text_file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Create PDF document
        doc = SimpleDocTemplate(str(output_pdf_path), pagesize=letter)
        styles = getSampleStyleSheet()
        
        # Create a custom style for the content
        content_style = ParagraphStyle(
            'CustomContent',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            leftIndent=0,
            rightIndent=0,
            alignment=0,  # Left alignment
        )
        
        # Split content into paragraphs
        paragraphs = content.split('\n\n')
        
        # Create story (list of flowables)
        story = []
        
        for para in paragraphs:
            if para.strip():  # Skip empty paragraphs
                # Clean up the paragraph text
                para_text = para.strip().replace('\n', ' ')
                story.append(Paragraph(para_text, content_style))
                story.append(Spacer(1, 6))
        
        # Build PDF
        doc.build(story)
        print(f"✅ Created PDF: {output_pdf_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error creating PDF {output_pdf_path}: {str(e)}")
        return False

def main():
    """Main function to convert all text files to PDFs."""
    print("🔄 Converting sample text files to PDF format...")
    
    # Define source and output directories
    base_dir = Path("/Users/yash/Documents/rfp/rfp-bid/example-PDF")
    templates_dir = base_dir / "templates"
    rfp_dir = base_dir / "rfp-examples"
    
    # Create output directories
    templates_pdf_dir = base_dir / "templates-pdf"
    rfp_pdf_dir = base_dir / "rfp-pdf"
    
    templates_pdf_dir.mkdir(exist_ok=True)
    rfp_pdf_dir.mkdir(exist_ok=True)
    
    success_count = 0
    total_count = 0
    
    # Convert template files
    print("\n📄 Converting template files...")
    for text_file in templates_dir.glob("*.txt"):
        pdf_file = templates_pdf_dir / f"{text_file.stem}.pdf"
        total_count += 1
        if create_pdf_from_text(text_file, pdf_file):
            success_count += 1
    
    # Convert RFP files
    print("\n📋 Converting RFP files...")
    for text_file in rfp_dir.glob("*.txt"):
        pdf_file = rfp_pdf_dir / f"{text_file.stem}.pdf"
        total_count += 1
        if create_pdf_from_text(text_file, pdf_file):
            success_count += 1
    
    print(f"\n📊 Conversion Results: {success_count}/{total_count} files converted successfully")
    
    if success_count == total_count:
        print("✅ All files converted successfully!")
        print(f"📁 Template PDFs: {templates_pdf_dir}")
        print(f"📁 RFP PDFs: {rfp_pdf_dir}")
    else:
        print("❌ Some files failed to convert. Check error messages above.")
    
    return success_count == total_count

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

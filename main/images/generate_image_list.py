#!/usr/bin/env python3
"""
Script to generate a list of image file names from the images directory
and save them to a CSV file.
"""

import os
import csv
from pathlib import Path

def generate_image_list():
    """Generate a list of image files and save to CSV."""
    
    # Define the images directory path
    images_dir = Path("/Users/yash/Documents/rfp/rfp-bid/main/images")
    
    # Define the output CSV file path
    csv_file = images_dir / "image_name_dicription.csv"
    
    # Supported image extensions
    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp', '.svg'}
    
    # Get all image files from the directory
    image_files = []
    for file_path in images_dir.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in image_extensions:
            image_files.append(file_path.name)
    
    # Sort the list alphabetically
    image_files.sort()
    
    # Write to CSV file
    with open(csv_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header
        writer.writerow(['Image Name', 'Description'])
        
        # Write image names with empty description column
        for image_name in image_files:
            writer.writerow([image_name, ''])
    
    print(f"Generated CSV file with {len(image_files)} image names:")
    for image_name in image_files:
        print(f"  - {image_name}")
    
    print(f"\nCSV file saved to: {csv_file}")

if __name__ == "__main__":
    generate_image_list()

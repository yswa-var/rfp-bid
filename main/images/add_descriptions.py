#!/usr/bin/env python3
"""
Script to add random descriptions to the image_name_dicription.csv file
for testing the image_adder_node.py functionality.
"""

import csv
import random
from pathlib import Path

def add_descriptions():
    """Add random descriptions to the CSV file."""
    
    # Define the CSV file path
    csv_file = Path("/Users/yash/Documents/rfp/rfp-bid/main/images/image_name_dicription.csv")
    
    # Sample descriptions that would be relevant for RFP/proposal documents
    descriptions = [
        "System architecture diagram showing overall infrastructure and component relationships",
        "Security infrastructure overview displaying network security zones and protection layers",
        "Technical implementation details and deployment workflow diagram",
        "Project timeline and milestone visualization chart",
        "Team structure and organizational hierarchy diagram",
        "Budget breakdown and cost analysis visualization",
        "Network topology and connectivity map",
        "Data flow diagram illustrating information processing",
        "Security compliance framework and certification roadmap",
        "Performance metrics dashboard and monitoring interface",
        "Risk assessment matrix and mitigation strategies",
        "Quality assurance process flow and testing procedures",
        "Disaster recovery and business continuity planning",
        "Technology stack comparison and selection criteria",
        "Implementation phases and delivery schedule",
        "Resource allocation and capacity planning",
        "Vendor evaluation criteria and scoring matrix",
        "Cost-benefit analysis and ROI projections",
        "Integration architecture and API specifications",
        "Monitoring and alerting system configuration",
        "Backup and recovery procedures documentation",
        "User interface mockups and design specifications",
        "Database schema and data modeling diagrams",
        "Cloud infrastructure and deployment architecture",
        "Security policies and access control mechanisms"
    ]
    
    # Read existing CSV data
    rows = []
    with open(csv_file, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            rows.append(row)
    
    # Add random descriptions to rows that don't have them
    for row in rows:
        if not row.get('Description', '').strip():
            row['Description'] = random.choice(descriptions)
    
    # Write back to CSV
    with open(csv_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Image Name', 'Description']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    
    print("✅ Added random descriptions to all images:")
    for row in rows:
        print(f"  • {row['Image Name']}")
        print(f"    Description: {row['Description']}")
        print()
    
    print(f"CSV file updated: {csv_file}")

if __name__ == "__main__":
    add_descriptions()

#!/bin/bash

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '#' | awk '/=/ {print $1}')
fi

# Start the Teams bot
echo "Starting DOCX Agent Teams Bot..."
python app.py
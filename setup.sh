#!/bin/bash

# Pharmacy Stock Management System - Setup Script

echo "=========================================="
echo "Pharmacy Stock Management System Setup"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "✓ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env and add your API keys and configuration"
    echo ""
else
    echo "✓ .env file already exists"
    echo ""
fi

# Check if credentials.json exists
if [ ! -f "credentials.json" ]; then
    echo "⚠️  WARNING: credentials.json not found!"
    echo "   Please download your Google service account JSON key"
    echo "   and save it as 'credentials.json' in this directory"
    echo ""
else
    echo "✓ credentials.json found"
    echo ""
fi

# Create uploads directory if it doesn't exist
if [ ! -d "static/uploads" ]; then
    echo "Creating static/uploads directory..."
    mkdir -p static/uploads
    touch static/uploads/.gitkeep
    echo "✓ Uploads directory created"
    echo ""
fi

echo "=========================================="
echo "Setup Checklist:"
echo "=========================================="
echo ""
echo "Before running the application, ensure:"
echo ""
echo "[ ] 1. Edit .env file with your API keys and configuration"
echo "[ ] 2. Add credentials.json (Google service account key)"
echo "[ ] 3. Create Google Sheets (Master Data + Output)"
echo "[ ] 4. Share sheets with service account email"
echo "[ ] 5. Create GCS bucket and configure permissions"
echo ""
echo "=========================================="
echo "Quick Start Commands:"
echo "=========================================="
echo ""
echo "Local Development:"
echo "  uv pip install -r pyproject.toml"
echo "  uvicorn main:app --reload"
echo ""
echo "Docker (Recommended):"
echo "  docker compose up --build"
echo ""
echo "=========================================="
echo ""
echo "For detailed instructions, see README.md"
echo ""

#!/bin/bash
# Simple launcher script for beads-web

cd "$(dirname "$0")"

echo "🔷 Starting Beads Web Interface..."
echo "📁 Reading issues from: $(realpath ../.beads/issues.jsonl)"
echo "🌐 Server will be available at: http://localhost:8000"
echo ""

# Check if .beads/issues.jsonl exists
if [ ! -f "../.beads/issues.jsonl" ]; then
    echo "⚠️  Warning: Issues file not found at ../.beads/issues.jsonl"
    echo "   The interface will show empty data until issues are created."
    echo ""
fi

# Activate virtual environment and start server
source .venv/bin/activate
python run.py
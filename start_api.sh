#!/bin/bash

# EspressFlowCV API Server Startup Script

echo "🚀 Starting EspressFlowCV API Server..."

# Check if conda environment exists
if conda info --envs | grep -q "coffeecv"; then
    echo "📦 Activating coffeecv environment..."
    source ~/miniconda3/etc/profile.d/conda.sh  # Adjust path if needed
    conda activate coffeecv
else
    echo "⚠️  coffeecv environment not found. Using system Python."
fi

# Install Flask dependencies if not already installed
echo "📋 Installing API dependencies..."
pip install -r requirements.txt

# Check if database directory exists
if [ ! -d "database" ]; then
    echo "❌ database/ directory not found. Make sure you're in the CoffeeCV root directory."
    exit 1
fi

# Start the API server
echo "🌐 Starting Flask API server on http://localhost:5000"
echo "📊 Health check: http://localhost:5000/api/health"
echo "📚 API endpoints:"
echo "   POST /api/analyze - Upload video for analysis"
echo "   GET  /api/shots   - List all shots"
echo "   GET  /api/stats   - Dashboard statistics"
echo ""
echo "Press Ctrl+C to stop the server"

# For development
python api_server.py

# For production, uncomment this instead:
# gunicorn -w 4 -b 0.0.0.0:5000 api_server:app
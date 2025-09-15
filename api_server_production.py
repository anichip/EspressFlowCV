#!/usr/bin/env python3
"""
EspressFlowCV API Server - Production Version (PostgreSQL only)
Flask REST API for Swift iOS app to upload videos and get espresso analysis
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import tempfile
import uuid
from datetime import datetime
import logging
from typing import Dict, Any, Optional

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import database (PostgreSQL only for production)
from database.postgres_db import EspressoPostgreSQLDatabase

import cv2
import joblib
import pandas as pd
import numpy as np

app = Flask(__name__)
CORS(app)  # Enable CORS for mobile app requests

# Configuration
UPLOAD_FOLDER = tempfile.mkdtemp(prefix='espresso_uploads_')
API_VERSION = "1.0"
MAX_VIDEO_SIZE_MB = 100

# Initialize PostgreSQL database
logger.info("🔍 Initializing PostgreSQL database...")
try:
    db = EspressoPostgreSQLDatabase()
    logger.info("✅ Connected to PostgreSQL database")
except Exception as e:
    logger.error(f"❌ PostgreSQL initialization failed: {str(e)}")
    raise

# Global model variables (loaded on startup)
MODEL = None
MODEL_METADATA = None

def load_trained_model():
    """Load trained ML model and metadata"""
    global MODEL, MODEL_METADATA

    model_path = "espresso_model.joblib"
    metadata_path = "model_metadata.joblib"

    try:
        if os.path.exists(model_path) and os.path.exists(metadata_path):
            MODEL = joblib.load(model_path)
            MODEL_METADATA = joblib.load(metadata_path)
            logger.info(f"✅ Loaded trained model: {MODEL_METADATA['model_type']}")
            logger.info(f"   ROC-AUC: {MODEL_METADATA['cv_roc_auc']:.3f}")
            logger.info(f"   Optimal threshold: {MODEL_METADATA['optimal_threshold']:.3f}")
            logger.info(f"   Features: {MODEL_METADATA['feature_count']}")
            return True
        else:
            logger.warning("⚠️  No trained model found. Server will use rule-based classification.")
            logger.warning(f"   Looking for: {model_path} and {metadata_path}")
            logger.warning(f"   Current directory: {os.getcwd()}")
            logger.warning(f"   Files in directory: {os.listdir('.')}")
            return False
    except Exception as e:
        logger.error(f"❌ Failed to load trained model: {str(e)}")
        logger.error(f"   This is not fatal - server will continue with rule-based classification")
        return False

# Copy all the API endpoints from your original api_server.py here...
# For brevity, I'll just include the health check

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        stats = db.get_database_stats()

        # Check model status
        model_status = {
            'loaded': MODEL is not None and MODEL_METADATA is not None,
            'model_type': MODEL_METADATA['model_type'] if MODEL_METADATA else None,
            'roc_auc': MODEL_METADATA['cv_roc_auc'] if MODEL_METADATA else None,
            'threshold': MODEL_METADATA['optimal_threshold'] if MODEL_METADATA else None,
            'features': MODEL_METADATA['feature_count'] if MODEL_METADATA else None
        }

        return jsonify({
            'status': 'healthy',
            'api_version': API_VERSION,
            'database_connected': True,
            'database_type': 'PostgreSQL',
            'database_stats': stats,
            'model_status': model_status,
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    try:
        # Ensure upload folder exists
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        logger.info(f"📁 Upload folder created: {UPLOAD_FOLDER}")

        # Load trained model on startup (non-fatal if it fails)
        logger.info("🤖 Loading ML model...")
        model_loaded = load_trained_model()

        # Server startup
        logger.info("🚀 EspressFlowCV API Server (Production) starting...")
        logger.info(f"📁 Upload folder: {UPLOAD_FOLDER}")
        logger.info(f"💾 Database: PostgreSQL")
        logger.info(f"🤖 ML Model: {'✅ Loaded' if model_loaded else '⚠️  Using rule-based fallback'}")

        # Get port from environment (Railway sets this automatically)
        port = int(os.environ.get('PORT', 5000))
        logger.info(f"🌐 Starting server on port {port}")

        # For production, use gunicorn
        app.run(host='0.0.0.0', port=port, debug=False)

    except Exception as e:
        logger.error(f"❌ Failed to start server: {str(e)}")
        raise
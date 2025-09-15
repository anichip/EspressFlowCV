#!/usr/bin/env python3
"""
EspressFlowCV API Server
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

# Import your existing modules
try:
    from database.postgres_db import EspressoPostgreSQLDatabase as EspressoDatabase
    logger.info("Using PostgreSQL database for production")
except ImportError:
    from database.espresso_db import EspressoDatabase
    logger.info("Using SQLite database for development")
import cv2
import joblib
import pandas as pd
import numpy as np

# Logger already configured above

app = Flask(__name__)
CORS(app)  # Enable CORS for mobile app requests

# Configuration
UPLOAD_FOLDER = tempfile.mkdtemp(prefix='espresso_uploads_')
API_VERSION = "1.0"
MAX_VIDEO_SIZE_MB = 100  # 50MB max video size

# Initialize database
# In production (Railway), use PostgreSQL with DATABASE_URL
# In development, fall back to SQLite
try:
    if os.environ.get('DATABASE_URL'):
        db = EspressoDatabase()  # PostgreSQL (no argument needed, uses env var)
        logger.info("✅ Connected to PostgreSQL database")
    else:
        db = EspressoDatabase("espresso_shots.db")  # SQLite for local development
        logger.info("✅ Connected to SQLite database")
except Exception as e:
    logger.error(f"❌ Database initialization failed: {str(e)}")
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

def classify_with_trained_model(features_dict: Dict) -> tuple:
    """
    Use trained ML model to classify espresso shot
    
    Args:
        features_dict: Dictionary of extracted features
        
    Returns:
        tuple: (classification, confidence)
    """
    global MODEL, MODEL_METADATA
    
    if MODEL is None or MODEL_METADATA is None:
        logger.warning("Model not loaded, falling back to rule-based classification")
        from espresso_flow_features import simple_rule_classifier
        classification = simple_rule_classifier(features_dict)
        return classification, 0.5  # Default confidence
    
    try:
        # Prepare features in the same order as training
        feature_names = MODEL_METADATA['feature_names']
        feature_values = []
        
        for feature_name in feature_names:
            if feature_name in features_dict:
                feature_values.append(features_dict[feature_name])
            else:
                # Missing feature - use NaN so SimpleImputer can handle it properly
                feature_values.append(np.nan)
                logger.warning(f"Missing feature: {feature_name}")
        
        # Create DataFrame with proper column names
        X = pd.DataFrame([feature_values], columns=feature_names)
        
        # Get probability prediction
        probabilities = MODEL.predict_proba(X)[0]  # Get first (and only) prediction
        under_probability = probabilities[1]  # Class 1 = 'under'
        
        # Use optimal threshold from training
        optimal_threshold = MODEL_METADATA['optimal_threshold']
        
        # Classify based on threshold
        if under_probability >= optimal_threshold:
            classification = 'under'
            confidence = under_probability
        else:
            classification = 'good'
            confidence = 1.0 - under_probability
        
        logger.info(f"ML prediction: {classification} (confidence: {confidence:.3f}, threshold: {optimal_threshold:.3f})")
        
        return classification, round(confidence, 3)
        
    except Exception as e:
        logger.error(f"❌ ML prediction failed: {str(e)}")
        # Fallback to rule-based
        from espresso_flow_features import simple_rule_classifier
        classification = simple_rule_classifier(features_dict)
        return classification, 0.1  # Low confidence for fallback

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

@app.route('/api/analyze', methods=['POST'])
def analyze_espresso_shot():
    """
    Main analysis endpoint for Swift app
    
    Expected payload:
    - video: Video file (multipart/form-data)
    - metadata: JSON with optional fields (notes, recorded_at, etc.)
    
    Returns:
    - analysis_result: "good" | "under"
    - confidence: float 0.0-1.0
    - features: dict of extracted features
    - shot_id: database ID for reference
    """
    try:
        # Validate request
        if 'video' not in request.files:
            return jsonify({'error': 'No video file provided'}), 400
        
        video_file = request.files['video']
        if video_file.filename == '':
            return jsonify({'error': 'No video file selected'}), 400
        
        # Check file size
        video_file.seek(0, os.SEEK_END)
        file_size_mb = video_file.tell() / (1024 * 1024)
        video_file.seek(0)
        
        if file_size_mb > MAX_VIDEO_SIZE_MB:
            return jsonify({'error': f'Video too large. Max size: {MAX_VIDEO_SIZE_MB}MB'}), 400
        
        # Generate unique filename
        video_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"shot_{timestamp}_{video_id[:8]}.mp4"
        
        # Save video temporarily
        temp_video_path = os.path.join(UPLOAD_FOLDER, filename)
        video_file.save(temp_video_path)
        
        logger.info(f"Processing video: {filename} ({file_size_mb:.1f}MB)")
        
        # Extract metadata first
        metadata = {}
        if 'metadata' in request.form:
            import json
            try:
                metadata = json.loads(request.form['metadata'])
                print(f"INFO:__main__:Received metadata: {metadata}")
            except json.JSONDecodeError:
                logger.warning("Invalid metadata JSON, using defaults")

        # Process with your existing CV pipeline
        analysis_result = process_video_for_api(temp_video_path, video_id, metadata)
        
        # Store in database
        shot_id = db.add_shot(
            filename=filename,
            analysis_result=analysis_result['classification'],
            confidence=analysis_result.get('confidence', 0.0),
            features=analysis_result.get('features', {}),
            video_duration_s=analysis_result.get('duration_s',0.0),
            notes=metadata.get('notes', ''),
            recorded_at=metadata.get('recorded_at')
        )
        
        # Cleanup temporary file
        try:
            os.remove(temp_video_path)
        except OSError:
            logger.warning(f"Could not cleanup temp file: {temp_video_path}")
        
        # Return results
        response = {
            'shot_id': shot_id,
            'filename': filename,
            'analysis_result': analysis_result['classification'],
            'confidence': analysis_result.get('confidence', 0.0),
            'features': analysis_result.get('features', {}),
            'processing_time_s': analysis_result.get('processing_time_s', 0.0),
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Analysis complete: {filename} → {analysis_result['classification']} (confidence: {analysis_result.get('confidence', 0.0):.2f})")
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        return jsonify({
            'error': 'Analysis failed',
            'details': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

def clean_shot_for_json(shot):
    """Clean a shot dictionary to ensure JSON serialization works"""
    cleaned_shot = shot.copy()

    # Clean features if they exist
    if 'features' in cleaned_shot and cleaned_shot['features']:
        try:
            import json
            features = json.loads(cleaned_shot['features']) if isinstance(cleaned_shot['features'], str) else cleaned_shot['features']
            clean_features = {}
            for key, value in features.items():
                if isinstance(value, (int, float)):
                    if np.isnan(value) or np.isinf(value):
                        clean_features[key] = None
                    else:
                        clean_features[key] = float(value)
                else:
                    clean_features[key] = value
            cleaned_shot['features'] = clean_features
        except:
            cleaned_shot['features'] = {}

    # Clean other numeric fields
    for field in ['confidence', 'video_duration_s']:
        if field in cleaned_shot and cleaned_shot[field] is not None:
            if isinstance(cleaned_shot[field], (int, float)):
                if np.isnan(cleaned_shot[field]) or np.isinf(cleaned_shot[field]):
                    cleaned_shot[field] = None

    return cleaned_shot

@app.route('/api/shots', methods=['GET'])
def get_shots():
    """Get all shots with optional filtering"""
    try:
        # Query parameters
        limit = request.args.get('limit', type=int)
        result_filter = request.args.get('result')  # 'good' or 'under'

        if result_filter:
            shots = db.get_shots_by_result(result_filter)
        else:
            shots = db.get_all_shots(limit=limit)

        # Clean shots for JSON serialization
        clean_shots = [clean_shot_for_json(shot) for shot in shots]

        return jsonify({
            'shots': clean_shots,
            'count': len(clean_shots),
            'timestamp': datetime.now().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Failed to get shots: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/shots/<int:shot_id>', methods=['GET'])
def get_shot(shot_id):
    """Get specific shot by ID"""
    try:
        shot = db.get_shot_by_id(shot_id)
        if not shot:
            return jsonify({'error': 'Shot not found'}), 404
        
        return jsonify({
            'shot': shot,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get shot {shot_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/shots/<int:shot_id>', methods=['DELETE'])
def delete_shot(shot_id):
    """Delete shot by ID"""
    try:
        deleted = db.delete_shot(shot_id)
        if not deleted:
            return jsonify({'error': 'Shot not found'}), 404
        
        return jsonify({
            'message': f'Shot {shot_id} deleted successfully',
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to delete shot {shot_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/shots/<int:shot_id>/notes', methods=['PUT'])
def update_shot_notes(shot_id):
    """Update notes for a shot"""
    try:
        data = request.get_json()
        if not data or 'notes' not in data:
            return jsonify({'error': 'Notes field required'}), 400
        
        updated = db.add_notes(shot_id, data['notes'])
        if not updated:
            return jsonify({'error': 'Shot not found'}), 404
        
        return jsonify({
            'message': 'Notes updated successfully',
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to update notes for shot {shot_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_statistics():
    """Get shot statistics for dashboard"""
    try:
        summary = db.get_shots_summary()
        db_stats = db.get_database_stats()
        
        return jsonify({
            'summary': summary,
            'database': db_stats,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

def process_video_for_api(video_path: str, video_id: str, metadata: Dict = None) -> Dict[str, Any]:
    """
    Wrapper around your existing CV pipeline for API use
    Uses extract_frames.py then process_frames_folder
    
    Args:
        video_path: Path to uploaded video file
        video_id: Unique ID for temporary files
        
    Returns:
        Dict with classification, confidence, features, etc.
    """
    try:
        import time
        import shutil
        start_time = time.time()
        
        # Create temporary directory structure to mimic your existing setup
        temp_video_dir = os.path.join(UPLOAD_FOLDER, f"temp_video_{video_id}")
        temp_frames_dir = os.path.join(UPLOAD_FOLDER, f"temp_frames_{video_id}")
        os.makedirs(temp_video_dir, exist_ok=True)
        
        # Copy video to temporary location with expected naming
        temp_video_path = os.path.join(temp_video_dir, f"api_shot_{video_id}.mp4")
        shutil.copy2(video_path, temp_video_path)
        
        # Get video duration first
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        duration_s = frame_count / fps if fps > 0 else 0.0
        cap.release()
        
        # Import and use your existing extract_frames logic
        from extract_frames import run_extraction
        
        # Temporarily modify extract_frames to work with our temp directory
        # We'll call the internal logic directly to avoid the hard-coded paths
        frames_extracted = extract_frames_for_single_video(temp_video_path, temp_frames_dir)
        
        if not frames_extracted:
            raise Exception("Failed to extract frames from video")
        
        # Find the frames folder (should be named after video basename)
        video_basename = os.path.splitext(os.path.basename(temp_video_path))[0]
        frames_folder = os.path.join(temp_frames_dir, video_basename)
        
        if not os.path.exists(frames_folder):
            raise Exception(f"Frames folder not created: {frames_folder}")
        
        logger.info(f"Extracted frames to {frames_folder}")
        
        # Now use your existing process_frames_folder function
        from espresso_flow_features import process_frames_folder, simple_rule_classifier

        features_dict = process_frames_folder(frames_folder)

        # Add duration from metadata if provided (more accurate than CV calculation)
        if metadata and 'pull_duration_s' in metadata:
            features_dict['pull_duration_s'] = metadata['pull_duration_s']
            duration_s = metadata['pull_duration_s']  # Use metadata duration
            print(f"INFO:__main__:Using metadata duration: {duration_s:.2f}s")

        # Use trained ML model instead of simple rule classifier
        classification, confidence = classify_with_trained_model(features_dict)
        
        # Cleanup temporary directories
        try:
            shutil.rmtree(temp_video_dir)
            shutil.rmtree(temp_frames_dir)
        except OSError:
            logger.warning(f"Could not cleanup temp directories")
        
        processing_time = time.time() - start_time
        
        return {
            'classification': classification,
            'confidence': confidence,
            'features': features_dict,
            'duration_s': duration_s,
            'processing_time_s': processing_time
        }
        
    except Exception as e:
        logger.error(f"Video processing failed: {str(e)}")
        # Cleanup on failure
        try:
            temp_video_dir = os.path.join(UPLOAD_FOLDER, f"temp_video_{video_id}")
            temp_frames_dir = os.path.join(UPLOAD_FOLDER, f"temp_frames_{video_id}")
            if os.path.exists(temp_video_dir):
                shutil.rmtree(temp_video_dir)
            if os.path.exists(temp_frames_dir):
                shutil.rmtree(temp_frames_dir)
        except:
            pass
            
        # Return safe defaults for failed processing
        return {
            'classification': 'under',  # Conservative default
            'confidence': 0.1,
            'features': {},
            'duration_s': 0.0,
            'processing_time_s': 0.0,
            'error': str(e)
        }

def extract_frames_for_single_video(video_path: str, output_root: str) -> bool:
    """
    Extract frames from a single video using your extract_frames.py logic
    
    Args:
        video_path: Path to video file
        output_root: Where to save frames
        
    Returns:
        bool: True if successful
    """
    try:
        import csv
        
        os.makedirs(output_root, exist_ok=True)
        
        # Settings from your extract_frames.py
        clip_duration_sec = 7
        target_fps = 60
        
        video_name = os.path.basename(video_path)
        
        if not video_name.lower().endswith(('.mp4', '.mov', '.avi')):
            return False
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return False
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if fps <= 0 or total_frames <= 0:
            cap.release()
            return False
        
        max_frames = int(min(clip_duration_sec * target_fps, total_frames))
        video_basename = os.path.splitext(video_name)[0]
        output_dir = os.path.join(output_root, video_basename)
        os.makedirs(output_dir, exist_ok=True)
        
        # Extract frames (skip first 1 second like your original code)
        frame_count = 0
        saved_frame_count = 0
        frames_to_skip = int(fps)  # Skip 1 second
        
        while cap.isOpened() and saved_frame_count < max_frames:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Skip first second
            if frame_count < frames_to_skip:
                frame_count += 1
                continue
            
            if frame is not None:
                frame_filename = os.path.join(output_dir, f"frame_{saved_frame_count:04d}.jpg")
                cv2.imwrite(frame_filename, frame)
                saved_frame_count += 1
            
            frame_count += 1
        
        cap.release()
        
        # Create pull_times.csv for compatibility
        csv_path = os.path.join(output_root, "pull_times.csv")
        with open(csv_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['filename', 'duration_s'])
            duration_s = saved_frame_count / target_fps
            writer.writerow([video_name, duration_s])
        
        return saved_frame_count > 0
        
    except Exception as e:
        logger.error(f"Frame extraction failed: {str(e)}")
        return False

def classify_from_features(features: Dict) -> str:
    """
    Simple rule-based classifier until you integrate your trained model
    
    Replace this with your actual ML model prediction
    """
    if not features:
        return 'under'
    
    # Example simple rules based on your features
    # Replace with your trained model
    onset_time = features.get('onset_time_s', 10)  # Default to slow start
    continuity = features.get('continuity', 0.0)
    mean_width = features.get('mean_width', 0.0)
    
    # Simple heuristics (replace with your model)
    if onset_time < 3.0 and continuity > 0.7 and mean_width > 15:
        return 'good'
    else:
        return 'under'

def calculate_confidence(features: Dict, classification: str) -> float:
    """
    Calculate confidence score for the classification
    
    Replace with your actual model's confidence output
    """
    if not features:
        return 0.1
    
    # Simple confidence calculation based on feature quality
    # Replace with your model's actual confidence
    feature_quality = 0.0
    
    if 'onset_time_s' in features:
        feature_quality += 0.2
    if 'continuity' in features:
        feature_quality += 0.3
    if 'mean_width' in features:
        feature_quality += 0.3
    if 'flicker' in features:
        feature_quality += 0.2
    
    # Add some randomness to simulate model uncertainty
    import random
    base_confidence = max(0.5, min(0.95, feature_quality + random.uniform(-0.1, 0.1)))
    
    return round(base_confidence, 2)

@app.errorhandler(413)
def too_large(e):
    """Handle file too large errors"""
    return jsonify({'error': f'File too large. Max size: {MAX_VIDEO_SIZE_MB}MB'}), 413

@app.errorhandler(500)
def internal_error(error):
    """Handle internal server errors"""
    logger.error(f"Internal error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    try:
        # Ensure upload folder exists
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        logger.info(f"📁 Upload folder created: {UPLOAD_FOLDER}")

        # Initialize database
        logger.info("💾 Initializing database...")
        db_stats = db.get_database_stats()
        logger.info(f"   Database ready: {db_stats['database_path']}")

        # Load trained model on startup (non-fatal if it fails)
        logger.info("🤖 Loading ML model...")
        model_loaded = load_trained_model()

        # Server startup
        logger.info("🚀 EspressFlowCV API Server starting...")
        logger.info(f"📁 Upload folder: {UPLOAD_FOLDER}")
        logger.info(f"💾 Database: espresso_shots.db")
        logger.info(f"🤖 ML Model: {'✅ Loaded' if model_loaded else '⚠️  Using rule-based fallback'}")

        # Get port from environment (Railway sets this automatically)
        port = int(os.environ.get('PORT', 5000))
        logger.info(f"🌐 Starting server on port {port}")

        # For production, use gunicorn or similar WSGI server
        app.run(host='0.0.0.0', port=port, debug=False)

    except Exception as e:
        logger.error(f"❌ Failed to start server: {str(e)}")
        raise
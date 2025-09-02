#!/usr/bin/env python3
"""
EspressFlowCV Database Schema and CRUD Operations
SQLite database for storing espresso shot analysis results
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import json

class EspressoDatabase:
    """SQLite database manager for espresso shot analysis"""
    
    def __init__(self, db_path: str = "espresso_shots.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Create database and tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS shots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL UNIQUE,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    analysis_result TEXT NOT NULL CHECK (analysis_result IN ('good', 'under')),
                    confidence REAL DEFAULT 0.0,
                    features_json TEXT,
                    video_duration_s REAL,
                    notes TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for faster queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_recorded_at ON shots(recorded_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_result ON shots(analysis_result)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_filename ON shots(filename)")
            
            conn.commit()
    
    # ==================
    # CREATE Operations
    # ==================
    
    def add_shot(self, 
                 filename: str,
                 analysis_result: str,
                 confidence: float = 0.0,
                 features: Optional[Dict] = None,
                 video_duration_s: Optional[float] = None,
                 notes: str = "",
                 recorded_at: Optional[datetime] = None) -> int:
        """
        Add a new espresso shot to database
        
        Args:
            filename: Video filename (e.g., "shot_20241203_142301.mp4")
            analysis_result: "good" or "under"  
            confidence: Model confidence score (0.0 - 1.0)
            features: Dict of extracted features from ML pipeline
            video_duration_s: Length of recorded video
            notes: Optional user notes
            recorded_at: When shot was recorded (defaults to now)
            
        Returns:
            int: ID of inserted record
        """
        features_json = json.dumps(features) if features else None
        recorded_timestamp = recorded_at or datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO shots (filename, recorded_at, analysis_result, confidence, 
                                 features_json, video_duration_s, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (filename, recorded_timestamp, analysis_result, confidence, 
                  features_json, video_duration_s, notes))
            
            shot_id = cursor.lastrowid
            conn.commit()
            return shot_id
    
    # ================
    # READ Operations  
    # ================
    
    def get_shot_by_id(self, shot_id: int) -> Optional[Dict]:
        """Get shot by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM shots WHERE id = ?", (shot_id,))
            row = cursor.fetchone()
            
            if row:
                shot = dict(row)
                # Parse JSON features back to dict
                if shot['features_json']:
                    shot['features'] = json.loads(shot['features_json'])
                return shot
            return None
    
    def get_shot_by_filename(self, filename: str) -> Optional[Dict]:
        """Get shot by filename"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM shots WHERE filename = ?", (filename,))
            row = cursor.fetchone()
            
            if row:
                shot = dict(row)
                if shot['features_json']:
                    shot['features'] = json.loads(shot['features_json'])
                return shot
            return None
    
    def get_all_shots(self, limit: Optional[int] = None, order_by: str = "recorded_at DESC") -> List[Dict]:
        """
        Get all shots with optional limit and ordering
        
        Args:
            limit: Maximum number of results
            order_by: SQL ORDER BY clause (default: newest first)
        """
        query = f"SELECT * FROM shots ORDER BY {order_by}"
        if limit:
            query += f" LIMIT {limit}"
            
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            
            shots = []
            for row in rows:
                shot = dict(row)
                if shot['features_json']:
                    shot['features'] = json.loads(shot['features_json'])
                shots.append(shot)
            
            return shots
    
    def get_shots_by_result(self, result: str) -> List[Dict]:
        """Get all shots with specific result ('good' or 'under')"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM shots WHERE analysis_result = ? ORDER BY recorded_at DESC", (result,))
            rows = cursor.fetchall()
            
            shots = []
            for row in rows:
                shot = dict(row)
                if shot['features_json']:
                    shot['features'] = json.loads(shot['features_json'])
                shots.append(shot)
                
            return shots
    
    def get_shots_summary(self) -> Dict[str, int]:
        """Get summary statistics for dashboard"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total counts by result
            cursor.execute("SELECT analysis_result, COUNT(*) FROM shots GROUP BY analysis_result")
            results = dict(cursor.fetchall())
            
            # Total shots
            cursor.execute("SELECT COUNT(*) FROM shots")
            total = cursor.fetchone()[0]
            
            return {
                'total_shots': total,
                'good_shots': results.get('good', 0),
                'under_shots': results.get('under', 0),
                'good_percentage': round(results.get('good', 0) / total * 100, 1) if total > 0 else 0,
                'under_percentage': round(results.get('under', 0) / total * 100, 1) if total > 0 else 0
            }
    
    # ==================
    # UPDATE Operations
    # ==================
    
    def update_shot(self, shot_id: int, **kwargs) -> bool:
        """
        Update shot fields by ID
        
        Args:
            shot_id: Shot ID to update
            **kwargs: Fields to update (analysis_result, confidence, notes, etc.)
            
        Returns:
            bool: True if update successful
        """
        if not kwargs:
            return False
            
        # Handle features dict -> JSON conversion
        if 'features' in kwargs:
            kwargs['features_json'] = json.dumps(kwargs.pop('features'))
        
        # Add updated_at timestamp
        kwargs['updated_at'] = datetime.now()
        
        # Build dynamic UPDATE query
        fields = list(kwargs.keys())
        placeholders = ', '.join([f"{field} = ?" for field in fields])
        values = list(kwargs.values()) + [shot_id]
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE shots SET {placeholders} WHERE id = ?", values)
            conn.commit()
            return cursor.rowcount > 0
    
    def add_notes(self, shot_id: int, notes: str) -> bool:
        """Add notes to a shot"""
        return self.update_shot(shot_id, notes=notes)
    
    # ==================
    # DELETE Operations
    # ==================
    
    def delete_shot(self, shot_id: int) -> bool:
        """Delete shot by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM shots WHERE id = ?", (shot_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_shot_by_filename(self, filename: str) -> bool:
        """Delete shot by filename"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM shots WHERE filename = ?", (filename,))
            conn.commit()
            return cursor.rowcount > 0
    
    def clear_all_shots(self) -> int:
        """Delete all shots (for testing). Returns number of deleted records."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM shots")
            deleted_count = cursor.rowcount
            conn.commit()
            return deleted_count
    
    # ==================
    # Utility Methods
    # ==================
    
    def get_database_stats(self) -> Dict:
        """Get database statistics for debugging"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Table info
            cursor.execute("PRAGMA table_info(shots)")
            columns = cursor.fetchall()
            
            # Database size
            db_size_bytes = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
            
            # Recent activity
            cursor.execute("SELECT COUNT(*) FROM shots WHERE created_at >= date('now', '-7 days')")
            recent_shots = cursor.fetchone()[0]
            
            return {
                'database_path': self.db_path,
                'database_size_bytes': db_size_bytes,
                'database_size_mb': round(db_size_bytes / 1024 / 1024, 2),
                'total_columns': len(columns),
                'recent_shots_7days': recent_shots
            }
    
    def export_to_csv(self, output_path: str) -> bool:
        """Export all shots to CSV for analysis"""
        import csv
        
        shots = self.get_all_shots()
        if not shots:
            return False
            
        with open(output_path, 'w', newline='') as csvfile:
            # Use first shot to determine fieldnames, exclude complex fields
            fieldnames = [k for k in shots[0].keys() if k not in ['features', 'features_json']]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for shot in shots:
                # Remove complex fields for CSV export
                csv_shot = {k: v for k, v in shot.items() if k in fieldnames}
                writer.writerow(csv_shot)
                
        return True


if __name__ == "__main__":
    # Basic testing when run directly
    print("Testing EspressFlowCV Database...")
    
    # Create test database
    db = EspressoDatabase("test_espresso.db")
    
    print("✅ Database initialized")
    print("📊 Database stats:", db.get_database_stats())
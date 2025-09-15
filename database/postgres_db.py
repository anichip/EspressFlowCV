#!/usr/bin/env python3
"""
EspressFlowCV PostgreSQL Database Schema and CRUD Operations
PostgreSQL database for storing espresso shot analysis results (Railway compatible)
"""

import psycopg2
import psycopg2.extras
import os
from datetime import datetime
from typing import List, Dict, Optional
import json
import logging

logger = logging.getLogger(__name__)

class EspressoPostgreSQLDatabase:
    """PostgreSQL database manager for espresso shot analysis"""

    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.environ.get('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set")

        self._init_database()

    def _get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.database_url)

    def _init_database(self):
        """Create database and tables if they don't exist"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS shots (
                            id SERIAL PRIMARY KEY,
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
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_recorded_at ON shots(recorded_at)")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_result ON shots(analysis_result)")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_filename ON shots(filename)")

                    conn.commit()
                    logger.info("✅ PostgreSQL database initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize PostgreSQL database: {str(e)}")
            raise

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

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO shots (filename, recorded_at, analysis_result, confidence,
                                     features_json, video_duration_s, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (filename, recorded_timestamp, analysis_result, confidence,
                      features_json, video_duration_s, notes))

                shot_id = cur.fetchone()[0]
                conn.commit()
                return shot_id

    # ================
    # READ Operations
    # ================

    def get_shot_by_id(self, shot_id: int) -> Optional[Dict]:
        """Get shot by ID"""
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM shots WHERE id = %s", (shot_id,))
                row = cur.fetchone()

                if row:
                    shot = dict(row)
                    # Parse JSON features back to dict
                    if shot['features_json']:
                        shot['features'] = json.loads(shot['features_json'])
                    return shot
                return None

    def get_shot_by_filename(self, filename: str) -> Optional[Dict]:
        """Get shot by filename"""
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM shots WHERE filename = %s", (filename,))
                row = cur.fetchone()

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
        params = []

        if limit:
            query += " LIMIT %s"
            params.append(limit)

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                rows = cur.fetchall()

                shots = []
                for row in rows:
                    shot = dict(row)
                    if shot['features_json']:
                        shot['features'] = json.loads(shot['features_json'])
                    shots.append(shot)

                return shots

    def get_shots_by_result(self, result: str) -> List[Dict]:
        """Get all shots with specific result ('good' or 'under')"""
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM shots WHERE analysis_result = %s ORDER BY recorded_at DESC", (result,))
                rows = cur.fetchall()

                shots = []
                for row in rows:
                    shot = dict(row)
                    if shot['features_json']:
                        shot['features'] = json.loads(shot['features_json'])
                    shots.append(shot)

                return shots

    def get_shots_summary(self) -> Dict[str, int]:
        """Get summary statistics for dashboard"""
        with self._get_connection() as conn:
            with conn.cursor() as cur:

                # Total counts by result
                cur.execute("SELECT analysis_result, COUNT(*) FROM shots GROUP BY analysis_result")
                results = dict(cur.fetchall())

                # Total shots
                cur.execute("SELECT COUNT(*) FROM shots")
                total = cur.fetchone()[0]

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
        placeholders = ', '.join([f"{field} = %s" for field in fields])
        values = list(kwargs.values()) + [shot_id]

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"UPDATE shots SET {placeholders} WHERE id = %s", values)
                conn.commit()
                return cur.rowcount > 0

    def add_notes(self, shot_id: int, notes: str) -> bool:
        """Add notes to a shot"""
        return self.update_shot(shot_id, notes=notes)

    # ==================
    # DELETE Operations
    # ==================

    def delete_shot(self, shot_id: int) -> bool:
        """Delete shot by ID"""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM shots WHERE id = %s", (shot_id,))
                conn.commit()
                return cur.rowcount > 0

    def delete_shot_by_filename(self, filename: str) -> bool:
        """Delete shot by filename"""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM shots WHERE filename = %s", (filename,))
                conn.commit()
                return cur.rowcount > 0

    def clear_all_shots(self) -> int:
        """Delete all shots (for testing). Returns number of deleted records."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM shots")
                deleted_count = cur.rowcount
                conn.commit()
                return deleted_count

    # ==================
    # Utility Methods
    # ==================

    def get_database_stats(self) -> Dict:
        """Get database statistics for debugging"""
        with self._get_connection() as conn:
            with conn.cursor() as cur:

                # Table info
                cur.execute("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = 'shots'
                """)
                columns = cur.fetchall()

                # Recent activity
                cur.execute("SELECT COUNT(*) FROM shots WHERE created_at >= NOW() - INTERVAL '7 days'")
                recent_shots = cur.fetchone()[0]

                return {
                    'database_url': self.database_url.split('@')[1] if '@' in self.database_url else 'hidden',
                    'database_type': 'PostgreSQL',
                    'total_columns': len(columns),
                    'recent_shots_7days': recent_shots
                }


if __name__ == "__main__":
    # Basic testing when run directly
    print("Testing EspressFlowCV PostgreSQL Database...")

    try:
        # Create test database
        db = EspressoPostgreSQLDatabase()
        print("✅ PostgreSQL database initialized")
        print("📊 Database stats:", db.get_database_stats())
    except Exception as e:
        print(f"❌ Failed to initialize database: {str(e)}")
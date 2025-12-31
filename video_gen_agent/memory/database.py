"""
SQLite Database for storing generation history and ratings.
Enables learning from past generations.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from video_gen_agent.config import config


class VideoGenDatabase:
    """Database for video generation history and ratings."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize database connection."""
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = config.data_dir / "video_gen.db"
        
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Create tables if they don't exist."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Generations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS generations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                topic TEXT NOT NULL,
                script TEXT,
                video_format TEXT,
                output_path TEXT,
                duration REAL,
                media_sources TEXT,  -- JSON array of source info
                status TEXT DEFAULT 'completed',
                metadata TEXT  -- JSON for additional data
            )
        """)
        
        # Ratings table - detailed rubric for better learning
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                generation_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                overall_score INTEGER CHECK(overall_score >= 1 AND overall_score <= 5),
                script_score INTEGER CHECK(script_score >= 1 AND script_score <= 5),
                visuals_score INTEGER CHECK(visuals_score >= 1 AND visuals_score <= 5),
                audio_score INTEGER CHECK(audio_score >= 1 AND audio_score <= 5),
                pacing_score INTEGER CHECK(pacing_score >= 1 AND pacing_score <= 5),
                feedback TEXT,
                FOREIGN KEY (generation_id) REFERENCES generations(id)
            )
        """)
        
        # Learned preferences table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                preference_type TEXT NOT NULL,  -- 'style', 'pacing', 'visuals', etc.
                preference_key TEXT NOT NULL,
                preference_value TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,  -- 0-1 based on rating patterns
                UNIQUE(preference_type, preference_key)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def save_generation(
        self,
        topic: str,
        script: str,
        video_format: str,
        output_path: str,
        duration: float,
        media_sources: list,
        metadata: Optional[dict] = None
    ) -> int:
        """
        Save a video generation record.
        
        Returns:
            The generation ID
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO generations 
            (topic, script, video_format, output_path, duration, media_sources, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            topic,
            script,
            video_format,
            output_path,
            duration,
            json.dumps(media_sources),
            json.dumps(metadata) if metadata else None
        ))
        
        generation_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return generation_id
    
    def save_rating(
        self,
        generation_id: int,
        overall_score: int,
        script_score: int = None,
        visuals_score: int = None,
        audio_score: int = None,
        pacing_score: int = None,
        feedback: str = None
    ) -> int:
        """
        Save a rating for a generation.
        
        Args:
            generation_id: ID of the generation to rate
            overall_score: Overall rating 1-5
            script_score: Script quality 1-5
            visuals_score: Visual quality 1-5
            audio_score: Audio quality 1-5
            pacing_score: Pacing quality 1-5
            feedback: Optional text feedback
        
        Returns:
            Rating ID
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO ratings 
            (generation_id, overall_score, script_score, visuals_score, 
             audio_score, pacing_score, feedback)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            generation_id,
            overall_score,
            script_score,
            visuals_score,
            audio_score,
            pacing_score,
            feedback
        ))
        
        rating_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return rating_id
    
    def get_generation(self, generation_id: int) -> Optional[dict]:
        """Get a generation by ID."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM generations WHERE id = ?
        """, (generation_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            result = dict(row)
            if result.get('media_sources'):
                result['media_sources'] = json.loads(result['media_sources'])
            if result.get('metadata'):
                result['metadata'] = json.loads(result['metadata'])
            return result
        return None
    
    def get_recent_generations(self, limit: int = 10) -> list[dict]:
        """Get recent generations."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT g.*, 
                   AVG(r.overall_score) as avg_rating,
                   COUNT(r.id) as rating_count
            FROM generations g
            LEFT JOIN ratings r ON g.id = r.generation_id
            GROUP BY g.id
            ORDER BY g.created_at DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            result = dict(row)
            if result.get('media_sources'):
                result['media_sources'] = json.loads(result['media_sources'])
            results.append(result)
        
        return results
    
    def get_ratings_by_category(self) -> dict:
        """Get average ratings by category for analysis."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                AVG(overall_score) as avg_overall,
                AVG(script_score) as avg_script,
                AVG(visuals_score) as avg_visuals,
                AVG(audio_score) as avg_audio,
                AVG(pacing_score) as avg_pacing,
                COUNT(*) as total_ratings
            FROM ratings
        """)
        
        row = cursor.fetchone()
        conn.close()
        
        return {
            "overall": row[0],
            "script": row[1],
            "visuals": row[2],
            "audio": row[3],
            "pacing": row[4],
            "total_ratings": row[5]
        }
    
    def update_preference(
        self,
        preference_type: str,
        preference_key: str,
        preference_value: str,
        confidence: float = 0.5
    ):
        """Update or insert a learned preference."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO preferences (preference_type, preference_key, preference_value, confidence)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(preference_type, preference_key) 
            DO UPDATE SET 
                preference_value = excluded.preference_value,
                confidence = excluded.confidence,
                updated_at = CURRENT_TIMESTAMP
        """, (preference_type, preference_key, preference_value, confidence))
        
        conn.commit()
        conn.close()
    
    def get_preferences(self, preference_type: Optional[str] = None) -> list[dict]:
        """Get learned preferences, optionally filtered by type."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if preference_type:
            cursor.execute("""
                SELECT * FROM preferences WHERE preference_type = ?
                ORDER BY confidence DESC
            """, (preference_type,))
        else:
            cursor.execute("""
                SELECT * FROM preferences ORDER BY confidence DESC
            """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_low_rated_aspects(self, threshold: float = 3.0) -> list[dict]:
        """Get aspects that consistently receive low ratings."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        averages = self.get_ratings_by_category()
        low_aspects = []
        
        for aspect in ['script', 'visuals', 'audio', 'pacing']:
            avg = averages.get(aspect)
            if avg and avg < threshold:
                low_aspects.append({
                    "aspect": aspect,
                    "average_score": avg,
                    "improvement_needed": True
                })
        
        conn.close()
        return low_aspects

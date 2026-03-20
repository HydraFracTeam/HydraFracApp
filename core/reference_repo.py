"""
Repository for accessing reference curves from SQLite database.
Works with storage/db/reference_curves.db
"""

import sqlite3
import numpy as np
import pandas as pd
from typing import List, Tuple, Optional, Dict
import logging
import os

logger = logging.getLogger(__name__)

# Global cache for skin library to avoid rebuilding
_global_skin_library_cache: Optional[Dict] = None
_global_db_path: Optional[str] = None


class ReferenceRepository:
    """
    Repository for loading reference curves from the database.
    Builds skin library for solver.
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Use absolute path relative to this file
            import os
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, "storage", "db", "reference_curves.db")
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None
        
    def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path)
            self._connection.row_factory = sqlite3.Row
        return self._connection
        
    def _close_connection(self):
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
    
    def load_all_data(self) -> pd.DataFrame:
        """
        Load all reference data from database into a single DataFrame.
        
        Returns:
            DataFrame with columns: Skin, h, N, W, L, a/L, X, Y
        """
        conn = self._get_connection()
        
        # Join statics and dynamics to get complete data
        query = """
            SELECT 
                s.Skin, s.h, s.N, s.W, s.L, s.aL as "a/L",
                d.X, d.Y
            FROM statics s
            JOIN dynamics d ON s.curve_id = d.curve_id
            ORDER BY s.curve_id, d.elemIdx
        """
        
        df = pd.read_sql_query(query, conn)
        logger.info(f"Loaded {len(df)} rows from database")
        
        return df
    
    def get_skin_library(self) -> Dict:
        """
        Build skin library from database.
        
        Returns:
            Dictionary: {skin_value: [samples]}
            where each sample is {
                'dynamic': DataFrame with X, Y columns,
                'h': float, 'N': float, 'W': float, 'L': float, 'a/L': float
            }
        """
        global _global_skin_library_cache, _global_db_path
        
        # Check cache
        if _global_skin_library_cache is not None and _global_db_path == self.db_path:
            logger.info("Using cached skin library")
            return _global_skin_library_cache
        
        conn = self._get_connection()
        
        # Get all static params grouped by curve_id
        query_static = "SELECT curve_id, Skin, h, N, W, L, aL FROM statics ORDER BY curve_id"
        static_df = pd.read_sql_query(query_static, conn)
        
        logger.info(f"Loaded {len(static_df)} static records")
        
        skin_library = {}
        
        for _, row in static_df.iterrows():
            curve_id = row['curve_id']
            skin_value = row['Skin']
            
            # Get dynamic data for this curve
            query_dynamic = "SELECT X, Y FROM dynamics WHERE curve_id = ? ORDER BY elemIdx"
            dynamic_df = pd.read_sql_query(query_dynamic, conn, params=(curve_id,))
            
            if dynamic_df.empty:
                continue
            
            sample = {
                'dynamic': dynamic_df,
                'h': row['h'],
                'N': row['N'],
                'W': row['W'],
                'L': row['L'],
                'a/L': row['aL'],
            }
            
            if skin_value not in skin_library:
                skin_library[skin_value] = []
            
            skin_library[skin_value].append(sample)
        
        self._close_connection()
        
        logger.info(f"Built skin library with {len(skin_library)} skin values")
        
        # Cache the library
        _global_skin_library_cache = skin_library
        _global_db_path = self.db_path
        
        return skin_library
    
    def get_available_skins(self) -> List[float]:
        """Get list of available skin values."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT Skin FROM statics ORDER BY Skin")
        skins = [row[0] for row in cursor.fetchall()]
        # Не закрываем соединение - оставляем для повторного использования
        return skins
    
    def get_curves_by_skin(self, skin: float) -> List[int]:
        """Get curve IDs for a specific skin value."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT curve_id FROM statics WHERE ABS(Skin - ?) < 0.001 ORDER BY curve_id",
            (skin,)
        )
        curve_ids = [row[0] for row in cursor.fetchall()]
        # Не закрываем соединение - оставляем для повторного использования
        return curve_ids
    
    def get_reference_curve(self, curve_id: int) -> Tuple[np.ndarray, np.ndarray]:
        """Get reference curve by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT X, Y FROM dynamics WHERE curve_id = ? ORDER BY elemIdx",
            (curve_id,)
        )
        rows = cursor.fetchall()
        # Не закрываем соединение - оставляем для повторного использования
        
        if not rows:
            raise ValueError(f"No curve found with curve_id {curve_id}")
        
        x = np.array([row[0] for row in rows])
        y = np.array([row[1] for row in rows])
        return x, y

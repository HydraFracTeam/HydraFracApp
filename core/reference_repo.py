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
from functools import lru_cache

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
                'x': dynamic_df['X'].to_numpy(dtype=float),
                'y': dynamic_df['Y'].to_numpy(dtype=float),
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

    @lru_cache(maxsize=1)
    def _cached_available_skins(self) -> Tuple[float, ...]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT Skin FROM statics ORDER BY Skin")
        return tuple(float(row[0]) for row in cursor.fetchall())

    @lru_cache(maxsize=1)
    def _cached_available_N_values(self) -> Tuple[int, ...]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT N FROM statics WHERE N IS NOT NULL ORDER BY N")
        return tuple(int(row[0]) for row in cursor.fetchall())

    @lru_cache(maxsize=512)
    def _cached_curve_ids_by_skin(self, skin: float) -> Tuple[int, ...]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT curve_id FROM statics WHERE ABS(Skin - ?) < 0.001 ORDER BY curve_id",
            (skin,),
        )
        return tuple(int(row[0]) for row in cursor.fetchall())

    @lru_cache(maxsize=2048)
    def _cached_reference_curve(self, curve_id: int) -> Tuple[Tuple[float, ...], Tuple[float, ...]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT X, Y FROM dynamics WHERE curve_id = ? ORDER BY elemIdx",
            (curve_id,),
        )
        rows = cursor.fetchall()
        if not rows:
            raise ValueError(f"No curve found with curve_id {curve_id}")
        x = tuple(float(row[0]) for row in rows)
        y = tuple(float(row[1]) for row in rows)
        return x, y

    @lru_cache(maxsize=2048)
    def _cached_static_params(self, curve_id: int) -> Tuple[float, float, float, float, int]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT Skin, L, W, h, N FROM statics WHERE curve_id = ?",
            (curve_id,),
        )
        row = cursor.fetchone()
        if row is None:
            raise ValueError(f"No static params found for curve_id {curve_id}")
        return (
            float(row["Skin"]),
            float(row["L"]),
            float(row["W"]),
            float(row["h"]),
            int(row["N"]),
        )
    
    def get_available_skins(self) -> List[float]:
        """Get list of available skin values."""
        return list(self._cached_available_skins())

    def get_available_N_values(self) -> List[int]:
        """Get sorted list of unique N values from database."""
        return list(self._cached_available_N_values())
    
    def get_curves_by_skin(self, skin: float) -> List[int]:
        """Get curve IDs for a specific skin value."""
        return list(self._cached_curve_ids_by_skin(round(float(skin), 6)))
    
    def get_reference_curve(self, curve_id: int) -> Tuple[np.ndarray, np.ndarray]:
        """Get reference curve by ID."""
        x, y = self._cached_reference_curve(int(curve_id))
        x = np.array(x, dtype=float)
        y = np.array(y, dtype=float)
        return x, y

    def get_static_params(self, curve_id: int) -> dict:
        """
        Получить статические параметры эталонной кривой.

        Returns:
            dict с ключами: Skin, L, W, h, N
        """
        skin, length, width, height, n_value = self._cached_static_params(int(curve_id))
        return {
            'Skin': skin,
            'L': length,
            'W': width,
            'h': height,
            'N': n_value,
        }

    def find_best_curve(
        self,
        skin: float,
        L_opt: float,
        N: Optional[int] = None,
        W: Optional[float] = None,
    ) -> Optional[Dict]:
        """
        Найти эталонную кривую, ближайшую по L, с фильтрацией по N и W.

        Args:
            skin: значение skin-фактора
            L_opt: целевая полудлина трещины
            N: фильтр по количеству трещин (опционально)
            W: фильтр по ширине трещины (опционально)

        Returns:
            dict с ключами curve_id, Skin, L, W, h, N, X, Y или None
        """
        curve_ids = self.get_curves_by_skin(skin)
        if not curve_ids:
            return None

        conn = self._get_connection()
        cursor = conn.cursor()

        best_curve = None
        best_diff = float('inf')

        for curve_id in curve_ids:
            cursor.execute(
                "SELECT Skin, L, W, h, N, aL FROM statics WHERE curve_id = ?",
                (curve_id,)
            )
            row = cursor.fetchone()
            if row is None:
                continue

            if N is not None and row['N'] != N:
                continue
            if W is not None and row['W'] != W:
                continue

            diff = abs(row['L'] - L_opt)
            if diff < best_diff:
                best_diff = diff
                best_curve = {
                    'curve_id': curve_id,
                    'Skin': row['Skin'],
                    'L': row['L'],
                    'W': row['W'],
                    'h': row['h'],
                    'N': row['N'],
                    'aL': row['aL'],
                }

        if best_curve:
            X, Y = self.get_reference_curve(best_curve['curve_id'])
            best_curve['X'] = X
            best_curve['Y'] = Y

        return best_curve

    def find_neighbor_curves(
        self,
        skin: float,
        L_opt: float,
        N: Optional[int] = None,
        W: Optional[float] = None,
    ) -> List[Dict]:
        """
        Найти соседние эталонные кривые (skin±1, skin±2), ближайшие по L.

        Args:
            skin: оптимальное значение skin-фактора
            L_opt: оптимальная полудлина трещины
            N: фильтр по количеству трещин (опционально)
            W: фильтр по ширине трещины (опционально)

        Returns:
            список dict с ключами curve_id, Skin, L, W, h, N, X, Y
        """
        neighbors = []

        available_skins = self.get_available_skins()
        if not available_skins:
            return neighbors

        skin_offsets = [-2, -1, 1, 2]
        target_skins = [skin + offset for offset in skin_offsets]

        conn = self._get_connection()
        cursor = conn.cursor()

        for target_skin in target_skins:
            query = "SELECT curve_id, Skin, L, W, h, N FROM statics WHERE ABS(Skin - ?) < 0.001"
            params: list = [target_skin]

            if N is not None:
                query += " AND N = ?"
                params.append(N)
            if W is not None:
                query += " AND W = ?"
                params.append(W)

            query += " ORDER BY ABS(L - ?) LIMIT 1"
            params.append(L_opt)

            cursor.execute(query, params)
            row = cursor.fetchone()
            if row:
                skin_already_added = any(n['Skin'] == row['Skin'] for n in neighbors)
                if not skin_already_added:
                    X, Y = self.get_reference_curve(row['curve_id'])
                    neighbors.append({
                        'curve_id': row['curve_id'],
                        'X': X,
                        'Y': Y,
                        'Skin': row['Skin'],
                        'L': row['L'],
                        'W': row['W'],
                        'h': row['h'],
                        'N': row['N'],
                    })

        return neighbors

"""
Reference repository module for HydraFracApp.
Handles access to reference curves stored in SQLite database.
Does not use pandas, returns numpy arrays, and does not contain solver logic.
"""

import sqlite3
import numpy as np
from typing import List, Tuple, Dict


class ReferenceRepository:
    """
    Class for accessing reference curves from SQLite database.
    Stores pre-calculated dimensionless curves parameterized by skin factor and geometry.
    """

    def __init__(self, db_path: str):
        """
        Initialize the repository with database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.connection = None

    def connect(self):
        """Establish connection to the database."""
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row  # Enable column access by name

    def disconnect(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None

    def get_available_skins(self) -> List[float]:
        """
        Get list of available skin factor values in the database.
        
        Returns:
            List of available skin values, sorted in ascending order
        """
        if not self.connection:
            self.connect()
        
        cursor = self.connection.cursor()
        cursor.execute("SELECT DISTINCT Skin FROM static ORDER BY Skin")
        rows = cursor.fetchall()
        
        skins = [row[0] for row in rows]
        return skins

    def get_curves_by_skin(self, skin: float, tolerance: float = 0.05) -> List[int]:
        """
        Get list of curve IDs that match the specified skin factor.
        
        Args:
            skin: Target skin factor value
            tolerance: Tolerance for skin value matching
            
        Returns:
            List of curve IDs matching the skin factor
        """
        if not self.connection:
            self.connect()
        
        cursor = self.connection.cursor()
        # Find curves with skin value within tolerance
        cursor.execute("""
            SELECT curve_id 
            FROM static 
            WHERE ABS(Skin - ?) <= ?
            ORDER BY ABS(Skin - ?)
        """, (skin, tolerance, skin))
        
        rows = cursor.fetchall()
        curve_ids = [row[0] for row in rows]
        
        return curve_ids

    def get_reference_curve(self, curve_id: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Retrieve reference X and Y values for a specific curve ID.
        
        Args:
            curve_id: ID of the reference curve to retrieve
            
        Returns:
            Tuple of (X array, Y array) as numpy arrays
        """
        if not self.connection:
            self.connect()
        
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT X, Y 
            FROM dynamic 
            WHERE curve_id = ?
            ORDER BY elemIdx
        """, (curve_id,))
        
        rows = cursor.fetchall()
        
        if not rows:
            raise ValueError(f"No reference curve found with curve_id {curve_id}")
        
        # Extract X and Y values
        x_values = []
        y_values = []
        for row in rows:
            x_values.append(row['X'])
            y_values.append(row['Y'])
        
        x_array = np.array(x_values)
        y_array = np.array(y_values)
        
        return x_array, y_array

    def get_static_metadata(self, curve_id: int) -> Dict:
        """
        Retrieve static metadata for a specific curve ID.
        
        Args:
            curve_id: ID of the curve to retrieve metadata for
            
        Returns:
            Dictionary containing static parameters for the curve
        """
        if not self.connection:
            self.connect()
        
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT Skin, h, N, W, L, aL, Q
            FROM static
            WHERE curve_id = ?
        """, (curve_id,))
        
        row = cursor.fetchone()
        
        if not row:
            raise ValueError(f"No metadata found for curve_id {curve_id}")
        
        # Convert Row object to dictionary
        metadata = dict(row)
        
        return metadata

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

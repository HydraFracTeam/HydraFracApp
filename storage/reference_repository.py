import sqlite3
import numpy as np
from typing import List

from config import settings
from core.models import ReferenceCurve, RawDynamicData, DimensionlessData
from schemas.static_params import StaticParams


class ReferenceCurveDBManager:
    """
    Минимальный менеджер доступа к эталонным кривым в SQLite.

    Используется только для чтения reference curves.
    Никакой solver-логики внутри нет.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn: sqlite3.Connection | None = None

    def connect(self):
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    # --------------------------------------------------
    # CURVE IDS
    # --------------------------------------------------

    def get_curve_ids_by_skin(self, skin: float) -> List[int]:
        """
        Возвращает список curve_id для заданного skin.
        """

        self.connect()

        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT curve_id
            FROM statics
            WHERE Skin = ?
            """,
            (skin,)
        )

        rows = cursor.fetchall()

        return [row["curve_id"] for row in rows]

    # --------------------------------------------------
    # SINGLE CURVE
    # --------------------------------------------------

    def load_reference_curve(self, curve_id: int) -> ReferenceCurve:
        """
        Загружает одну эталонную кривую.
        """

        self.connect()
        cursor = self.conn.cursor()

        # dynamic
        cursor.execute(
            """
            SELECT X, Y
            FROM dynamics
            WHERE curve_id = ?
            ORDER BY elemIdx
            """,
            (curve_id,)
        )

        rows = cursor.fetchall()

        X = np.array([r["X"] for r in rows], dtype=float)
        Y = np.array([r["Y"] for r in rows], dtype=float)

        # metadata
        cursor.execute(
            """
            SELECT Skin, h, N, W, L, Q
            FROM statics
            WHERE curve_id = ?
            """,
            (curve_id,)
        )

        meta = cursor.fetchone()

        static_params = StaticParams(
            Skin=meta["Skin"],
            W=meta["W"],
            h=meta["h"],
            Q_constant=meta["Q"],
            N=meta["N"],
            mu=settings.REF_mu,
            phi=settings.REF_phi,
            B=settings.REF_B,
            ct=settings.REF_ct,
            P0=settings.REF_P0,
        )

        return ReferenceCurve(
            dynamic_data=RawDynamicData(
                t=np.zeros_like(X),
                P=np.zeros_like(X),
                Q=np.zeros_like(X),
                is_Q_in_dynamic_input=True,
            ),
            dimensionless=DimensionlessData(
                X=X,
                Y=Y
            ),
            static_params=static_params
        )

    # --------------------------------------------------
    # MULTIPLE CURVES
    # --------------------------------------------------

    def get_reference_curves_by_skin(self, skin: float) -> List[ReferenceCurve]:
        """
        Возвращает все эталонные кривые для заданного skin.
        """
        curve_ids = self.get_curve_ids_by_skin(skin)

        curves: List[ReferenceCurve] = []

        for cid in curve_ids:
            curve = self.load_reference_curve(cid)
            curves.append(curve)

        return curves

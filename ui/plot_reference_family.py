import numpy as np

from PySide6.QtCore import Qt

from core.models import (
    DimensionlessData,
    ReferenceCurves,
    RuntimeSettings,
)

from ui.plot_xy import plot_xy


def _align_reference_x_to_factual(
    factual_x: np.ndarray | None,
    reference_x: np.ndarray,
) -> np.ndarray:
    """
    UI must mirror solver alignment.

    The solver compares curves after anchoring the factual curve to the
    reference by the first positive X. For visualization we keep the
    factual curve fixed and apply the inverse X-shift to each reference.
    """
    if factual_x is None or len(factual_x) == 0 or len(reference_x) == 0:
        return reference_x

    factual_pos = factual_x[np.isfinite(factual_x) & (factual_x > 0)]
    reference_pos = reference_x[np.isfinite(reference_x) & (reference_x > 0)]

    if len(factual_pos) == 0 or len(reference_pos) == 0:
        return reference_x

    shift = factual_pos[0] / reference_pos[0]
    return reference_x * shift


def plot_reference_family(
    plot,
    factual_dimensionless: DimensionlessData | None,
    reference_curves: ReferenceCurves | None,
    runtime_settings: RuntimeSettings | None = None,
):
    """
    Унифицированная отрисовка:
    - фактической кривой
    - эталонной
    - соседних

    Поддерживает сценарий,
    когда reference_curves отсутствуют.
    """

    plot.clear()

    # factual

    if factual_dimensionless is not None:
        factual_x = factual_dimensionless.X

        plot_xy(
            plot=plot,
            X=factual_x,
            Y=factual_dimensionless.Y,
            color=(255, 255, 255),
            width=2,
            name="Фактическая кривая",
            runtime_settings=runtime_settings,
            symbol_size=5,
        )

    # references 

    if reference_curves is None:
        return

    if reference_curves.main is not None:

        main = reference_curves.main

        skin_val = (
            main.static_params.Skin
            if main.static_params is not None
            else 0
        )

        aligned_main_x = _align_reference_x_to_factual(
            factual_x if factual_dimensionless is not None else None,
            main.dimensionless.X,
        )

        plot_xy(
            plot=plot,
            X=aligned_main_x,
            Y=main.dimensionless.Y,
            color=(220, 50, 47),
            width=3,
            style=Qt.PenStyle.DashLine,
            name=f"Эталонная кривая (S={skin_val:.1f})",
            runtime_settings=runtime_settings,
            symbol_size=3,
        )

    # neighbours
    if not reference_curves.neighbours:
        return

    neighbor_colors = {
        -2: (38, 139, 210),
        -1: (133, 153, 0),
         1: (181, 137, 0),
         2: (108, 113, 196),
    }

    for nb in reference_curves.neighbours:

        offset = nb.skin_offset

        color = neighbor_colors.get(
            offset,
            (120, 120, 120)
        )

        aligned_nb_x = _align_reference_x_to_factual(
            factual_x if factual_dimensionless is not None else None,
            nb.dimensionless.X,
        )

        plot_xy(
            plot=plot,
            X=aligned_nb_x,
            Y=nb.dimensionless.Y,
            color=color,
            width=1.5,
            style=Qt.PenStyle.DashLine,
            name=f"Сосед: Skin {offset:+d}",
            runtime_settings=runtime_settings,
            symbol_size=2,
        )

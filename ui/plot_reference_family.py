from PySide6.QtCore import Qt

from core.models import (
    DimensionlessData,
    ReferenceCurves,
    RuntimeSettings,
)

from ui.plot_xy import plot_xy


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

        plot_xy(
            plot=plot,
            X=factual_dimensionless.X,
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

        plot_xy(
            plot=plot,
            X=main.dimensionless.X,
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

        plot_xy(
            plot=plot,
            X=nb.dimensionless.X,
            Y=nb.dimensionless.Y,
            color=color,
            width=1.5,
            style=Qt.PenStyle.DashLine,
            name=f"Сосед: Skin {offset:+d}",
            runtime_settings=runtime_settings,
            symbol_size=2,
        )

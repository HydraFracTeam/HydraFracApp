# ui/plot_reference_family.py

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

    Reference-кривые отображаются
    со сдвигом относительно factual,
    чтобы стартовые точки совпадали.
    """

    plot.clear()

    # factual

    if factual_dimensionless is None:
        return

    xf = factual_dimensionless.X
    yf = factual_dimensionless.Y

    plot_xy(
        plot=plot,
        X=xf,
        Y=yf,
        color=(255, 255, 255),
        width=2,
        name="Фактическая кривая",
        runtime_settings=runtime_settings,
        symbol_size=5,
    )

    # no references

    if reference_curves is None:
        return

    if reference_curves.main is None:
        return

    # shift calculation

    main = reference_curves.main

    xr0 = main.dimensionless.X[1]
    yr0 = main.dimensionless.Y[1]

    xf0 = xf[1]
    yf0 = yf[1]
    dx = xf0 - xr0
    dy = yf0 - yr0

    # main reference

    skin_val = (
        main.static_params.Skin
        if main.static_params is not None
        else 0
    )

    xr = main.dimensionless.X + dx
    yr = main.dimensionless.Y + dy

    plot_xy(
        plot=plot,
        X=xr,
        Y=yr,
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

        xn = nb.dimensionless.X + dx
        yn = nb.dimensionless.Y + dy

        plot_xy(
            plot=plot,
            X=xn,
            Y=yn,
            color=color,
            width=1.5,
            style=Qt.PenStyle.DashLine,
            name=f"Сосед: Skin {offset:+d}",
            runtime_settings=runtime_settings,
            symbol_size=2,
        )

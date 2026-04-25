import numpy as np


DEFAULT_THRESHOLD = 5000


def lttb_downsample(
    x: np.ndarray,
    y: np.ndarray,
    threshold: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Largest Triangle Three Buckets (LTTB).

    Parameters
    ----------
    x, y
        Input series.

    threshold
        Number of points to keep.

    Returns
    -------
    x_ds
        Downsampled x

    y_ds
        Downsampled y

    indices
        Selected indices from original arrays
    """

    n = len(x)

    if n <= threshold or threshold < 3:
        idx = np.arange(n)
        return x, y, idx

    sampled = np.zeros(threshold, dtype=np.int64)

    sampled[0] = 0
    sampled[-1] = n - 1

    every = (n - 2) / (threshold - 2)

    a = 0

    for i in range(threshold - 2):

        # next bucket average

        avg_start = int(np.floor((i + 1) * every)) + 1
        avg_end = int(np.floor((i + 2) * every)) + 1

        if avg_end > n:
            avg_end = n

        if avg_start >= avg_end:
            avg_x = x[-1]
            avg_y = y[-1]
        else:
            avg_x = np.mean(x[avg_start:avg_end])
            avg_y = np.mean(y[avg_start:avg_end])

        # ---------------------------------
        # current bucket candidates
        # ---------------------------------

        range_start = int(np.floor(i * every)) + 1
        range_end = int(np.floor((i + 1) * every)) + 1

        if range_end > n:
            range_end = n

        ax = x[a]
        ay = y[a]

        bx = x[range_start:range_end]
        by = y[range_start:range_end]

        if len(bx) == 0:
            sampled[i + 1] = a
            continue

        # triangle areas
        areas = np.abs(
            (ax - avg_x) * (by - ay)
            -
            (ax - bx) * (avg_y - ay)
        )

        if len(areas) == 0:
            sampled[i + 1] = a
            continue

        selected = np.argmax(areas)

        a = range_start + selected
        sampled[i + 1] = a

    return x[sampled], y[sampled], sampled


def downsample_for_plot(
    x: np.ndarray,
    y: np.ndarray,
    interp_mask: np.ndarray | None = None,
    extrap_mask: np.ndarray | None = None,
    threshold: int = DEFAULT_THRESHOLD,
    log_space: bool = False,
):
    """
    Prepare data for plotting with optional LTTB downsampling.

    Supports:
      - ordinary time series
      - log-log XY curves
      - optional interpolation / extrapolation masks

    Returns
    -------
    x_ds
    y_ds
    interp_ds | None
    extrap_ds | None
    """

    finite = np.isfinite(x) & np.isfinite(y)

    if log_space:
        finite &= (x > 0) & (y > 0)

    x_valid = x[finite]
    y_valid = y[finite]

    interp_valid = (
        interp_mask[finite]
        if interp_mask is not None
        else None
    )

    extrap_valid = (
        extrap_mask[finite]
        if extrap_mask is not None
        else None
    )

    if len(x_valid) == 0:
        return (
            x_valid,
            y_valid,
            interp_valid,
            extrap_valid,
        )

    # No reduction needed
    if len(x_valid) <= threshold:
        return (
            x_valid,
            y_valid,
            interp_valid,
            extrap_valid,
        )

    # ---------------------------------
    # LTTB selection space
    # ---------------------------------

    if log_space:

        # numerical protection for tiny values
        eps = np.finfo(float).tiny

        x_work = np.log10(
            np.maximum(x_valid, eps)
        )

        y_work = np.log10(
            np.maximum(y_valid, eps)
        )

    else:
        x_work = x_valid
        y_work = y_valid

    _, _, selected_idx = lttb_downsample(
        x_work,
        y_work,
        threshold,
    )

    x_ds = x_valid[selected_idx]
    y_ds = y_valid[selected_idx]

    interp_ds = (
        interp_valid[selected_idx]
        if interp_valid is not None
        else None
    )

    extrap_ds = (
        extrap_valid[selected_idx]
        if extrap_valid is not None
        else None
    )

    return (
        x_ds,
        y_ds,
        interp_ds,
        extrap_ds,
    )

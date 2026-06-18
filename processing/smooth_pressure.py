import numpy as np
import torch
import torch.nn as nn
from scipy.interpolate import interp1d

from core.models import (
    ProcessingDynamicData,
    ProcessingOperationResult,
)


# Copy of DAE_Ablation class from autoencoders.py
class DAE_Ablation(nn.Module):
    """Гибкий DAE: настраиваются глубина, размер латентного вектора,
        dropout, функция активации."""
    def __init__(self, input_size=400, latent=50, depth=3,
                 dropout=0.0, act='relu'):
        super().__init__()
        act_map = {'relu': nn.ReLU, 'gelu': nn.GELU,
                   'leaky': lambda: nn.LeakyReLU(0.1)}
        Act = act_map[act]

        # Геометрически убывающие размеры слоёв
        sizes = [input_size]
        for i in range(depth):
            next_s = max(latent, sizes[-1] // 2)
            sizes.append(next_s)
        sizes[-1] = latent

        enc_layers, dec_layers = [], []
        for i in range(len(sizes) - 1):
            enc_layers += [nn.Linear(sizes[i], sizes[i+1]), Act()]
            if dropout > 0:
                enc_layers.append(nn.Dropout(dropout))
        for i in range(len(sizes) - 1, 0, -1):
            dec_layers += [nn.Linear(sizes[i], sizes[i-1])]
            if i > 1:
                dec_layers.append(Act())

        self.encoder = nn.Sequential(*enc_layers)
        self.decoder = nn.Sequential(*dec_layers)

    def forward(self, x):
        return self.decoder(self.encoder(x))


# Configuration for the autoencoder model
_N_POINTS = 400  # must match the training
_LATENT_DIM = _N_POINTS // 8
_MODEL_PATH = "saved_models/dae_baseline_state_dict.pt"

_dae_model = None  # will be loaded on first use


def _get_dae_model():
    global _dae_model
    if _dae_model is None:
        try:
            _dae_model = DAE_Ablation(input_size=_N_POINTS, latent=_LATENT_DIM, depth=3, dropout=0.0, act='relu')
            _dae_model.load_state_dict(torch.load(_MODEL_PATH, map_location='cpu'))
            _dae_model.eval()
        except Exception as e:
            raise RuntimeError(f"Failed to load autoencoder model from {_MODEL_PATH}: {e}") from e
    return _dae_model


def smooth_pressure(
    data: ProcessingDynamicData,
    window_length: int | None = None,
    polyorder: int = 3,
) -> ProcessingOperationResult:
    """
    Автоэнкодерное шумоподавление давления.
    Заменяет метод Савицкого-Голaye на автоэнкодер.
    Параметры window_length и polyorder оставлены для совместимости signature,
    но не используются.
    """
    if data is None:
        raise ValueError(
            "ProcessingDynamicData is None"
        )

    P = data.P
    t = data.t

    if P is None:
        raise ValueError(
            "Pressure array is None"
        )

    mask = np.isfinite(P) & (t > 1)

    if mask.sum() < 10:
        return ProcessingOperationResult(
            data=data,
            operation="pressure_denoising_autoencoder",
            details=[
                "Автоэнкодерное шумоподавление: недостаточно точек для обработки (<10)",
            ],
        )

    P_valid = P[mask]
    t_valid = t[mask]

    t_uniform = np.linspace(t_valid[0], t_valid[-1], _N_POINTS)
    interp_fn = interp1d(t_valid, P_valid, kind='linear',
                         bounds_error=False, fill_value='extrapolate')
    P_uniform = interp_fn(t_uniform).astype(np.float32)

    try:
        model = _get_dae_model()
    except Exception as e:
        return ProcessingOperationResult(
            data=data,
            operation="pressure_denoising_autoencoder",
            details=[
                f"Ошибка загрузки модели автоэнкодера: {e}",
            ],
        )

    with torch.no_grad():
        input_tensor = torch.from_numpy(P_uniform).unsqueeze(0).unsqueeze(0)
        denoised_tensor = model(input_tensor)
        P_denoised_uniform = denoised_tensor.squeeze().numpy()

    interp_fn_back = interp1d(t_uniform, P_denoised_uniform, kind='linear',
                              bounds_error=False, fill_value='extrapolate')
    P_denoised = interp_fn_back(t)

    P_result = P.copy()
    P_result[mask] = P_denoised[mask]

    data.P = P_result

    details = [
        (
            "Автоэнкодерное шумоподавление: "
            f"модель=dae_baseline, точки={_N_POINTS}"
        ),
    ]

    return ProcessingOperationResult(
        data=data,
        operation="pressure_denoising_autoencoder",
        details=details,
    )
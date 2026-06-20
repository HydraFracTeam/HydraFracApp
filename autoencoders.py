ABLATION_EPOCHS = 40
N_POINTS    = 400   # целевая длина 
LATENT_DIM = N_POINTS // 8   # ~100 для N_POINTS=800


def detect_curve_type(p: np.ndarray) -> str:
    """КСД — давление в среднем убывает, КВД — растёт."""
    slope = np.polyfit(np.arange(len(p)), p, 1)[0]
    return 'PDD' if slope < 0 else 'PBU'


def load_and_prepare(csv_path: str,
                     nf_levels=NF_LEVELS,
                     n_seeds=N_SEEDS,
                     n_points=N_POINTS,
                     rng_seed=42):
    """
    Читает reference.csv, интерполирует каждую кривую до n_points,
    накладывает реалистичный шум и возвращает словарь:
      {
        'PDD': (ideal, noisy, nf_arr),
        'PBU': (ideal, noisy, nf_arr),
      }
    """
    df = pd.read_csv(csv_path)
    rng = np.random.default_rng(rng_seed)

    results = {'PDD': ([], [], []), 'PBU': ([], [], [])}

    unique_curves = df[static_cols].drop_duplicates().reset_index(drop=True)
    print(f'Уникальных кривых в файле: {len(unique_curves)}')

    for _, row in unique_curves.iterrows():
        # Выбираем кривую
        mask = np.ones(len(df), dtype=bool)
        for col in static_cols:
            mask &= df[col] == row[col]
        curve = df[mask].sort_values('t')

        t_raw = curve['t'].values.astype(np.float64)
        p_raw = curve['P'].values.astype(np.float64)

        if len(t_raw) < 10:
            continue

        # Интерполируем до единой сетки n_points
        t_uniform = np.linspace(t_raw[0], t_raw[-1], n_points)
        interp    = interp1d(t_raw, p_raw, kind='linear',
                             bounds_error=False, fill_value='extrapolate')
        p_ideal   = interp(t_uniform).astype(np.float32)

        ctype = detect_curve_type(p_ideal)
        ideals, noisys, levels = results[ctype]

        for nf in nf_levels:
            for _ in range(n_seeds):
                p_noisy = add_realistic_noise(p_ideal, t_uniform, nf, rng)
                ideals.append(p_ideal.copy())
                noisys.append(p_noisy)
                levels.append(float(nf))

    # Конвертируем в numpy
    out = {}
    for ctype, (ideals, noisys, levels) in results.items():
        if len(ideals) == 0:
            print(f'Предупреждение: нет кривых типа {ctype}')
            continue
        out[ctype] = (
            np.array(ideals, dtype=np.float32),
            np.array(noisys, dtype=np.float32),
            np.array(levels, dtype=np.float32),
        )
        print(f'{ctype}: {len(ideals)} семплов  '
              f'(кривых: {len(ideals) // (len(nf_levels) * n_seeds)})')

    return out


# ── Запуск ──
dataset = load_and_prepare('reference.csv')

pdd_ideal, pdd_noisy, pdd_nf = dataset['PDD']
if 'PBU' in dataset:
    pbu_ideal, pbu_noisy, pbu_nf = dataset['PBU']
else:
    print('PBU не найдено — используем подвыборку PDD как заглушку')
    # Берём первые N кривых из PDD, имитируем КВД инверсией тренда
    n_stub = min(1000, len(pdd_ideal))
    idx = np.random.choice(len(pdd_ideal), n_stub, replace=False)
    pbu_ideal = pdd_ideal[idx][:, ::-1].copy()   # разворачиваем — давление растёт
    pbu_noisy = pdd_noisy[idx][:, ::-1].copy()
    pbu_nf    = pdd_nf[idx].copy()
    print(f'PBU заглушка: {pbu_ideal.shape}')

print(f'\nPDD: {pdd_ideal.shape}')
print(f'PBU: {pbu_ideal.shape}')

class DAE_Ablation(nn.Module):
    """Гибкий DAE: настраиваются глубина, размер латентного вектора,
       dropout, функция активации."""
    def __init__(self, input_size=1062, latent=133, depth=3,
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


class CAE_Ablation(nn.Module):
    def __init__(self, channels=(16, 32), dropout=0.2, act='relu'):
        super().__init__()
        act_map = {'relu': nn.ReLU, 'gelu': nn.GELU,
                   'leaky': lambda: nn.LeakyReLU(0.1)}
        Act = act_map[act]

        ch = [1] + list(channels)
        enc, dec = [], []
        for i in range(len(ch) - 1):
            enc += [nn.Conv1d(ch[i], ch[i+1], 3, stride=2, padding=1),
                    Act(), nn.Dropout(dropout)]
        ch_r = list(reversed(ch))
        for i in range(len(ch_r) - 1):
            dec += [nn.ConvTranspose1d(ch_r[i], ch_r[i+1], 3,
                                       stride=2, padding=1, output_padding=1)]
            if i < len(ch_r) - 2:
                dec.append(Act())

        self.encoder = nn.Sequential(*enc)
        self.decoder = nn.Sequential(*dec)
        self.refine   = nn.Conv1d(1, 1, kernel_size=7, padding=3)

    def forward(self, x):
        input_len = x.shape[-1]          # ← запоминаем
        if x.dim() == 2:
            x = x.unsqueeze(1)
        out = self.decoder(self.encoder(x))
        out = self.refine(out)
        return out[..., :input_len].squeeze(1)   # ← обрезаем


print('Ablation classes defined.')


        
 #------ train process -------
 
 # ============================================================
# EXPORT MODELS
# ============================================================

import torch
from pathlib import Path

EXPORT_DIR = Path("saved_models")
EXPORT_DIR.mkdir(exist_ok=True)

# ------------------------------------------------------------
# 1. Основная обученная модель DAE (если существует)
# ------------------------------------------------------------

if 'dae_pdd' in globals():

    torch.save(
        dae_pdd.state_dict(),
        EXPORT_DIR / "dae_pdd_state_dict.pt"
    )

    torch.save(
        dae_pdd,
        EXPORT_DIR / "dae_pdd_full_model.pt"
    )

    print("Saved: dae_pdd")

# ------------------------------------------------------------
# 2. DAE-baseline из абляций
# ------------------------------------------------------------

LATENT_DIM = N_POINTS // 8

dae_baseline = DAE_Ablation(
    input_size=N_POINTS,
    latent=LATENT_DIM,
    depth=3,
    dropout=0.0,
    act='relu'
)

dae_baseline, _ = train_model(
    dae_baseline,
    pdd_noisy,
    pdd_ideal,
    epochs=40,
    verbose=False
)

torch.save(
    dae_baseline.state_dict(),
    EXPORT_DIR / "dae_baseline_state_dict.pt"
)

torch.save(
    dae_baseline,
    EXPORT_DIR / "dae_baseline_full_model.pt"
)

print("Saved: DAE-baseline")

print("\nFiles:")
for f in EXPORT_DIR.iterdir():
    print(" ", f.name)
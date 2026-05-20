# Cache Performance And Validation

Этот документ фиксирует, что было оптимизировано, как это проверяется сейчас, и как человеку воспроизвести замеры на своей машине или между разными ветками.

## Что оптимизировано

### `core/reference_repo.py`

- оставлен глобальный кеш `skin_library`
- добавлены `lru_cache` для:
  - `get_available_skins()`
  - `get_available_N_values()`
  - `get_curves_by_skin()`
  - `get_reference_curve()`
  - `get_static_params()`
- при сборке `skin_library` сразу готовятся `numpy`-массивы `x/y`, чтобы не гонять повторно `DataFrame -> ndarray`

### `solver/solver_new.py`

- добавлен ручной кеш `self._sample_misfit_cache`
- повторные вызовы `_sample_misfit()` по одному и тому же sample больше не считают невязку заново
- solver переиспользует подготовленные `x/y`, а не повторяет `.values.astype(float)` на каждом проходе

### `session.py`

- добавлены ручные кеши для:
  - `recalculate_processing_dynamic_data()`
  - `recalculate_dimensionless()`
- ключ кеша строится по скалярам и содержимому массивов через `blake2b`

### `ui/table_data_builder.py`

- добавлен легкий кеш уже собранных `DataFrame` для таблиц размерных и безразмерных данных

## Какие тесты добавлены

### Корректность

Файл: `tests/test_cache_pipeline.py`

- повторяемость pipeline на хорошем файле `data_files/user_input.csv`
- сохранение NaN-масок и детерминизма на проблемном файле `data_files/user_input_empty.csv`
- hit-поведение `lru_cache` в `ReferenceRepository`
- переиспользование ручного кеша `solver._sample_misfit_cache`

### Производительность

Файл: `tests/test_cache_performance.py`

- измерение cold/warm времени для запросов `ReferenceRepository`
- измерение cold/warm времени для `solver._sample_misfit`
- замер стоимости полного pipeline на хорошем и проблемном CSV
- perf-тесты не только проверяют `warm < cold`, но и требуют минимальный выигрыш:
  - `ReferenceRepository`: не меньше `5x`
  - `solver._sample_misfit`: не меньше `20x`

## Вспомогательный benchmark-модуль

Файл: `utils/cache_benchmarks.py`

Что делает:

- собирает synthetic SQLite БД для повторяемых замеров
- считает медиану времени на вызов по нескольким раундам
- возвращает структурированный отчет по:
  - `repository_query`
  - `solver_sample_misfit`
  - `pipeline_good`
  - `pipeline_bad`

## CLI для человека

Файл: `scripts/benchmark_cache_perf.py`

### Запуск в markdown-формате

```bash
.venv/bin/python scripts/benchmark_cache_perf.py
```

### Запуск в JSON

```bash
.venv/bin/python scripts/benchmark_cache_perf.py --format json
```

## Как сравнить две ветки или два коммита

Ниже безопасный способ через `git worktree`, чтобы не трогать текущее рабочее дерево.

### 1. Создать два временных checkout

```bash
git worktree add /tmp/HydraFracApp_base <base-commit-or-branch>
git worktree add /tmp/HydraFracApp_target <target-commit-or-branch>
```

### 2. В каждом checkout подготовить окружение

Пример:

```bash
cd /tmp/HydraFracApp_base
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

То же для `/tmp/HydraFracApp_target`.

### 3. Запустить benchmark

```bash
/tmp/HydraFracApp_base/.venv/bin/python scripts/benchmark_cache_perf.py --format json
/tmp/HydraFracApp_target/.venv/bin/python scripts/benchmark_cache_perf.py --format json
```

### 4. Сравнить поля

Смотреть нужно в первую очередь на:

- `repository_query.speedup`
- `solver_sample_misfit.speedup`
- `pipeline_good.seconds_per_run`
- `pipeline_bad.seconds_per_run`

## Замеры, полученные в этой задаче

Сравнивались три точки:

- `ce8811c` — за два коммита до `optimized`
- `ca9e7a3` — `feat: vectorizing ops, simplifying algs and start of cache implements`
- текущее состояние рабочего дерева

### Медианное время на 1 вызов

| Metric | `ce8811c` | `ca9e7a3` | current |
|---|---:|---:|---:|
| pipeline good CSV | 0.009351 s | 0.009037 s | 0.008715 s |
| pipeline bad CSV | 0.011817 s | 0.012505 s | 0.011677 s |
| repo query cold | 0.006628 s | 0.005827 s | 0.006785 s |
| repo query warm | 0.002236 s | 0.002217 s | 0.000093 s |
| solver misfit cold | 0.002106 s | 0.002329 s | 0.003902 s |
| solver misfit warm | 0.002757 s | 0.002916 s | 0.000003 s |

## Интерпретация

- общий pipeline немного ускорился и на хорошем, и на проблемном CSV
- warm-path для `ReferenceRepository` ускорился кратно
- warm-path для `solver._sample_misfit` ускорился очень сильно
- cold-path для `solver._sample_misfit` стал тяжелее, потому что теперь платим цену за построение ключа кеша
- это нормальный обмен: одиночный вызов может стать немного дороже, но серии повторных вызовов становятся сильно дешевле

## Что запускать в CI или вручную

### Быстрая проверка корректности

```bash
.venv/bin/python -m pytest -q tests/test_cache_pipeline.py
```

### Быстрая проверка performance-гарантий

```bash
.venv/bin/python -m pytest -q tests/test_cache_performance.py
```

### Полный локальный прогон

```bash
.venv/bin/python -m pytest -q
```

import optuna
import numpy as np
import logging

logger = logging.getLogger(__name__)

# Suppress optuna logging
optuna.logging.set_verbosity(optuna.logging.WARNING)


def bayesian_fit(objective, bounds, n_trials=50, progress_callback=None):
    """
    Bayesian optimization using Optuna.
    
    Args:
        objective: Function to minimize
        bounds: Dictionary of parameter bounds {name: (low, high)}
        n_trials: Number of optimization trials
        progress_callback: Function(trial_num, params, value, best_value) for progress reporting
        
    Returns:
        best_params: Dictionary of best parameters found
        best_value: Best objective value
    """
    
    best_value_so_far = np.inf
    best_params_so_far = None

    def optuna_objective(trial):
        nonlocal best_value_so_far, best_params_so_far
        
        params = []
        param_dict = {}
        for name, (low, high) in bounds.items():
            val = trial.suggest_float(name, low, high, log=True)
            params.append(val)
            param_dict[name] = val
        
        value = objective(params)
        
        # Update best values
        if value < best_value_so_far:
            best_value_so_far = value
            best_params_so_far = param_dict.copy()
        
        # Call progress callback if provided
        if progress_callback:
            progress_callback(trial.number + 1, param_dict, value, best_value_so_far, best_params_so_far)
        
        return value

    # Create study without storage (in-memory only)
    study = optuna.create_study(
        direction="minimize",
        sampler=optuna.samplers.TPESampler(seed=42)
    )

    study.optimize(optuna_objective, n_trials=n_trials, show_progress_bar=False)

    return study.best_params, study.best_value

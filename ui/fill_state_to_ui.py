from core.app_state import AppState


def fill_static_params(ui, state: AppState):
    if state.static_params is None:
        return

    s = state.static_params

    ui.well_length_spinbox.setValue(s.W)
    ui.well_height_spinBox.setValue(s.h)
    ui.viscosity_spinBox.setValue(s.mu)
    ui.porosity_spinBox.setValue(s.phi)
    ui.volume_coef_spinBox.setValue(s.B)
    ui.compressibility_spinBox.setValue(s.ct)
    ui.frac_amount_combobox.setCurrentText(str(s.N))
    ui.reservoir_pressure_spinbox.setValue(s.P0)

    if s.Q_constant is not None:
        ui.debit_doubleSpinBox.setValue(s.Q_constant)


def fill_thresholds(ui, state: AppState):
    if state.optimize_thresholds is None:
        return

    t = state.optimize_thresholds

    ui.frac_length_min_border_doubleSpinBox.setValue(t.L_min)
    ui.frac_length_max_border_doubleSpinBox.setValue(t.L_max)
    ui.permeability_min_border_doubleSpinBox.setValue(t.k_min)
    ui.permeability_max_border_doubleSpinBox.setValue(t.k_max)


def fill_solver(ui, state: AppState):
    if state.solver_state is None:
        return

    s = state.solver_state

    ui.skin_result_spinbox.setValue(s.skin_current)
    ui.frac_length_result_spinbox.setValue(s.L_current)
    ui.permeability_result_spinbox.setValue(s.k_current)


def fill_state_to_ui(ui, state: AppState):
    fill_static_params(ui, state)
    fill_thresholds(ui, state)
    fill_solver(ui, state)

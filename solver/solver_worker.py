# solver_worker.py
from solver.solver_wrapper import Solver
from PySide6.QtCore import QObject, Signal
from core.app_state import AppState

class SolverWorker(QObject):

    finished = Signal(object)
    error = Signal(str)

    def __init__(self, app_state: AppState):
        super().__init__()
        self.app_state = app_state

    def run(self):
        try:
            solver = Solver()

            static_params = self.app_state.static_params
            thresholds = self.app_state.optimize_thresholds

            x = self.app_state.dimensionless.X
            y = self.app_state.dimensionless.Y

            results = solver.solve_top5(
                x_fact=x,
                y_fact=y,
                W_fixed=static_params.W,
                h_known=static_params.h,
                N_fixed=static_params.N,
                k_bounds=(thresholds.k_min, thresholds.k_max),
                L_bounds=(thresholds.L_min, thresholds.L_max),
            )

            self.finished.emit(results)

        except Exception as e:
            self.error.emit(str(e))

from solver import ReservoirSolver
from solver.library import build_skin_library

skin_library = build_skin_library(df)

solver = ReservoirSolver(skin_library)

result = solver.solve(x_fact, y_fact)

print(result)
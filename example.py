import matplotlib.pyplot as plt
import pandas as pd 


df = pd.read_csv("well_data_test_min.csv")
print(df.columns)

x_data = df["X"]
y_data = df["Y"]
print(x_data, y_data)

k = 5
phi = 0.2
ct = 4*10e-5

x_ideal = 0.00864*k*df["h"]*df["dP"]/(1*df["Q"])
y_ideal = df["Q"]*1*df['t']/(24*phi * ct * df['h']*df["L"]**2 * df["dP"])


# y_ideal_smooth = 0.5 * np.sqrt(x_ideal_smooth)  # пример для линейного течения

plt.figure(figsize=(10, 6))

# Фактические данные
plt.plot(x_data, y_data, 'b-', linewidth=2, label='Фактические данные')

# Идеальные расчетные точки из данных
# plt.scatter(x_ideal, y_data, color='red', s=30, alpha=0.7, label='Идеальные расчетные точки')

# Идеальная сглаженная кривая
plt.plot(x_ideal, y_ideal, 'g--', linewidth=2, label='Идеальная теоретическая кривая')

plt.legend()
plt.grid(True, which="both", ls="-", alpha=0.2)
plt.show()

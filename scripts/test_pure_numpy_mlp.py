import time
import numpy as np
from sklearn.neural_network import MLPRegressor

t0 = time.time()
# Synthesize data matching real dimensions
T_val, N = 4261, 14
T_test = 4981
X_val = np.random.randn(T_val * N, 5)
y_val = np.abs(np.random.randn(T_val * N)) * 50.0
X_test = np.random.randn(T_test * N, 5)

# Capacity-matched single-turbine MLP: (64, 64)
mlp = MLPRegressor(
    hidden_layer_sizes=(64, 64),
    activation="relu",
    solver="adam",
    max_iter=15,
    random_state=201,
    early_stopping=True,
    validation_fraction=0.2,
)
mlp.fit(X_val, y_val)
pred = mlp.predict(X_test)

# Pinball adjustment for 90th percentile if mean squared error loss is used:
# or fit directly with quantile pinball
print(f"MLP fit and predict in {time.time() - t0:.2f}s, pred mean={pred.mean():.2f}")

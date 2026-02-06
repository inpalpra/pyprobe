"""
Convergence test for scalar history chart feature.

Simulates gradient descent with exponential decay.
Probe the 'loss' variable to see the history chart in action.
"""

import time

# Simulate gradient descent convergence
loss = 100.0
learning_rate = 0.05
noise_scale = 0.5

print("Starting convergence simulation...")
print("Probe the 'loss' variable to see the history chart!")

for iteration in range(300):
    # Exponential decay with some noise
    loss = loss * (1 - learning_rate) + noise_scale * (0.5 - iteration / 600)
    
    # Slow down to observe in real-time
    time.sleep(0.03)

print(f"Final loss: {loss:.6f}")

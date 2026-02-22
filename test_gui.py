import numpy as np
import time

def main():
    while True:
        comp_data = np.exp(2j * np.pi * 10 * np.linspace(0, 1, 500)) + np.random.randn(500) * 0.1
        yield comp_data
        time.sleep(0.1)

if __name__ == "__main__":
    for _ in main():
        pass

import numpy as np
from pysoqpsktg.tx import precoder
from pysoqpsktg.tx import modulator

def main():
    n_bits = 1000
    sps = 16
    bits = np.random.randint(0, 2, n_bits)

    tx = modulator.SOQPSKModulator(samples_per_symbol=sps).transmit(bits)
    signal = tx.waveform
    real1000 = signal.real[:1000]
    real = signal.real

if __name__ == "__main__":
    main()
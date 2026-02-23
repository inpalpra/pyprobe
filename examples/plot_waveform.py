from rfutil.waveform import Waveform
import numpy as np


def main():
    y = np.concatenate([np.arange(51), np.arange(50)[::-1]])
    triangleWaveform = Waveform(
        x0=-0.5,
        dx=0.1,
        y=y,
    )

    triangleWaveformComplex = Waveform(
        x0=3.0,
        dx=0.2,
        y=y + 1j * y,
    )


if __name__ == "__main__":
    main()
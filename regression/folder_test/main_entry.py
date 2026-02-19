import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from helper import compute


def main():
    x = compute(5)


if __name__ == "__main__":
    main()

"""
Multi-probe same-line test script.
Tests that probing multiple variables on the same line works correctly.
"""

def main():
    a = 5
    b = 3
    x = a + b  # probe all three on this line
    return x

if __name__ == "__main__":
    main()

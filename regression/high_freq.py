"""
High frequency loop test script.
Tests that no data is lost in a fast loop.
"""

def main():
    for i in range(100):
        x = i  # probe x - should capture all 100 values
    return x

if __name__ == "__main__":
    main()

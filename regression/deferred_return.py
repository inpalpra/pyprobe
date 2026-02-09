"""
Deferred capture at function return test script.
Tests that LHS assignment is captured even when followed immediately by return.
"""

def foo():
    x = 42  # probe x here - assignment on last meaningful line
    return x

if __name__ == "__main__":
    result = foo()
    print(f"Result: {result}")

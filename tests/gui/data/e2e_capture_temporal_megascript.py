import sys
import time
def run_loop():
    def main():
        x = 10
        for i in range(3):
            x = x - 1
    
    
    if True:
        main()

def run_deferred_return():
    """
    Deferred capture at function return test script.
    Tests that LHS assignment is captured even when followed immediately by return.
    """
    
    def foo():
        x = 42  # probe x here - assignment on last meaningful line
        return x
    
    if True:
        result = foo()
        print(f"Result: {result}")

def run_high_freq():
    """
    High frequency loop test script.
    Tests that no data is lost in a fast loop.
    """
    
    def main():
        for i in range(100):
            x = i  # probe x - should capture all 100 values
        return x
    
    if True:
        main()

def run_multi_probe():
    """
    Multi-probe same-line test script.
    Tests that probing multiple variables on the same line works correctly.
    """
    
    def main():
        a = 5
        b = 3
        x = a + b  # probe all three on this line
        return x
    
    if True:
        main()

if __name__ == '__main__':
    run_loop()
    time.sleep(0.3)
    run_deferred_return()
    time.sleep(0.3)
    run_high_freq()
    time.sleep(0.3)
    run_multi_probe()
    time.sleep(0.3)

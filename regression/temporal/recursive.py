def countdown(n):
    x = n
    if n > 0:
        countdown(n - 1)
    return

def main():
    countdown(3)

if __name__ == "__main__":
    main()

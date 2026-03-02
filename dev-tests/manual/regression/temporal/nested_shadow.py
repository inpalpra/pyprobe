def main():
    x = 1
    def inner():
        x = 2
        return x
    inner()
    y = x
    return y

if __name__ == "__main__":
    main()

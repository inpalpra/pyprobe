def main():
    x = 1
    try:
        x = 2
        raise ValueError
        x = 999
    except:
        x = 3
    return x

if __name__ == "__main__":
    main()

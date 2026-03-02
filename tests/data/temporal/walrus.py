def main():
    data = [1, 2, 3, 4, 5]
    result = [y for x in data if (y := x * 2) > 4]
    return result

if __name__ == "__main__":
    main()

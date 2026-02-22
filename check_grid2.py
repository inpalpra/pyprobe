from PIL import Image

# Load test_grid_item.png
img = Image.open('test_grid_item.png')
width, height = img.size
pixels = img.load()

# Count pixels
yellow_count = 0
black_count = 0
white_count = 0

for x in range(width):
    for y in range(height):
        r, g, b, a = pixels[x, y]
        if r > 200 and g > 200 and b < 50:
            yellow_count += 1
        elif r < 10 and g < 10 and b < 10:
            black_count += 1
        elif r > 200 and g > 200 and b > 200:
            white_count += 1

print(f"Yellow pixels (curve): {yellow_count}")
print(f"Black pixels (bg): {black_count}")
print(f"White pixels (explicit grid item): {white_count}")

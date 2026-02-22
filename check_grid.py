from PIL import Image

# Load test_grid_z.png
img = Image.open('test_grid_z.png')
# Search for white/grey pixels inside the yellow block
# The yellow block is a huge dense sine wave covering (-10, 10) range in Y and (0, 10) in X
# Let's see if there are ANY pixels that are NOT yellow (or black) inside the plot bounding rectangle.
width, height = img.size
pixels = img.load()

# Count pixels
yellow_count = 0
grey_count = 0 
black_count = 0

for x in range(width):
    for y in range(height):
        r, g, b, a = pixels[x, y]
        if r > 200 and g > 200 and b < 50:
            yellow_count += 1
        elif r < 10 and g < 10 and b < 10:
            black_count += 1
        elif abs(r - g) < 10 and abs(r - b) < 10 and r > 50 and g > 50 and b > 50:
            grey_count += 1

print(f"Yellow pixels (curve): {yellow_count}")
print(f"Black pixels (bg): {black_count}")
print(f"Grey pixels (grid lines/axis): {grey_count}")

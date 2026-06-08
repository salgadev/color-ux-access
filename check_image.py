import base64

# Read the image
with open(r"examples\calendar.JPG", "rb") as f:
    data = f.read()

# Encode
image_base64 = base64.b64encode(data).decode('utf-8')
print(f"Length: {len(image_base64)}")
print(f"First 20 chars: {image_base64[:20]}")
print(f"Last 20 chars: {image_base64[-20:]}")
print(f"Ends with =? {image_base64.endswith('=')}")

# Decode back
decoded = base64.b64decode(image_base64)
print(f"Decoded length: {len(decoded)}")
print(f"Original length: {len(data)}")
print(f"Match: {decoded == data}")

# Check if it's a valid JPEG by looking at the first few bytes
# JPEG starts with FF D8 FF
if decoded[:2] == b'\xff\xd8':
    print("Starts with JPEG marker (FF D8)")
else:
    print(f"First 4 bytes: {decoded[:4].hex()}")
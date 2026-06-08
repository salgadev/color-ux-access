import base64
import requests
import json

# Path to image
image_path = r"examples\calendar.JPG"

# Read and encode image
with open(image_path, "rb") as f:
    image_base64 = base64.b64encode(f.read()).decode('utf-8')

# Endpoint URL
url = "https://narwall-tech--minicpm-vllm-inference.modal.run"

# Payload
payload = {
    "prompt": "Describe this image in detail, focusing on any accessibility issues related to color contrast.",
    "image_base64": image_base64
}

# Send request
try:
    response = requests.post(url, json=payload, timeout=180)
    print("Status code:", response.status_code)
    print("Response:", response.json())
except Exception as e:
    print("Error:", e)
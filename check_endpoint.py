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
response = requests.post(url, json=payload, timeout=120)
print("Status code:", response.status_code)
print("Response:", response.json())

# currently responds with
# OSError: You are trying to access a gated repo.
# Make sure to have access to it at https://huggingface.co/openbmb/MiniCPM-V-2_6.
# 401 Client Error. (Request ID: Root=1-6a265f5c-3ccab77d57cb789f49f81ed4;e344ee33-682e-4be5-9b80-0b5068598cf4)
#
# Cannot access gated repo for url https://huggingface.co/openbmb/MiniCPM-V-2_6/resolve/main/config.json.
# Access to model openbmb/MiniCPM-V-2_6 is restricted. You must have access to it and be authenticated to access it. Please log in.
# Runner failed with exception: OSError('You are trying to access a gated repo.\nMake sure to have access to it at https://huggingface.co/openbmb/MiniCPM-V-2_6.\n401 Client Error. (Request ID: Root=1-6a265f5c-3ccab77d57cb789f49f81ed4;e344ee33-682e-4be5-9b80-0b5068598cf4)\n\nCannot access gated repo for url https://huggingface.co/openbmb/MiniCPM-V-2_6/resolve/main/config.json.\nAccess to model openbmb/MiniCPM-V-2_6 is restricted. You must have access to it and be authenticated to access it. Please log in.')
import requests
import json

url = "https://narwall-tech--minicpm-vllm-inference.modal.run"

# Test with a simple text prompt
payload = {
    "prompt": "Hello, how are you?",
    "image_base64": ""
}

try:
    response = requests.post(url, json=payload, timeout=180)
    print("Status code:", response.status_code)
    print("Response:", response.json())
except Exception as e:
    print("Error:", e)
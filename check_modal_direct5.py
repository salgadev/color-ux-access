import modal
import base64

# Look up the class from the deployed app
MiniCPMVLLM = modal.Cls.from_name("minicpm-vllm", "MiniCPMVLLM")
# Instantiate and call method
model = MiniCPMVLLM()
# Read image
with open(r"examples\calendar.JPG", "rb") as f:
    image_data = f.read()
    image_base64 = base64.b64encode(image_data).decode('utf-8')
    print(f"Image base64 length: {len(image_base64)}")
    print(f"First 100 chars: {image_base64[:100]}")

print("Calling model.generate...")
result = model.generate.remote(
    prompt="Describe this image in detail, focusing on any accessibility issues related to color contrast.",
    image_base64=image_base64
)
print("Result:", result)
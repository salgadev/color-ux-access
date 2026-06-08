import modal
import base64

# Look up the deployed app
app = modal.App.lookup("minicpm-vllm", create_if_missing=False)
# Get the class
MiniCPMVLLM = app.cls.MiniCPMVLLM
# Instantiate and call method
model = MiniCPMVLLM()
# Read image
with open(r"examples\calendar.JPG", "rb") as f:
    image_base64 = base64.b64encode(f.read()).decode('utf-8')

print("Calling model.generate...")
result = model.generate.remote(
    prompt="Describe this image in detail, focusing on any accessibility issues related to color contrast.",
    image_base64=image_base64
)
print("Result:", result)
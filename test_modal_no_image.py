import modal

# Look up the class from the deployed app
MiniCPMVLLM = modal.Cls.from_name("minicpm-vllm", "MiniCPMVLLM")
# Instantiate and call method
model = MiniCPMVLLM()

print("Calling model.generate with no image...")
result = model.generate.remote(
    prompt="Hello, how are you?",
    image_base64=None
)
print("Result:", result)
import modal

app = modal.App("minicpm-vllm")

vllm_image = (
    modal.Image.from_registry("nvidia/cuda:12.4.1-devel-ubuntu22.04", add_python="3.11")
    .pip_install("vllm>=0.6.4")
    .pip_install("transformers>=4.45.0")
    .pip_install("accelerate>=0.34.0")
    .pip_install("torch>=2.4.0")
)

MODEL_ID = "openbmb/MiniCPM-V-4.6"


@app.cls(
    gpu="A100",
    scaledown_window=300,
    timeout=600,
    image=vllm_image,
    secrets=[modal.Secret.from_name("hf-token-minicpm")],
)
class MiniCPMVLLM:
    @modal.enter()
    def start_engine(self):
        from vllm import LLM
        from vllm.sampling_params import SamplingParams
        import os

        hf_token = os.getenv("HF_TOKEN")
        if hf_token:
            print("HF_TOKEN is set")
        else:
            print("HF_TOKEN is NOT set")

        self.llm = LLM(
            model=MODEL_ID,
            trust_remote_code=True,
            max_model_len=4096,
            dtype="bfloat16",
            tensor_parallel_size=1,
            limit_mm_per_prompt={"image": 1},
        )
        self.default_sampling_params = SamplingParams(
            temperature=0.7,
            max_tokens=2048,
            top_p=0.95,
        )

    @modal.method()
    async def generate(self, prompt: str, image_base64: str = None) -> str:
        # Build message content
        content = []
        if image_base64:
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}})
        content.append({"type": "text", "text": prompt})

        messages = [
            {
                "role": "user",
                "content": content,
            }
        ]

        outputs = self.llm.chat(
            messages=messages,
            sampling_params=self.default_sampling_params,
        )
        return outputs[0].outputs[0].text


@app.function(image=vllm_image)
@modal.fastapi_endpoint(method="POST")
async def inference(request: dict):
    prompt = request.get("prompt", "")
    image_b64 = request.get("image_base64")
    infer = MiniCPMVLLM()
    result = infer.generate.remote(prompt, image_b64)
    return {"response": result}
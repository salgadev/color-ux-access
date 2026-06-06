"""
VLM inference using llama.cpp for local GGUF model loading.
This provides an alternative to the Hugging Face API approach.
"""

import os
import base64
from io import BytesIO
from typing import Optional
from PIL import Image

# Try to import llama_cpp, provide fallback if not available
try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    Llama = None  # type: ignore


def load_llama_model(
    model_path: str = "./llama-3.2-11b-vision-gguf/Llama-3.2-11B-Vision-Instruct.Q4_K_M.gguf",
    mmproj_path: str = "./llama-3.2-11b-vision-gguf/Llama-3.2-11B-Vision-Instruct-mmproj.f16.gguf",
    n_ctx: int = 2048,
    n_batch: int = 512,
    n_threads: Optional[int] = None,
    verbose: bool = False,
) -> Optional[Llama]:
    """
    Load a Llama 3.2 Vision model via llama.cpp.
    
    Args:
        model_path: Path to the GGUF model file
        mmproj_path: Path to the multimodal projection file
        n_ctx: Context size
        n_batch: Batch size for prompt processing
        n_threads: Number of CPU threads to use (None for auto)
        verbose: Enable verbose logging
        
    Returns:
        Loaded Llama model instance or None if failed
    """
    if not LLAMA_CPP_AVAILABLE:
        print("llama-cpp-python not available. Install with: pip install llama-cpp-python")
        return None
        
    try:
        # Check if model files exist
        if not os.path.exists(model_path):
            print(f"Model file not found: {model_path}")
            return None
            
        if not os.path.exists(mmproj_path):
            print(f"Multimodal projection file not found: {mmproj_path}")
            return None
            
        # Initialize the model with vision capabilities
        model = Llama(
            model_path=model_path,
            mmproj_path=mmproj_path,
            n_ctx=n_ctx,
            n_batch=n_batch,
            n_threads=n_threads,
            verbose=verbose,
            logits_all=False,
            # Vision models may need specific parameters
            # Refer to llama.cpp documentation for vision model loading
        )
        print(f"Successfully loaded Llama 3.2 Vision model from {model_path}")
        return model
    except Exception as e:
        print(f"Failed to load Llama model: {e}")
        return None


def analyze_image_with_llama(
    model: Llama,
    image: Image.Image,
    prompt: str = "Describe any color accessibility issues in this image, such as low contrast or color-dependent elements.",
    max_tokens: int = 512,
    temperature: float = 0.1,
) -> str:
    """
    Analyze an image using a locally loaded Llama 3.2 Vision model via llama.cpp.
    
    Args:
        model: Loaded Llama model instance
        image: PIL Image to analyze
        prompt: Prompt for the VLM
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature
        
    Returns:
        VLM analysis result as string
    """
    if model is None:
        return "Error: Model not loaded"
        
    try:
        # Convert image to base64 for inclusion in prompt
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        # Construct the prompt with image placeholder
        # For llama.cpp vision models, we need to use the proper format
        # This may vary based on the specific model and llama.cpp version
        
        # For now, we'll use a simple approach - in practice, you'd need to
        # consult the llama.cpp documentation for vision model prompting
        full_prompt = f"{prompt}\n\n![image](data:image/png;base64,{img_base64})"
        
        # Generate response
        response = model(
            full_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=["\n\n", "<|end|>", "<|im_end|>"]
        )
        
        # Extract text from response
        if isinstance(response, dict) and "choices" in response:
            return response["choices"][0]["text"].strip()
        else:
            return str(response)
    except Exception as e:
        print(f"Error during image analysis: {e}")
        return f"Error: {e}"
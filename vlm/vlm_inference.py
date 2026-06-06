import torch
from PIL import Image
import argparse
import os
import json
import base64
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def load_model_api(model_name="CohereLabs/aya-vision-32b:fastest", token=None):
    """
    Set up the OpenAI client for the Hugging Face Router API.
    """
    print(f"Setting up API client for model: {model_name}")
    if token is None:
        token = os.getenv("HF_TOKEN")
    if token is None:
        raise ValueError("HF_TOKEN environment variable not set and no token provided.")
    client = OpenAI(
        base_url="https://router.huggingface.co/v1",
        api_key=token
    )
    return client, model_name

def analyze_image_api(client_model_tuple, image_path, prompt):
    """
    Analyze an image using the VLM via Hugging Face Router API (OpenAI compatible).
    """
    client, model_name = client_model_tuple
    image = Image.open(image_path).convert("RGB")
    # Convert image to base64
    from io import BytesIO
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    # Create chat completion with vision
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_base64}"
                        }
                    }
                ]
            }
        ],
        max_tokens=512,
        temperature=0.1
    )
    return response.choices[0].message.content

def main():
    parser = argparse.ArgumentParser(description="Analyze image with VLM for accessibility via API")
    parser.add_argument("image_path", help="Path to the image file")
    parser.add_argument("--prompt", default="Analyze this webpage screenshot for color accessibility issues. Describe any problems with contrast, color-dependent elements, and readability for users with color vision deficiency. Provide specific remediation suggestions.", help="Prompt for the VLM")
    parser.add_argument("--model", default="CohereLabs/aya-vision-32b:fastest", help="Model name or path")
    parser.add_argument("--token", help="Hugging Face API token (optional, can also set HF_TOKEN env var)")
    args = parser.parse_args()
    
    try:
        client_model = load_model_api(args.model, args.token)
        result = analyze_image_api(client_model, args.image_path, args.prompt)
        print(result)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()

import base64
import os
import argparse

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

base_url = 'https://api.rhymes.ai/v1/'
aria_api_key = os.environ['ARIA_API_KEY']
allegro_api_key = os.environ['ALLEGRO_API_KEY']

client = OpenAI(
    base_url=base_url,
    api_key=aria_api_key
)

def image_to_base64(image_path):
    """
    Converts an image to a base64-encoded string.

    Args:
        image_path (str): The path to the image file.

    Returns:
        str: The base64-encoded string of the image.
    """
    try:
        with open(image_path, "rb") as image_file:
            base64_string = base64.b64encode(image_file.read()).decode("utf-8")
        return base64_string
    except FileNotFoundError:
        return "Image file not found. Please check the path."
    except Exception as e:
        return f"An error occurred: {str(e)}"

def aria_image_analysis(base64_image, question):
    response = client.chat.completions.create(
            model="aria",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        },
                        {
                            "type": "text",
                            "text": f"<image>\n{question}"
                        }
                    ]
                }
            ],
            stream=False,
            temperature=0.6,
            max_tokens=1024,
            top_p=1,
            stop=["<|im_end|>"]
    )
    return response.choices[0].message.content

def main():  
    parser = argparse.ArgumentParser(description="Ask ARIA about an image")
    parser.add_argument("image_path", help="Path to the image file")
    parser.add_argument("question", help="Question to ask ARIA about the image")
    args = parser.parse_args()   
    
    image_path = args.image_path    
    question = args.question

    base64_image = image_to_base64(image_path)
    result = aria_image_analysis(base64_image, question)
    print(result)
    

if __name__ == "__main__":
    main()
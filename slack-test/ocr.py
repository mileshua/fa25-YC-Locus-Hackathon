from PIL import Image
import anthropic
from dotenv import load_dotenv
import json
import base64
from io import BytesIO

load_dotenv()

client = anthropic.Anthropic()

f = open("prompts/ocr.txt", "r")
prompt = f.read()
f.close()

def extract_text(file_path):
    image = Image.open(file_path)
    
    # Convert image to base64 properly
    buffer = BytesIO()
    # Ensure we have a format, default to PNG if unknown
    format = image.format if image.format else 'PNG'
    image.save(buffer, format=format)
    image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    resp = client.messages.create(
        model="claude-haiku-4-5",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/{extension}".format(extension=format.lower()),
                            "data": image_base64
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ],
        max_tokens=4096
    )
    print(resp.content[0].text)
    return json.loads(resp.content[0].text)
import os
import logging
import sys
from openai import OpenAI
import json
import base64
from PIL import Image, ImageDraw, ImageFont
import ast
from pdf2image import convert_from_path
from find_label_coords import find_label_coords

"""Example script usage: python3 src/document_creation/write_pdf.py SAMPLE_PNG_PATH SAMPLE_JSON"""
SAMPLE_PNG_PATH = "./W-2.png"

SAMPLE_JSON = '{ "Employee social security number": "000-11-2222", \
                "Employer identification number": "999-888-777", \
                "Wages, tips, other compensation": "64000" }'

MODEL_NAME = "gpt-4o-mini" # configure API key by running: `export OPENAI_API_KEY="your_api_key_here"`

# Vertical padding to adjust text placement (negative value moves text down)
Y_PADDING = 20

SYSTEM_PROMPT = f"""You are a helpful, form-filling assistant. The user will provide you with an 
image of a form, as well as a list of fields that need to be filled in along with their label 
pixel coordinates on the page. For each field, your task is to identify the x,y pixel coordinates 
of the blank corresponding to that field, where the user could insert a left-justified answer. 
To do this, first determine where the answer should be written relative to the question 
(i.e. above, right, below). Then, consider the size of the image, and then choose coordinates which
are far enough in the right direction such that there is a sizeable gap between the label and answer.
Lastly, output your response as a list of tuples (no additional text), where the 
n-th tuple contains the x,y pixel coordinates of the top-left corner of the n-th field's blank.
For example, if the user input was: 'name: (x1, y1), EIN: (x2, y2), cell: (x3, y3)' respectively, 
your output should be of the exact format: [(new_x1, new_y1),(new_x2, new_y2),(new_x3, new_y3)]."""


def encode_image(img_path):
    """"Create a base64 encoding of an image file."""
    with open(img_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")
    

def process_image_path(form_path):
    """Take a path to an image or pdf and convert it into a list of png pages."""
    image_paths = []
    if not os.path.exists(form_path):
        logging.error(f"File not found at path: {form_path}")
        return None
    ext = os.path.splitext(form_path)[1].lower()
    if ext in [".png", ".jpg", ".jpeg"]:
        image_paths.append(form_path)
    elif ext == ".pdf":
        # Create tmp directory if it doesn't exist
        tmp_dir = './tmp'
        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir)
            
        pages = convert_from_path(form_path, 500)
        for count, page in enumerate(pages):
            pagename = f'{tmp_dir}/page{count}.png'
            page.save(pagename, 'PNG')
            image_paths.append(pagename)
    else:
        logging.error(f"Unsupported file format: {ext}")
        return None
    return image_paths


def overlay_text(img_path, text_list, coordinates_list, 
                 font_path="./fonts/arial/arial.ttf", font_size=20):
    """"Overlay text on an image at the given coordinates."""
    image = Image.open(img_path)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
    
    for text, (x, y) in zip(text_list, coordinates_list):
        # Convert dictionaries or other non-string types to string
        if isinstance(text, dict):
            # Format the dictionary as a string, e.g., "Readdle, 795 Folsom Street, 94107"
            formatted_text = ", ".join([str(v) for v in text.values()])
            text = formatted_text
        elif not isinstance(text, (str, bytes)):
            text = str(text)
            
        # Apply Y_PADDING to move text down
        adjusted_y = y + Y_PADDING
        draw.text((x, adjusted_y), text, fill="black", font=font)
    
    return image


def populate_form(fields, label_coords, img_path):
    """
    populate_form takes in a JSON string of fields and their values, a list of label coordinates, 
    and an image path. The function calls an LLM to identify the coordinates of the blanks where 
    the values should be filled in, and then calls overlay_text() to create a filled pdf.
    """
    client = OpenAI()
    base64_image = encode_image(img_path)
    
    img = Image.open(img_path)
    x, y = img.size

    # Format LLM query
    message = ""
    for field in label_coords:
        message += field + ": " + str(label_coords[field]) + ", "
        
    # Call model to identify coordinates of blanks
    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT + f"The size of this image is {x} pixels wide by {y} pixels long"},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": message},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                ]
            }
        ]
    )
    blank_coords = ast.literal_eval(completion.choices[0].message.content)
    return overlay_text(img_path, list(fields.values()), blank_coords, font_size=(10 + (x / 1000) * 10))


def main():
    args = sys.argv[1:]
    if len(args) != 2:
        print("Please provide the pathname of the folder holding the empty form to be filled and a JSON of all the fields and their values.")
        return

    # form to be filled out
    form_path = args[0]
    image_paths = process_image_path(form_path)
    if not image_paths:
        logging.error(f"File not found at path: {form_path}")
        return None

    # json with all form fields and answers
    try:
        # Try to parse the JSON string directly
        json_string = json.loads(args[1])
    except (json.JSONDecodeError, TypeError):
        # If direct parsing fails, check if it's a file path
        json_path = args[1]
        if os.path.exists(json_path):
            with open(json_path) as file:
                json_string = json.load(file)
        else:
            logging.error(f"Could not parse JSON or find file at path: {json_path}")
            return

    output = []
    output_path = form_path[0:form_path.rfind('.')] + "_filled.pdf"

    # Make sure tmp directory exists for cleanup at the end
    tmp_dir = './tmp'
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)

    for img_path in image_paths:
        lost_keys, label_coords = find_label_coords(img_path, list(json_string.keys()))
        fields = json_string.copy()
        for key in lost_keys:
            if key in fields:
                del fields[key]
        page = populate_form(fields, label_coords, img_path)
        output.append(page)

    if len(output) > 1: # if there are multiple pages, combine them as one pdf
        output[0].save(output_path, save_all=True, append_images=output[1:])
    else:
        output[0].save(output_path)

    # Check if tmp directory exists before attempting to clean it
    if os.path.exists("tmp"):
        for file in os.listdir("tmp"):
            try:
                os.remove(os.path.join("tmp", file))
            except Exception as e:
                logging.error(f"Failed to remove temporary file: {e}")

if __name__ == "__main__":
    main()
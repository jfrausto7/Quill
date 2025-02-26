import sys
import numpy as np
from openai import OpenAI
import json
import base64
from PIL import Image, ImageDraw, ImageFont
import ast
from find_label_coords import find_label_coords
from rag import quill_rag
import subprocess

"""Example script usage: python3 src/document_creation/write_pdf.py SAMPLE_PNG_PATH SAMPLE_JSON"""
SAMPLE_PNG_PATH = "./W-2.png"

SAMPLE_JSON = '{ "Employee social security number": "000-11-2222", \
                "Employer identification number": "999-888-777", \
                "Wages, tips, other compensation": "64000" }'

MODEL_NAME = "gpt-4o-mini"

SYSTEM_PROMPT = """You are a helpful, form-filling assistant. The user will provide you with an 
image of a form, as well as a list of fields that need to be filled in along with their label 
pixel coordinates on the page. For each field, your task is to identify the x,y pixel coordinates 
of the blank corresponding to that field, where the user could insert a left-justified answer. 
To do this, first determine where the answer should be written relative to the question 
(i.e. above, right, below). Then, determine how many coordinates in this direction the answer 
should begin. Lastly, output your response as a list of tuples (no additional text), where the 
n-th tuple contains the x,y pixel coordinates of the top-left corner of the n-th field's blank. 
For example, if the user input was: 'name: (100, 100), EIN: (200, 200), cell: (300, 300)' 
respectively, your output should be of the exact format: [(120, 100),(220, 200),(300, 330)]."""


def encode_image(img_path):
    """"Create a base64 encoding of an image file."""
    with open(img_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")
    

def overlay_text(img_path, output_img_path, text_list, coordinates_list, 
                 font_path="./fonts/arial/arial.ttf", font_size=20):
    """"Overlay text on an image at the given coordinates."""
    image = Image.open(img_path)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
    
    for text, (x, y) in zip(text_list, coordinates_list):
        draw.text((x, y), text, fill="black", font=font)
    
    image.save(output_img_path)


def write_pdf(jsonString, label_coords, img_path, output_img_path):
    """
    write_pdf takes in a JSON string of fields and their values, a list of label coordinates, 
    and an image path. The function calls an LLM to identify the coordinates of the blanks where 
    the values should be filled in, and then calls overlay_text() to create a filled pdf.
    """
    client = OpenAI()
    fields = json.loads(jsonString)
    base64_image = encode_image(img_path)

    # Format LLM query
    message = ""
    for i, field in enumerate(fields.keys()):
        message += field + ": " + str(label_coords[i]) + ", "
        
    # Call model to identify coordinates of blanks
    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
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
    overlay_text(img_path, output_img_path, list(fields.values()), blank_coords)


def main():
    args = sys.argv[1:]
    if len(args) != 2:
        print("Please provide the pathname of the empty form image to be filled and a JSON of all \
              the fields and their values.")
        return

    # form to be filled out
    img_path = args[0]
    output_img_path = img_path.split(".")[0] + "_filled.png"
    jsonString = args[1]

    # question = f"""You are a helpful, form-filling assistant. The user will provide you with an 
    #             image of a blank or partially-filled form. For each field, your task is to generate
    #             the answer to the question, 'What is the value of the field?' and add the field label
    #             and its answer as a key-value pair to a .JSON file. If the answer to the field is
    #             not already in the form, check if you can find the answer in the chat history.
    #             Lastly, output your answer as a .JSON file with no additional text. For example,
    #             your output should be of the exact format: {SAMPLE_JSON}"""

    # command = f"quill_rag_v2.py --mode query --document {img_path} --question {question} --chat-history {chat_history}"
    # print(command.split())
    # subprocess.call("../rag_v2/quill_rag_v2.py", shell=True)
    # sys.argv = command.split()
    
    # Find the locations of each element in the JSON.
    label_coords = find_label_coords(img_path, jsonString)

    write_pdf(jsonString, label_coords, img_path, output_img_path)

if __name__ == "__main__":
    main()

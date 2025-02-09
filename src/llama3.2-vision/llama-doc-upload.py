import sys
import ollama
from spire.pdf.common import *
from spire.pdf import *

# System prompt defining the assistant's persona and behavior
SYSTEM_PROMPT = """You are Quill, a friendly and efficient document assistant. 

IMPORTANT RULES:
1. Review the document and extract the fields
2. Output each field as a line in a .yaml file format

Example good response:
"---
 first name: Jane
 last name: Doe
 SSN: 012-34-5678
 "

RESPOND TO THE USER'S MESSAGE:
"""
USER_PROMPT = "I need help extracting the fields from this document:"

def PDF2IMG(doc):
    # Create a PdfDocument object
    pdf = PdfDocument()
    # Load a PDF document
    pdf.LoadFromFile(doc)
    imgs = []

    # Loop through the pages in the document
    for i in range(pdf.Pages.Count):
        # Save each page as a PNG image
        fileName = "tmp/img-{0:d}.png".format(i)
        imgs.append(fileName)
        with pdf.SaveAsImage(i) as imageS:
            imageS.Save(fileName)

    # Close the PdfDocument object
    pdf.Close()
    return imgs

def extract_fields(doc):
    imgs = PDF2IMG(doc)
    response = ollama.chat(
        'llama3.2-vision:11b',
        messages=[
            {
                'role': 'system',
                'content': SYSTEM_PROMPT
            },
            {
                'role': 'user',
                'content': USER_PROMPT,
                'images': imgs
            },
        ],
        options={
            'temperature': 0.7,
            'top_k': 50,
            'top_p': 0.9,
            'max_tokens': 100
        }
    )
    
    # Print response
    print(response['message']['content'])

if __name__ == "__main__":
    if len(sys.argv) > 1:
        doc = sys.argv[1]
        print(doc)
        extract_fields(doc)
import sys
import ollama
from spire.pdf.common import *
from spire.pdf import *

# System prompt defining the assistant's persona and behavior
SYSTEM_PROMPT = """You are Quill, a friendly and efficient document assistant. 

IMPORTANT RULES:
1. Keep responses SHORT and FOCUSED - no more than 2-3 sentences
2. Never talk about your own development or features
3. Respond directly to the user's question or need
4. If you're unsure, ask a simple clarifying question
5. Stay focused on helping with documents and forms

Example good response:
"I'd love to help with your tax form! 😊 Which section are you stuck on?"

Example bad response:
"Let me think about how I should approach this task... I need to consider the various aspects..."

RESPOND TO THE USER'S MESSAGE:
"""

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

def send_query(message):
    # imgs = [PDF2IMG(doc) for doc in docs]
    response = ollama.chat(
        'llama3.2-vision:11b',
        messages=[
            {
                'role': 'system',
                'content': SYSTEM_PROMPT
            },
            {
                'role': 'user',
                'content': message,
                # 'images': imgs
            },
        ],
        options={
            'temperature': 0.7,
            'top_k': 50,
            'top_p': 0.9,
            'max_tokens': 100
        }
    )
    
    # Clean and print the response
    print(response['message']['content'])

if __name__ == "__main__":
    if len(sys.argv) > 1:
        message = sys.argv[1]
        send_query(message)
    else:
        print("Please provide a message as a command-line argument.")
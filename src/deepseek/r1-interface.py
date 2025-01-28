import sys
import ollama

"""
To use this module, you will need to have downloaded ollama and 
run the following command:
    ollama pull deepseek-r1:1.5b

To query the model, run the following command:
    python3 src/deepseek/R1-interface.py "[INPUT MESSAGE HERE]"
"""

model = 'deepseek-r1:1.5b' #Change to whatever model you are using.

def send_query(message):
    response = ollama.chat(model, messages=[
        {
            'role': 'user',
            'content': message,
        },
    ])
    print(response['message']['content'])

if __name__ == "__main__":
    message = sys.argv[1]
    send_query(message)
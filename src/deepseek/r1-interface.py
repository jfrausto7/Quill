import sys
import ollama

# System prompt defining the assistant's persona and behavior
SYSTEM_PROMPT = """You are DocuFill, a friendly and efficient document assistant. 

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

def clean_response(text):
    # Remove <userStyle>Normal</userStyle> tag
    text = text.replace('<userStyle>Normal</userStyle>', '')
    
    # Find all content after </think> tags
    think_splits = text.split('</think>')
    if len(think_splits) > 1:
        # Return everything after the last </think> tag
        return think_splits[-1].strip()
    
    # Remove quotation marks at the beginning and end
    text = text.strip('"')  # This removes both single and double quotes
    
    return text.strip()

def send_query(message):
    response = ollama.chat(
        'deepseek-r1:1.5b',
        messages=[
            {
                'role': 'system',
                'content': ""
            },
            {
                'role': 'user',
                'content': SYSTEM_PROMPT + message,
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
    cleaned_response = clean_response(response['message']['content'])
    print(cleaned_response)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        message = sys.argv[1]
        send_query(message)
    else:
        print("Please provide a message as a command-line argument.")
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
import json
import re
import logging
import sys

def extract_key_value_info(url):
    """
    Use o3-mini to visit a URL and extract key-value pairs from an online form.
    Returns the data in JSON format.
    """
    llm = ChatOpenAI(model_name="o3-mini", temperature=0)

    prompt = (
        f"Visit this URL: {url}\n\n"
        "Extract all form fields from this web page. Look for input fields, labels, and their placeholder values. "
        "For each field, identify the label (like 'Name:', 'Address:', 'Date:') and any default or example values. "
        "Format your response ONLY as a clean JSON object with the field labels as keys. "
        "For example: {\"Name\": \"John Doe\", \"Email\": \"example@email.com\"}"
    )

    result = llm.invoke(input=prompt)
    logging.info("Key-value information extracted from document.")

    try:
        info = json.loads(result.content.strip())
    except Exception as e:
        logging.error("Failed to parse JSON output from LLM: " + str(e))
        info = {}
    return info

def main():
    """
    Main function to handle URL extraction from chat input.
    This function would be called by your chat interface when a user sends a URL.
    """
    if len(sys.argv) > 1:
        user_message = " ".join(sys.argv[1:])
        url_match = re.search(r'https?://\S+', user_message)
        
        if url_match:
            url = url_match.group(0)
            logging.info(f"Processing URL: {url}")
            
            # Extract form data from the URL
            result = extract_form_data_from_url(url)
            print(json.dumps({"result": result}))
        else:
            print(json.dumps({"error": "No URL found in the message"}))

if __name__ == "__main__":
    main()




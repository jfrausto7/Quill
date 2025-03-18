import time
import re
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pytesseract
from PIL import Image
import openai
import pdfplumber

openai.api_key = OPEN_AI_KEY
SURVEY_MONKEY = "https://www.surveymonkey.com/r/WYCHJ7P"
GOOGLE_FORM = "https://forms.gle/KBzBQVgSYcA28BKj6"
TYPE_FORM = "https://form.typeform.com/to/mwWgVg29"
JOT_FORM = "https://form.jotform.com/250685379571166"
HTML_FORM = "http://localhost:63342/discord_agent/discord_agent/src/form1.html?_ijt=nrbddslpgrdho7hpi8lgi0t9h5"

def clean_field_name(text):
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    return text

def extract_text_from_pdf(pdf_path):
    extracted_data = {}
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                lines = text.split("\n")
                for line in lines:
                    if ":" in line:
                        key, value = line.split(":", 1)
                        extracted_data[clean_field_name(key)] = value.strip()
    return extracted_data

def extract_form_fields(form_url):
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    driver.get(form_url)
    time.sleep(3)

    page_height = driver.execute_script("return document.body.scrollHeight")
    viewport_height = driver.execute_script("return window.innerHeight")
    scroll_step = int(viewport_height * 0.5)
    extracted_text = ""
    for current_position in range(0, page_height, scroll_step):
        driver.execute_script(f"window.scrollTo(0, {current_position})")
        time.sleep(1.5)
        screenshot_path = f"screenshot_{current_position}.png"
        driver.save_screenshot(screenshot_path)
        image = Image.open(screenshot_path)
        extracted_text += pytesseract.image_to_string(image) + "\n"
    driver.quit()
    field_patterns = [
        r"(name|full name|first name|last name)",
        r"(Address|address|city|state|zip code|postal code|country)",
        r"(phone number|mobile number|contact number)",
        r"(email|email address)",
        r"(date of birth|dob|birthdate)",
        r"(social security number|ssn)",
        r"(university|Stanford ID|ID|college)",
        r"(major|Major|Field of study)",
        r"(grade|class)",
        r"(Injury Description|Injury)",
        r"(E-Signature|Signature)",
    ]
    fields = []
    seen_fields = set()
    for line in extracted_text.split("\n"):
        line = clean_field_name(line)
        if any(re.search(pattern, line, re.IGNORECASE) for pattern in field_patterns) and line not in seen_fields:
            fields.append(line)
            seen_fields.add(line)
    return fields

def chat_with_user_gpt(form_fields):
    user_responses = {}
    print("Hello! This is Quill, your form-filling assistant. Let's get started!")
    system_prompt = """
    You are Quill, a web-based form filling assistant. Your job is to respond conversationally, prompting the user for each required field.
    For example, if provided to you was "Name", you should respond with "I need your full name, please."
    Another example would be if you are provided "Address", you would say something like "Please give me your address."
    Keep it SIMILAR not EXACTLY the same as the examples I provided to you. GET CREATIVE.
    Keep responses brief and natural, and DO NOT attempt to fill in the fields yourself.
    If you are given fields in an order I expect the order to be the same when responding to the user.
    You need to keep in mind that you FILL ANY TYPE OF FORM. So it's important you adopt the character based on the context of the form.
    Some forms can be surveys, some can be medical forms, or even interest forms.
    """
    conversation_history = [{"role": "system", "content": system_prompt}]
    for field in form_fields:
        user_prompt = f"Field detected: {field}"
        conversation_history.append({"role": "user", "content": user_prompt})
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=conversation_history
        )
        assistant_reply = response["choices"][0]["message"]["content"].strip()
        print(assistant_reply)
        user_input = input("Your response: ")
        user_responses[field] = user_input
        conversation_history.append({"role": "assistant", "content": assistant_reply})
        conversation_history.append({"role": "user", "content": user_input})
    return user_responses

def fill_and_submit_form(form_url, user_responses):
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    driver.get(form_url)
    time.sleep(3)
    input_fields = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.XPATH, "//input[contains(@aria-label, 'Your answer') or @type='text']"))
    )
    for field, value in user_responses.items():
        for input_element in input_fields:
            try:
                input_element.send_keys(value)
                input_fields.remove(input_element)
                break
            except Exception:
                continue
    while True:
        try:
            next_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Next')]")                           ))
            next_button.click()
            time.sleep(2)
        except Exception:
            break
    try:
        submit_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Submit')]")))
        submit_button.click()
        print("Form successfully submitted!")
    except Exception:
        print("Submit button not found.")
    driver.quit()

if __name__ == "__main__":
    form_url = input("Please enter the form URL: ")
    fields = extract_form_fields(form_url)
    responses = chat_with_user_gpt(fields)
    fill_and_submit_form(form_url, responses)

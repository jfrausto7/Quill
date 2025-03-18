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
import fitz

openai.api_key = OPEN_AI_KEY
SURVEY_MONKEY = "https://www.surveymonkey.com/r/WYCHJ7P"
GOOGLE_FORM = "https://forms.gle/KBzBQVgSYcA28BKj6"
TYPE_FORM = "https://form.typeform.com/to/mwWgVg29"
JOT_FORM = "https://form.jotform.com/250685379571166"
HTML_FORM = "http://localhost:63342/discord_agent/discord_agent/src/form1.html?_ijt=nrbddslpgrdho7hpi8lgi0t9h5"

def clean_field_name(text):
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def parse_extracted_text(text):
    extracted_data = {}
    field_mappings = {
        "Last Name": "last_name",
        "First Name": "first_name",
        "Middle Initial": "middle_initial",
        "Date of Birth": "dob",
        "Gender": "gender",
        "Marital Status": "marital_status",
        "Patient Address": "address",
        "City": "city",
        "State": "state",
        "Zip Code": "zip_code",
        "Home Telephone": "home_phone",
        "Cell Telephone": "cell_phone",
        "Primary Care Physician": "pcp",
        "Physician Address": "pcp_address",
        "Insurance Provider": "insurance_provider",
        "Policy Number": "policy_number",
        "Social Security Number": "ssn",
        "Occupation": "occupation",
        "Company Name": "company_name",
        "Company Address": "company_address"
    }

    lines = text.split("\n")
    for i in range(len(lines) - 1):
        field_name = clean_field_name(lines[i])
        field_value = clean_field_name(lines[i + 1])
        for key in field_mappings:
            if key in field_name:
                extracted_data[field_mappings[key]] = field_value
                break  # Ensures only the first matching field is used

    return extracted_data

def extract_text_from_screenshot(image_path):
    image = Image.open(image_path)
    raw_text = pytesseract.image_to_string(image)
    return parse_extracted_text(raw_text)

def extract_form_fields(form_url):
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    driver.get(form_url)
    time.sleep(3)
    extracted_text = ""
    page_height = driver.execute_script("return document.body.scrollHeight")
    viewport_height = driver.execute_script("return window.innerHeight")
    scroll_step = int(viewport_height * 0.5)
    for current_position in range(0, page_height, scroll_step):
        driver.execute_script(f"window.scrollTo(0, {current_position})")
        time.sleep(1.5)
        screenshot_path = f"screenshot_{current_position}.png"
        driver.save_screenshot(screenshot_path)
        image = Image.open(screenshot_path)
        extracted_text += pytesseract.image_to_string(image) + "\n"
    driver.quit()
    fields = set(clean_field_name(line) for line in extracted_text.split("\n") if line.strip())
    return list(fields)

def review_and_edit_data(extracted_screenshot_data, extracted_form_fields):
    print("Extracted data from Screenshot:")
    for field, value in extracted_screenshot_data.items():
        print(f"{field}: {value}")
    system_prompt = """
    You are Quill, an AI web-based form-filling assistant. You store and recall extracted user data like a database.
    Your role is to confirm and refine user information before submitting it to a web form. You will be given two types of information:
    1. The first being the field extracted from the web-based form.
    2. The second being the field & respective information extracted from the PDF for.

    It is your job to match fields. THEY MIGHT NOT BE EXACTLY THE SAME. THEY MIGHT BE SIMILAR SO USE LOGIC.

    After concluding that the two fields are similar, confirm with the user because REMEMBER THAT PEOPLE MIGHT NEED TO UPDATE INFORMATION FROM TIME TO TIME.

    If you go by all the fields that match, and there are some that do not, ask the user to provide the information.
    Be conversational. Remember- you are a web-based form-filling assistant.

    If you find fields like 'Your answer', 'Google Forms', 'Never submit passwords through Google Forms.' -> IGNORE THEM AND DON'T BRING THEM UP IN CONVERSATION. 
    These are watermarks and other random information extracted form the web-based form that is not relevant.
    """
    conversation_history = [{"role": "system", "content": system_prompt}]
    for field in extracted_form_fields:
        if field in extracted_screenshot_data:
            user_prompt = f" This here is a blank field from the web-based form: {field} Here are chunks of information from the user (these fields & responses were gotten from another form the user filled: {extracted_screenshot_data[field]}"
        else:
            user_prompt = f"The web form requires '{field}', but it was not found in the screenshot. What should we enter?"
        conversation_history.append({"role": "user", "content": user_prompt})
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=conversation_history
        )
        assistant_reply = response["choices"][0]["message"]["content"].strip()
        print(assistant_reply)
        user_input = input(f"Your response for {field}: ")
        extracted_screenshot_data[field] = user_input
    return extracted_screenshot_data

def fill_and_submit_form(form_url, user_responses):
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    driver.get(form_url)
    time.sleep(3)
    input_fields = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.XPATH, "//input[contains(@aria-label, 'Your answer') or @type='text']")))
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
            next_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Next')]")))
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
    print("Welcome to Quill, your AI-powered form-filling assistant!")
    form_url = input("Please enter the URL of the web-based form: ")
    image_path = input("Please enter the path to the screenshot containing the filled-out form: ")
    extracted_screenshot_data = extract_text_from_screenshot(image_path)
    extracted_form_fields = extract_form_fields(form_url)
    reviewed_data = review_and_edit_data(extracted_screenshot_data, extracted_form_fields)
    fill_and_submit_form(form_url, reviewed_data)
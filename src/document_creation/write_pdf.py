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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

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

    # Format LLM query with more detailed guidance
    message = "Here are the field labels and their coordinates that need to be filled:\n"
    for field in label_coords:
        message += field + ": " + str(label_coords[field]) + "\n"
    
    # Add explicit examples to help the model understand the expected format
    message += "\nPlease provide the coordinates where I should place text for each field as a Python list of (x, y) tuples.\n"
    message += "For example, if I have 3 fields, return something like: [(100, 200), (150, 300), (200, 400)]"
    
    # Enhanced system prompt
    enhanced_system_prompt = f"""You are a helpful, form-filling assistant. The user will provide you with an 
image of a form, as well as a list of fields that need to be filled in along with their label 
pixel coordinates on the page. For each field, your task is to identify the x,y pixel coordinates 
of the blank corresponding to that field, where the user could insert a left-justified answer. 
To do this, first determine where the answer should be written relative to the question 
(i.e. above, right, below). Then, consider the size of the image ({x} x {y} pixels), and then choose coordinates which
are far enough in the right direction such that there is a sizeable gap between the label and answer.

You MUST output your response as a list of tuples in Python syntax, where the 
n-th tuple contains the x,y pixel coordinates of the top-left corner of the n-th field's blank.
Do not include any explanatory text - ONLY output the list of tuples.

For example, if the input is 3 fields with their label coordinates, your output should be 
exactly in this format: [(x1, y1), (x2, y2), (x3, y3)]"""

    # Call model to identify coordinates of blanks
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": enhanced_system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": message},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                    ]
                }
            ]
        )
        
        # Extract and validate the response
        response_content = completion.choices[0].message.content.strip()
        
        # Check if the response starts with a square bracket (indicating a list)
        if not response_content.startswith('[') or not response_content.endswith(']'):
            # The response isn't in the correct format, generate fallback coordinates
            logging.warning(f"LLM did not return valid coordinates. Response: {response_content}")
            # Generate simple fallback coordinates based on label positions
            blank_coords = generate_fallback_coordinates(fields, label_coords)
        else:
            try:
                # Try to parse the response as a Python list of tuples
                blank_coords = ast.literal_eval(response_content)
                # Validate that we got enough coordinates
                if len(blank_coords) != len(fields):
                    logging.warning(f"Expected {len(fields)} coordinates but got {len(blank_coords)}. Using fallback.")
                    blank_coords = generate_fallback_coordinates(fields, label_coords)
            except (SyntaxError, ValueError) as e:
                logging.error(f"Failed to parse LLM response: {e}")
                blank_coords = generate_fallback_coordinates(fields, label_coords)
        
        return overlay_text(img_path, list(fields.values()), blank_coords, font_size=(10 + (x / 1000) * 10))
    
    except Exception as e:
        logging.error(f"Error in populate_form: {e}")
        # Generate fallback coordinates and continue
        blank_coords = generate_fallback_coordinates(fields, label_coords)
        return overlay_text(img_path, list(fields.values()), blank_coords, font_size=(10 + (x / 1000) * 10))


def generate_fallback_coordinates(fields, label_coords):
    """
    Generate fallback coordinates when LLM response fails.
    Places text to the right of each label.
    """
    blank_coords = []
    
    for field_name in fields:
        if field_name in label_coords:
            # Get label coordinates
            label_x, label_y = label_coords[field_name]
            # Position the text 200 pixels to the right and at the same y position
            blank_coords.append((label_x + 200, label_y))
        else:
            # If no label coordinates, use a default position
            blank_coords.append((300, 300))
    
    return blank_coords


def normalize_and_match_fields(json_data, label_coords):
    """
    Normalize field names from JSON data and match them with form fields.
    Handles field name variations and nested structures.
    
    Args:
        json_data (dict): The original JSON data with field values
        label_coords (dict): Field names found in the form with their coordinates
        
    Returns:
        dict: Matched fields with their values
    """

    # Create a normalized mapping of common field variations
    field_variations = {
        # Personal information
        "patientfirstname": ["first name", "firstname", "fname", "patient first name", "patient name"],
        "patientmiddleinitial": ["middle initial", "mi", "middle name", "patient middle initial"],
        "patientlastname": ["last name", "lastname", "lname", "patient last name", "surname"],
        "dateofbirth": ["dob", "birth date", "birthdate", "date of birth", "patient date of birth"],
        "gender": ["sex", "patient gender", "patient sex"],
        "race": ["ethnicity", "patient race", "patient ethnicity"],
        "maritalstatus": ["marital status", "status", "patient marital status"],
        "language": ["preferred language", "patient language", "language preference"],
        "socialsecuritynumber": ["ssn", "social security no", "social security number", "social security"],
        
        # Contact information
        "addressstreet": ["address", "street address", "street", "patient address", "patient address street"],
        "addresscity": ["city", "town", "patient city", "patient address city"],
        "addressstate": ["state", "province", "patient state", "patient address state"],
        "addresszipcode": ["zip", "zipcode", "zip code", "postal code", "patient zip", "patient address zip code"],
        "hometelephone": ["home phone", "telephone", "home tel", "home telephone"],
        "worktelephone": ["work phone", "business phone", "office phone", "work tel", "work telephone"],
        "celltelephone": ["cell phone", "mobile", "mobile phone", "cell", "cellular", "cell telephone"],
        "email": ["email address", "e-mail", "patient email"],
        
        # Emergency contact
        "emergencycontactname": ["emergency contact", "emergency name", "emergency contact person", "emergency contact name"],
        "emergencycontactrelationship": ["emergency relationship", "emergency contact relation", "relation to patient", "emergency contact relationship"],
        "emergencycontacttelephone": ["emergency phone", "emergency tel", "emergency contact phone", "emergency contact tel", "emergency contact telephone"],
        
        # Employment
        "employmentstatus": ["employment", "employment type", "work status"],
        "occupation": ["job", "position", "profession"],
        "industry": ["sector", "field", "business sector"],
        "companyname": ["employer", "company", "business name", "place of employment", "employer name"],
        "companyaddressstreet": ["company street", "employer address", "business address", "company address", "company address street"],
        "companyaddresscity": ["company city", "employer city", "business city", "company address city"],
        "companyaddressstate": ["company state", "employer state", "business state", "company address state"],
        "companyaddresszipcode": ["company zip", "employer zip", "business zip", "company address zip", "company address zip code"],
        
        # Insurance
        "insuranceprovider": ["insurance company", "insurer", "insurance", "insurance carrier", "insurance provider"],
        "patientgroupnumber": ["group number", "group no", "group", "insurance group", "patient group number"],
        "policynumber": ["policy no", "policy", "insurance policy", "policy id", "policy number"],
        "patientsubscriberid": ["subscriber id", "member id", "insurance id", "patient id", "patient subscriber id"],
        "typeofinsurance": ["insurance type", "plan type", "coverage type", "type of insurance"],
        "insurancetelephone": ["insurance phone", "insurer phone", "insurance tel", "insurance telephone"],
        "subscribername": ["subscriber", "policy holder", "insurance holder", "subscriber name"],
        
        # Medical
        "allergies": ["patient allergies", "known allergies", "allergy list", "allergic to"],
        "reasonforvisit": ["chief complaint", "reason", "symptoms", "reason for visit"],
        "primarycarephysicianname": ["pcp", "primary doctor", "doctor name", "physician", "primary care physician", "primary care physician name"],
        "primarycarephysicianaddressstreet": ["doctor address", "physician address", "pcp address", "primary care physician address", "primary care physician address street"],
        "primarycarephysicianaddresscity": ["doctor city", "physician city", "pcp city", "primary care physician address city"],
        "primarycarephysicianaddressstate": ["doctor state", "physician state", "pcp state", "primary care physician address state"],
        "primarycarephysicianaddresszipcode": ["doctor zip", "physician zip", "pcp zip", "primary care physician address zip", "primary care physician address zip code"],
        
        # Appointment
        "desiredappointmentdate1": ["appointment date", "appt date", "preferred date", "desired appointment date"],
        "desiredappointmenttime1": ["appointment time", "appt time", "preferred time", "desired appointment time"],
        "desiredappointmentdate2": ["alternate date", "second date", "backup date", "desired appointment date 2"],
        "desiredappointmenttime2": ["alternate time", "second time", "backup time", "desired appointment time 2"],
        
        # Signature fields
        "date": ["signature date", "today's date", "form date"],
        "signature": ["patient signature", "signature of patient", "signature"]
    }
    
    # Create normalized versions of label_coords keys
    normalized_labels = {}
    for label in label_coords:
        # Remove punctuation, lowercase, and remove whitespace
        normalized = ''.join(e.lower() for e in label if e.isalnum())
        normalized_labels[normalized] = label
    
    # Function to flatten nested JSON
    def flatten_json(nested_json, prefix=''):
        flattened = {}
        for key, value in nested_json.items():
            if isinstance(value, dict):
                # For nested dicts, recurse with prefix
                nested_flat = flatten_json(value, f"{prefix}{key}_")
                flattened.update(nested_flat)
            else:
                # For non-nested values, add with prefix
                flattened[f"{prefix}{key}"] = value
        return flattened
    
    # Flatten the JSON data
    flattened_json = flatten_json(json_data)
    
    # Create a mapping between normalized JSON keys and their original values
    json_mapping = {}
    for key, value in flattened_json.items():
        normalized_key = ''.join(e.lower() for e in key if e.isalnum())
        json_mapping[normalized_key] = value
    
    # Match fields using the variation mappings
    matched_fields = {}
    
    # First try direct matches
    for json_key_norm, value in json_mapping.items():
        if json_key_norm in normalized_labels:
            original_label = normalized_labels[json_key_norm]
            matched_fields[original_label] = value
    
    # Then try finding variations
    for standard_key, variations in field_variations.items():
        # If we already have this field, skip
        if any(standard_key == ''.join(e.lower() for e in k if e.isalnum()) for k in matched_fields):
            continue
            
        # Try to find a match using variations
        for variation in variations:
            variation_norm = ''.join(e.lower() for e in variation if e.isalnum())
            
            # Check if this variation exists in the form labels
            if variation_norm in normalized_labels:
                original_label = normalized_labels[variation_norm]
                
                # Find the value in the JSON data
                if standard_key in json_mapping:
                    matched_fields[original_label] = json_mapping[standard_key]
                    break
                    
                # Try variations in the JSON too
                for json_key_norm, value in json_mapping.items():
                    if json_key_norm == standard_key or json_key_norm in variations:
                        matched_fields[original_label] = value
                        break
    
    # Add any unmatched but recognized form fields with empty values
    for label in label_coords:
        if label not in matched_fields:
            matched_fields[label] = ""
    
    return matched_fields


def process_nested_json(json_data):
    """
    Process nested JSON and convert it to a flat structure.
    
    Args:
        json_data (dict): The JSON data that may contain nested objects
        
    Returns:
        dict: Flattened JSON with concatenated keys
    """
    flat_json = {}
    
    def flatten(data, prefix=""):
        for key, value in data.items():
            if isinstance(value, dict):
                # Recursively flatten nested dictionaries
                flatten(value, f"{prefix}{key} ")
            else:
                # Add to flat dictionary with concatenated key
                flat_json[f"{prefix}{key}"] = value
    
    flatten(json_data)
    return flat_json


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

    # Flatten nested JSON structure if present
    flattened_json = process_nested_json(json_string)
    
    output = []
    output_path = form_path[0:form_path.rfind('.')] + "_filled.pdf"

    # Make sure tmp directory exists for cleanup at the end
    tmp_dir = './tmp'
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)

    for img_path in image_paths:
        # Get label coordinates - pass the flattened keys
        lost_keys, label_coords = find_label_coords(img_path, list(flattened_json.keys()))
        
        # Apply the advanced field matching logic
        matched_fields = normalize_and_match_fields(flattened_json, label_coords)
        
        # Log the matching results for debugging
        logging.info(f"Original fields: {len(flattened_json)} fields")
        logging.info(f"Form labels found: {len(label_coords)} labels")
        logging.info(f"Matched fields: {len(matched_fields)} matches")
        
        # Use the matched fields instead of filtering the original fields
        page = populate_form(matched_fields, label_coords, img_path)
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
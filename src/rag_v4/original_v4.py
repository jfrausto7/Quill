import os
import json
import re
import logging
import argparse
from langchain_community.document_loaders import (
    UnstructuredWordDocumentLoader,
)
from langchain.document_loaders.csv_loader import CSVLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_core.documents import Document
import pytesseract
from PIL import Image
from pdf2image import convert_from_path

# Configure logging
logging.basicConfig(level=logging.INFO)

# Constants
DOC_PATH1 = "Demo_Input_Form_filled.pdf"   # For ingest mode (can be any supported file)
DOC_PATH2 = "Demo_Input_Form.pdf"     # For query mode (new form to be processed)
DOC_PATH3 = "update_info.png"     # For update mode (update user_info.json via a document)
VECTOR_DB_DIR = "vector_db"
MODEL_NAME = "llama3.2-vision:11b"
EMBEDDING_MODEL = "nomic-embed-text"
USER_INFO_JSON = "user_info.json"


## Helper Functions

def flatten_json(data, parent_key='', sep='_'):
    """Recursively flatten a nested JSON object into a flat dictionary."""
    items = []
    for key, value in data.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key
        if isinstance(value, dict):
            items.extend(flatten_json(value, new_key, sep=sep).items())
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    items.extend(flatten_json(item, f"{new_key}{sep}{i}", sep=sep).items())
                else:
                    items.append((f"{new_key}{sep}{i}", item))
        else:
            items.append((new_key, value))
    return dict(items)

def extract_text_from_pdf_with_ocr(file_path):
    """Extract text from PDF using OCR."""
    logging.info(f"Processing PDF with OCR: {file_path}")
    
    try:
        # Convert PDF pages to images
        images = convert_from_path(file_path, dpi=900)
        logging.info(f"Converted PDF to {len(images)} images")
        
        # Process each page with OCR
        text_content = []
        for i, image in enumerate(images):
            logging.info(f"Processing page {i+1} with OCR")
            text = pytesseract.image_to_string(image)
            text_content.append(text)
            
        # Combine all pages with page numbers for context
        full_text = ""
        for i, text in enumerate(text_content):
            full_text += f"\n--- Page {i+1} ---\n{text}\n"
            
        return [Document(page_content=full_text, metadata={"source": file_path})]
        
    except Exception as e:
        logging.error(f"Error processing PDF with OCR: {e}")
        return None

def ingest_file(file_path):
    """Load a file (PDF, Word, image, or CSV) with OCR for PDFs."""
    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        return None
        
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == ".pdf":
        # Use OCR for PDF processing instead of UnstructuredPDFLoader
        data = extract_text_from_pdf_with_ocr(file_path)
    elif ext in [".doc", ".docx"]:
        loader = UnstructuredWordDocumentLoader(file_path=file_path)
        data = loader.load()
    elif ext in [".png", ".jpg", ".jpeg"]:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        data = [Document(page_content=text, metadata={"source": file_path})]
    elif ext == ".csv":
        loader = CSVLoader(file_path=file_path)
        data = loader.load()
    else:
        logging.error(f"Unsupported file format: {ext}")
        return None
        
    logging.info(f"File {file_path} loaded successfully.")
    return data

def split_documents(documents):
    """Split documents into smaller chunks."""
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=1000)
    chunks = text_splitter.split_documents(documents)
    logging.info("Documents split into chunks.")
    return chunks

def extract_key_value_info(chunks, text, llm):
    """Extract key-value pairs from document chunks or text."""
    if text is not None:
        full_text = text
        prompt = (
            "You are an expert conversation analyzer tasked with extracting user information from natural language. Examine the following conversation carefully.\n\n"
            "TASK: Extract ALL personal/user information mentioned in this conversation as a clean JSON object with key-value pairs.\n\n"
            "GUIDELINES:\n"
            "- Identify information shared in natural language (e.g., 'My name is Ken' → {'name': 'Ken'})\n"
            "- Look for personal details like name, age, address, phone, email, occupation, preferences, etc.\n"
            "- Extract specific numerical values (dates, prices, ages, income amounts, etc.)\n"
            "- Use normalized key names in camelCase format (e.g., 'phoneNumber' not 'phone_number')\n"
            "- For complex values, combine relevant information (e.g., '123 Main St, Boston MA' → {'address': '123 Main St, Boston MA'})\n"
            "- Only extract information actually provided by the person, not hypothetical or example text\n"
            "- Exclude pleasantries, questions, and non-informational content\n"
            "- If the same type of information is mentioned multiple times, use the most recent or complete version\n\n"
            "EXAMPLES:\n"
            "1. 'Hi there, my name is Ken and I'm 34 years old' → {'name': 'Ken', 'age': 34}\n"
            "2. 'You can reach me at 555-123-4567 or ken@example.com' → {'phoneNumber': '555-123-4567', 'email': 'ken@example.com'}\n"
            "3. 'I live at 123 Oak Street, Apt 4B, Chicago' → {'address': '123 Oak Street, Apt 4B, Chicago'}\n"
            "4. 'I make about $75,000 per year and was born on March 15, 1989' → {'income': '$75,000', 'dateOfBirth': 'March 15, 1989'}\n\n"
            f"CONVERSATION TEXT:\n{full_text}\n\n"
            "OUTPUT (JSON only):"
        )
    else:
        full_text = " ".join([chunk.page_content for chunk in chunks])
        prompt = (
            "You are an expert data extraction specialist working with vector database content. Analyze the following data carefully.\n\n"
            "TASK: Extract ALL relevant information into a FLAT (non-nested) JSON object with simple key-value pairs.\n\n"
            "GUIDELINES:\n"
            "- Create a SINGLE-LEVEL JSON only - NO nested objects or arrays\n"
            "- For structured or hierarchical data, flatten using dot notation or combined keys:\n"
            "  INSTEAD OF: {'address': {'street': '123 Main', 'city': 'Austin'}} \n"
            "  USE: {'addressStreet': '123 Main', 'addressCity': 'Austin'}\n"
            "- Extract all personal data (name, contact, identification numbers, credentials)\n"
            "- Extract all financial information (account numbers, balances, transactions)\n"
            "- Extract all dates, times, locations, measurements, and quantities\n"
            "- Standardize all key names to camelCase format\n"
            "- Ensure keys are specific and self-explanatory (e.g., 'primaryPhoneNumber' vs 'phone')\n"
            "- Preserve the original values exactly as they appear - don't normalize values\n"
            "- EXCLUDE metadata, schema information, vector embeddings, or system fields\n"
            "- EXCLUDE empty fields, placeholder text, or fields without clear values\n"
            "- If identical information appears multiple times, use the most recent or complete version\n\n"
            "EXAMPLES OF PROPER FLATTENING:\n"
            "1. {'user': {'name': 'John', 'contact': {'email': 'j@example.com'}}} → {'userName': 'John', 'userContactEmail': 'j@example.com'}\n"
            "2. {'payment': [{'date': '2023-04-01', 'amount': '$500'}]} → {'paymentDate': '2023-04-01', 'paymentAmount': '$500'}\n\n"
            f"DATABASE CONTENT:\n{full_text}\n\n"
            "OUTPUT (FLAT JSON ONLY):"
        )
    result = llm.invoke(input=prompt)
    raw_output = result.content.strip()
    json_match = re.search(r'\{.*\}', raw_output, re.DOTALL)
    json_str = json_match.group(0) if json_match else "{}"
    try:
        info = json.loads(json_str)
    except Exception as e:
        logging.error(f"Failed to parse JSON: {e}")
        info = {}
    return info

def sanitize_collection_name(name: str) -> str:
    """Sanitize collection name for Chroma."""
    name = name.lower()
    name = re.sub(r'\s+', '_', name)
    name = re.sub(r'[^a-z0-9_-]', '', name)
    name = re.sub(r'^([^a-z0-9]+)', '', name)
    name = re.sub(r'([^a-z0-9]+)$', '', name)
    if len(name) < 3:
        name = name + "_store"
    if len(name) > 63:
        name = name[:63]
    return name

def create_vector_db(chunks, collection_name):
    """Create and persist a vector database."""
    persist_dir = os.path.join(VECTOR_DB_DIR, collection_name)
    os.makedirs(persist_dir, exist_ok=True)
    vector_db = Chroma.from_documents(
        documents=chunks,
        embedding=OllamaEmbeddings(model=EMBEDDING_MODEL),
        collection_name=collection_name,
        persist_directory=persist_dir,
    )
    vector_db.persist()
    logging.info(f"Vector database persisted to {persist_dir}")
    return vector_db

def update_user_info_json(new_info, json_file=USER_INFO_JSON):
    """Update the user_info JSON file."""
    if os.path.exists(json_file):
        try:
            with open(json_file, "r") as f:
                user_info = json.load(f)
        except json.JSONDecodeError:
            user_info = {}
    else:
        user_info = {}
    user_info.update(new_info)
    with open(json_file, "w") as f:
        json.dump(user_info, f, indent=4)
    logging.info("User info JSON updated.")

def load_user_info(json_file=USER_INFO_JSON):
    """Load user information from JSON."""
    if os.path.exists(json_file):
        try:
            with open(json_file, "r") as f:
                user_info = json.load(f)
            return user_info
        except Exception as e:
            logging.error(f"Error reading {json_file}: {e}")
    return {}

def create_retriever(vector_db):
    """Create a retriever from a vector database."""
    retriever = vector_db.as_retriever()
    logging.info("Retriever created.")
    return retriever

def create_chain(new_form, llm, user_info="", uploaded=None):
    """Create a chain to answer questions."""
    if uploaded is None:
        uploaded = []
    template = (
        "You are Quill, an expert form-filling assistant. Your task is to generate a FLAT JSON object where keys EXACTLY match the form field names and values are accurately derived from stored user information.\n\n"
        "FORM TO COMPLETE:\n{new_form_context}\n\n"
        "USER PROFILE DATA:\n{user_info}\n\n"
        "INSTRUCTIONS:\n"
        "1. FIELD EXTRACTION:\n"
        "   - Extract ALL field names from the form using their EXACT naming (preserve case, spacing, and special characters)\n"
        "   - Include all fields in your JSON output, even if some values are missing\n"
        "   - NO NESTED JSON STRUCTURES - output must be a one-level, flat JSON object\n"
        "   - If form has fields that appear hierarchical (e.g., 'address.street'), maintain them as flat keys\n\n"
        "2. VALUE DETERMINATION:\n"
        "   - For each field, find the most relevant information from user profile data\n"
        "   - If information is unavailable, set value to '' (don't guess or omit the field)\n\n"
        "3. DATA FORMATTING:\n"
        "   - Dates: Match exactly the format specified in the form (MM/DD/YYYY, YYYY-MM-DD, etc.)\n"
        "   - Addresses: Format as single strings with appropriate separators as required by the form\n"
        "   - Phone numbers: Apply correct formatting with appropriate separators\n"
        "   - Financial values: Preserve exact decimal places and currency formatting\n"
        "   - Boolean values: Use true/false unless form specifies other values\n\n"
        "4. OUTPUT REQUIREMENTS:\n"
        "   - Generate valid, properly formatted FLAT JSON with no nested objects or arrays\n"
        "   - Ensure all field names in your output EXACTLY match those in the form\n"
        "   - Do not include any explanatory text before or after the JSON object\n"
        "   - Verify the JSON has no nested structures and is properly formatted\n\n"
        "QUESTION: {question}\n\n"
        "ANSWER (DO NOT USE ANY NESTED STRUCTURE IN JSON. USE ONLY FLAT, ONE-LEVEL JSON.):"
    )
    def chain_invoke(question: str) -> str:
        new_form_docs = new_form
        new_form_context = "\n".join(doc.page_content for doc in new_form_docs)
        # uploaded_contexts = [r.get_relevant_documents(question) for r in uploaded]
        # uploaded_forms_context = "\n".join("\n".join(doc.page_content for doc in docs) for docs in uploaded_contexts)
        prompt_text = template.format(
            new_form_context=new_form_context,
            # uploaded_forms_context=uploaded_forms_context,
            user_info=user_info,
            question=question
        )
        response = llm.invoke(input=prompt_text)
        return response.content.strip()
    return chain_invoke

def merge_user_info(current_info: dict, new_info: dict, llm) -> dict:
    """Merge new_info into current_info using LLM-generated mapping."""
    current_json = json.dumps(current_info, indent=2)
    new_json = json.dumps(new_info, indent=2)
    
    prompt = f"""
You are a data integration specialist tasked with merging user information from multiple sources. Your goal is to create an accurate, consolidated user profile.

CURRENT USER PROFILE:
{current_json}

NEW INFORMATION TO INTEGRATE:
{new_json}

TASK: Create a mapping between fields in the new information and corresponding fields in the current profile.

FIELD MATCHING RULES:
1. Match fields that represent the same information, even if the field names differ
2. Consider semantic meaning, not just exact field name matches
3. Use the following known field synonyms:
   - name = fullName, userName, firstName+lastName
   - phone = mobile, phoneNumber, cellPhone, telephone
   - address = homeAddress, streetAddress, residentialAddress
   - email = emailAddress, userEmail
   - ssn = socialSecurityNumber, taxpayerID
   - dob = dateOfBirth, birthDate
   - income = salary, wages, earnings, compensation

OUTPUT INSTRUCTIONS:
1. For each field in the NEW information, identify if it:
   - Matches an existing field in the current profile (provide the field name)
   - Is a completely new field (mark as null)
2. Output a JSON object with the following structure:
   {{
     "mapping": {{
       "new_field_name1": "matching_current_field_name",
       "new_field_name2": null,
       ...
     }}
   }}
3. Include ALL fields from the new information in your mapping
4. Return ONLY the valid JSON with no additional text

EXAMPLE 1:
Current: {{"name": "John Smith", "phone": "555-1234"}}
New: {{"fullName": "John Smith", "mobile": "555-1234", "email": "john@example.com"}}
Output: {{"mapping": {{"fullName": "name", "mobile": "phone", "email": null}}}}

EXAMPLE 2:
Current: {{"address": "123 Main St", "ssn": "123-45-6789"}}
New: {{"homeAddress": "123 Main St", "taxpayerID": "123-45-6789", "employer": "ACME Inc"}}
Output: {{"mapping": {{"homeAddress": "address", "taxpayerID": "ssn", "employer": null}}}}

YOUR MAPPING OUTPUT:
"""
    
    response = llm.invoke(input=prompt)
    try:
        mapping_json = json.loads(response.content.strip())
        mapping = mapping_json["mapping"]
    except Exception as e:
        logging.error(f"Failed to parse LLM response: {e}")
        merged = current_info.copy()
        merged.update(new_info)
        return merged
    
    merged = current_info.copy()
    for new_field, current_field in mapping.items():
        if new_field not in new_info:
            logging.warning(f"Mapping includes '{new_field}', not in new_info. Skipping.")
            continue
        if current_field is not None:
            if current_field in merged:
                merged[current_field] = new_info[new_field]
            else:
                merged[new_field] = new_info[new_field]
        else:
            merged[new_field] = new_info[new_field]
    
    return merged

def update_user_info_from_doc(file_path, llm, current_info: dict):
    """Update user_info from a document."""
    data = ingest_file(file_path)
    if data is None:
        return current_info
    chunks = split_documents(data)
    new_info = extract_key_value_info(chunks, None, llm)
    logging.info(f"New info from document: {new_info}")
    flat_new_info = flatten_json(new_info)
    merged = merge_user_info(current_info, flat_new_info, llm)
    update_user_info_json(merged)
    filename = os.path.basename(file_path)
    collection_name = sanitize_collection_name(os.path.splitext(filename)[0])
    vector_db = create_vector_db(chunks, collection_name)
    vector_db_path = os.path.join(VECTOR_DB_DIR, collection_name)
    update_user_info_json({collection_name: vector_db_path})
    return merged

def update_user_info_from_conversation(text, llm, current_info: dict):
    """Update user_info from conversation text."""
    new_info = extract_key_value_info(None, text, llm)
    logging.info(f"New info from conversation: {new_info}")
    flat_new_info = flatten_json(new_info)
    merged = merge_user_info(current_info, flat_new_info, llm)
    update_user_info_json(merged)
    return merged

## Main Function
def main():
    parser = argparse.ArgumentParser(description="Run Quill in ingest, query, or update mode.")
    parser.add_argument(
        "--mode",
        choices=["ingest", "query", "update"],
        required=True,
        help="Mode: 'ingest', 'query', or 'update'."
    )
    args = parser.parse_args()

    if args.mode == "ingest":
        data = ingest_file(DOC_PATH1)
        if data is None:
            return
        chunks = split_documents(data)
        llm = ChatOllama(model=MODEL_NAME, temperature=0.3)
        key_value_info = extract_key_value_info(chunks, None, llm)
        logging.info(f"Extracted key-value pairs: {key_value_info}")
        flat_key_value_info = flatten_json(key_value_info)
        update_user_info_json(flat_key_value_info)
        filename = os.path.basename(DOC_PATH1)
        collection_name = sanitize_collection_name(os.path.splitext(filename)[0])
        vector_db = create_vector_db(chunks, collection_name)
        vector_db_path = os.path.join(VECTOR_DB_DIR, collection_name)
        update_user_info_json({collection_name: vector_db_path})
        print("User info JSON updated and vector database persisted.")

    elif args.mode == "query":
        user_info_str = json.dumps(load_user_info())
        if not user_info_str or user_info_str == "{}":
            logging.error("User info JSON empty. Run 'ingest' mode first.")
            return
        user_info_dict = load_user_info()
        uploaded_forms = []
        for key, value in user_info_dict.items():
            if isinstance(value, str) and os.path.exists(value) and os.path.isdir(value):
                retriever = create_retriever(
                    Chroma(
                        persist_directory=value,
                        collection_name=sanitize_collection_name(key),
                        embedding_function=OllamaEmbeddings(model=EMBEDDING_MODEL),
                    )
                )
                uploaded_forms.append(retriever)
        if not uploaded_forms:
            logging.error("No uploaded forms found. Run 'ingest' mode first.")
            return
        data = ingest_file(DOC_PATH2)
        if data is None:
            return
        chunks = split_documents(data)
        new_form_collection = "new_form"
        new_form_vector_db = create_vector_db(chunks, new_form_collection)
        llm = ChatOllama(model=MODEL_NAME, temperature=0.3)
        new_form_retriever = create_retriever(new_form_vector_db)
        chain = create_chain(new_form=data, llm=llm, user_info=user_info_str, uploaded=uploaded_forms)
        question = input("Enter your question: ")
        res = chain(question)
        print("Response:")
        print(res)

    elif args.mode == "update":
        current_info = load_user_info()
        if not current_info:
            logging.error("User info JSON empty. Run 'ingest' mode first.")
            return
        llm = ChatOllama(model=MODEL_NAME, temperature=0.3)
        update_method = input("Enter update type ('doc' for document, 'conv' for conversation): ").strip().lower()
        if update_method == "doc":
            file_path = DOC_PATH3
            current_info = update_user_info_from_doc(file_path, llm, current_info)
        elif update_method == "conv":
            text = input("Enter the conversation text update: ").strip()
            current_info = update_user_info_from_conversation(text, llm, current_info)
        else:
            print("Invalid update type.")
            return
        print("Updated user info:")
        print(json.dumps(current_info, indent=4))

if __name__ == "__main__":
    main()
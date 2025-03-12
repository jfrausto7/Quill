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

Image.MAX_IMAGE_PIXELS = None  # Disable image size limit

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Constants
VECTOR_DB_DIR = "vector_db"       # Base directory for persisting vector DBs
MODEL_NAME = "llama3.2-vision:11b"
EMBEDDING_MODEL = "nomic-embed-text"
USER_INFO_JSON = "../../uploads/user_info.json"


## Helper Functions

def flatten_json(data, parent_key='', sep='_'):
    """Recursively flatten a nested JSON object into a flat dictionary."""
    items = []
    
    if not data:
        return {}
        
    for key, value in data.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key
        
        # Skip flattening vector database paths
        if isinstance(value, str) and VECTOR_DB_DIR in value:
            items.append((new_key, value))
            continue
            
        if isinstance(value, dict):
            # Handle nested dictionaries
            items.extend(flatten_json(value, new_key, sep=sep).items())
        elif isinstance(value, list):
            # Handle arrays
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    items.extend(flatten_json(item, f"{new_key}{sep}{i}", sep=sep).items())
                else:
                    items.append((f"{new_key}{sep}{i}", item))
        else:
            # Simple key-value pair
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
    
    try:
        if ext == ".pdf":
            # Use OCR for PDF processing
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
            
        logging.info(f"File {file_path} loaded successfully with {len(data) if data else 0} documents.")
        return data
    except Exception as e:
        logging.error(f"Error loading file {file_path}: {e}")
        return None

def split_documents(documents):
    """Split documents into smaller chunks with optimized parameters."""
    if not documents:
        logging.warning("No documents to split")
        return []
        
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=1000)
    chunks = text_splitter.split_documents(documents)
    logging.info(f"Documents split into {len(chunks)} chunks.")
    return chunks

def extract_key_value_info(chunks, text, llm):
    """Extract key-value pairs from document chunks or text using enhanced prompts."""
    try:
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
            if not chunks:
                logging.warning("No chunks provided for extraction")
                return {}
                
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
        
        # Robust JSON extraction
        json_match = re.search(r'\{.*\}', raw_output, re.DOTALL)
        json_str = json_match.group(0) if json_match else "{}"
        
        try:
            info = json.loads(json_str)
            logging.info(f"Successfully extracted {len(info)} fields")
            return info
        except json.JSONDecodeError as e:
            # Try to repair common JSON issues
            logging.warning(f"JSON parsing failed: {e}, attempting to fix")
            # Replace single quotes with double quotes
            json_str = json_str.replace("'", "\"")
            # Fix missing quotes around keys
            json_str = re.sub(r'([{,])\s*([a-zA-Z0-9_]+)\s*:', r'\1"\2":', json_str)
            
            try:
                info = json.loads(json_str)
                logging.info(f"Fixed JSON and extracted {len(info)} fields")
                return info
            except Exception as e2:
                logging.error(f"Failed to fix JSON: {e2}")
                return {}
    except Exception as e:
        logging.error(f"Error in key-value extraction: {e}")
        return {}

def sanitize_collection_name(name: str) -> str:
    """Sanitize collection name to meet Chroma requirements."""
    if not name:
        return "default_collection"
        
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
    """Create and persist a vector database from document chunks."""
    if not chunks:
        logging.error("No chunks provided to create vector database")
        return None
    
    # Ensure the vector DB directory exists
    os.makedirs(VECTOR_DB_DIR, exist_ok=True)    
    persist_dir = os.path.join(VECTOR_DB_DIR, collection_name)
    os.makedirs(persist_dir, exist_ok=True)
    
    try:
        vector_db = Chroma.from_documents(
            documents=chunks,
            embedding=OllamaEmbeddings(model=EMBEDDING_MODEL),
            collection_name=collection_name,
            persist_directory=persist_dir,
        )
        vector_db.persist()
        logging.info(f"Vector database created and persisted to {persist_dir}")
        return vector_db
    except Exception as e:
        logging.error(f"Error creating vector database: {e}")
        return None

def update_user_info_json(new_info, json_file=USER_INFO_JSON):
    """Update the user_info JSON file with new key-value pairs."""
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(json_file), exist_ok=True)
    
    if os.path.exists(json_file):
        try:
            with open(json_file, "r") as f:
                user_info = json.load(f)
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON from {json_file}: {e}. Initializing empty user_info.")
            user_info = {}
    else:
        user_info = {}
    
    user_info.update(new_info)
    
    try:
        with open(json_file, "w") as f:
            json.dump(user_info, f, indent=4)
        logging.info(f"User info JSON updated with {len(new_info)} new key-value pairs.")
    except Exception as e:
        logging.error(f"Error writing to {json_file}: {e}")

def load_user_info(json_file=USER_INFO_JSON):
    """Load and return user information from the JSON file."""
    if os.path.exists(json_file):
        try:
            with open(json_file, "r") as f:
                user_info = json.load(f)
            return user_info
        except Exception as e:
            logging.error(f"Error reading {json_file}: {e}")
    return {}

def format_chat_history(chat_history_path):
    """Format chat history for the prompt."""
    if not chat_history_path:
        return ""
    try:
        with open(chat_history_path, 'r') as f:
            chat_history = json.load(f)
        formatted = "\nPrevious conversation:\n"
        for msg in chat_history:
            role = "User" if msg['type'] == 'user' else "Assistant"
            formatted += f"{role}: {msg['content']}\n"
        return formatted
    except Exception as e:
        logging.error(f"Error reading chat history: {e}")
        return ""

def create_retriever(vector_db):
    """Create a standard retriever from a vector database."""
    if not vector_db:
        logging.error("No vector database provided for retriever creation")
        return None
        
    try:
        retriever = vector_db.as_retriever()
        logging.info("Retriever created successfully.")
        return retriever
    except Exception as e:
        logging.error(f"Error creating retriever: {e}")
        return None

def create_chain(new_form, llm, user_info="", uploaded=None):
    """Create a chain to answer questions using form context and user info."""
    if not new_form:
        logging.error("No new form retriever provided")
        return None
        
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
        "   - NO NESTED JSON STRUCTURES - output must be a single-level, flat JSON object\n"
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
        "ANSWER (FLAT JSON ONLY):"
    )
    
    def chain_invoke(question: str) -> str:
        if not question or not question.strip():
            return "Please provide a question about the form."
            
        try:
            new_form_docs = new_form
            new_form_context = "\n".join(doc.page_content for doc in new_form_docs) if new_form_docs else ""
            
            # uploaded_contexts = []
            # for r in uploaded:
            #     if r:
            #         try:
            #             docs = r.get_relevant_documents(question)
            #             if docs:
            #                 context_str = "\n".join(doc.page_content for doc in docs)
            #                 uploaded_contexts.append(context_str)
            #         except Exception as e:
            #             logging.warning(f"Error getting relevant documents: {e}")
            
            # uploaded_forms_context = "\n".join(uploaded_contexts)
            
            prompt_text = template.format(
                new_form_context=new_form_context,
                # uploaded_forms_context=uploaded_forms_context,
                user_info=user_info,
                question=question
            )
            
            response = llm.invoke(input=prompt_text)
            return response.content.strip()
        except Exception as e:
            logging.error(f"Error in chain invoke: {e}")
            return f"I encountered an error while processing your question: {e}"
    
    return chain_invoke

def merge_user_info(current_info: dict, new_info: dict, llm) -> dict:
    """Merge new_info into current_info using LLM-generated mapping."""
    # If either dictionary is empty, handle the simple cases
    if not current_info:
        return new_info.copy()
    if not new_info:
        return current_info.copy()
    
    # Format the dictionaries for better LLM comprehension
    current_json = json.dumps(current_info, indent=2)
    new_json = json.dumps(new_info, indent=2)
    
    # Create a prompt that asks the LLM to analyze both sets of fields at once
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
    
    try:
        # Get the LLM's analysis
        response = llm.invoke(input=prompt)
        result_text = response.content.strip()
        
        # Extract the JSON object (handle potential formatting issues)
        json_match = re.search(r'\{[\s\S]*\}', result_text)
        if not json_match:
            logging.warning("Could not extract JSON from LLM response, falling back to simple merge")
            return {**current_info, **new_info}
            
        mapping_json = json_match.group(0)
        
        try:
            mapping = json.loads(mapping_json)
        except json.JSONDecodeError as e:
            logging.warning(f"Error parsing mapping JSON: {e}, attempting to fix")
            # Try to fix common JSON issues
            mapping_json = mapping_json.replace("'", "\"")
            mapping_json = re.sub(r'([{,])\s*([a-zA-Z0-9_]+)\s*:', r'\1"\2":', mapping_json)
            
            try:
                mapping = json.loads(mapping_json)
            except Exception as e2:
                logging.error(f"Failed to fix mapping JSON: {e2}, falling back to simple merge")
                return {**current_info, **new_info}
        
        if "mapping" not in mapping:
            logging.warning("Invalid mapping format (no 'mapping' key), falling back to simple merge")
            return {**current_info, **new_info}
            
        # Initialize the merged result with the current info
        merged = current_info.copy()
        
        # Apply the mapping
        for new_field, current_field in mapping["mapping"].items():
            if new_field not in new_info:
                logging.warning(f"Mapping includes '{new_field}', not in new_info. Skipping.")
                continue
                
            if current_field is not None:
                if current_field in merged:
                    merged[current_field] = new_info[new_field]
                    logging.info(f"Updated field '{current_field}' with value from '{new_field}'")
                else:
                    merged[new_field] = new_info[new_field]
                    logging.info(f"Added new field '{new_field}' (mapped field '{current_field}' doesn't exist)")
            else:
                merged[new_field] = new_info[new_field]
                logging.info(f"Added new field '{new_field}'")
                
        return merged
        
    except Exception as e:
        logging.error(f"Error in field mapping: {e}")
        # Fallback to simple merge in case of errors
        return {**current_info, **new_info}

def update_user_info_from_doc(file_path, llm, current_info: dict):
    """
    Update user_info by processing a new document.
    Also creates and persists a vector database for the update document.
    """
    data = ingest_file(file_path)
    if data is None:
        logging.error(f"Failed to ingest document from {file_path}")
        return current_info
        
    chunks = split_documents(data)
    new_info = extract_key_value_info(chunks, None, llm)
    logging.info(f"New info extracted from document: {new_info}")
    
    # Flatten the new info before merging
    flat_new_info = flatten_json(new_info)
    logging.info(f"Flattened new info: {flat_new_info}")
    
    # Use the efficient merging function
    merged = merge_user_info(current_info, flat_new_info, llm)
    update_user_info_json(merged)
    
    # Create and persist a vector DB for the document
    filename = os.path.basename(file_path)
    collection_name = sanitize_collection_name(os.path.splitext(filename)[0])
    vector_db = create_vector_db(chunks, collection_name)
    if vector_db:
        vector_db_path = os.path.join(VECTOR_DB_DIR, collection_name)
        update_user_info_json({collection_name: vector_db_path})
    
    return merged

def update_user_info_from_conversation(text, llm, current_info: dict):
    """
    Update user_info by processing conversation text.
    """
    if not text.strip():
        logging.warning("Empty conversation text provided, no update performed")
        return current_info
        
    new_info = extract_key_value_info(None, text, llm)
    logging.info(f"New info extracted from conversation: {new_info}")
    
    # Flatten the new info before merging
    flat_new_info = flatten_json(new_info)
    logging.info(f"Flattened new info: {flat_new_info}")
    
    # Use the efficient merging function
    merged = merge_user_info(current_info, flat_new_info, llm)
    update_user_info_json(merged)
    
    return merged

def answer_query(llm, question, user_info="", chat_history="", new_form=None):
    """
    Answer a query using stored data and vector DBs of uploaded forms.
    """
    try:
        user_info_dict = json.loads(user_info) if isinstance(user_info, str) else user_info
    except Exception as e:
        logging.error(f"Error parsing user_info: {e}")
        return "Sorry, I couldn't process your request due to an error with user information."
    
   
    new_form_context = "\n".join(doc.page_content for doc in new_form)
    
    # If we have vector DBs, use the more sophisticated approach
    template = (
        "You are Quill, an expert form-filling assistant. Your task is to generate a FLAT JSON object where keys EXACTLY match the form field names and values are accurately derived from stored user information.\n\n"
        "FORM TO COMPLETE:\n{new_form_context}\n\n"
        "USER PROFILE DATA:\n{user_info}\n\n"
        "CHAT HISTORY:\n{chat_history}\n\n "
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
        "ANSWER (DO NOT USE ANY NESTED STRUCTURE IN JSON. USE ONLY FLAT, ONE-LEVEL JSON. ANSWER ONLY JSON, NOTHING ELSE):"
    )
    
    prompt_text = template.format(
        new_form_context=new_form_context,
        user_info=json.dumps(user_info_dict, indent=2),
        chat_history=chat_history,
        question=question
    )
    
    response = llm.invoke(input=prompt_text)
    return response.content.strip()

def main():
    parser = argparse.ArgumentParser(
        description="Run in multiple modes: ingest (update user_info.json), query (answer questions), or update (update user info)."
    )
    parser.add_argument(
        "--mode",
        choices=["ingest", "query", "update"],
        required=True,
        help="Mode: 'ingest' to process a file and update user info; 'query' to answer questions; 'update' to update user info."
    )
    parser.add_argument(
        "--document",
        type=str,
        help="Path to the document file for ingest and update modes"
    )
    parser.add_argument(
        "--question",
        type=str,
        help="Question for query mode or conversation text for update mode"
    )
    parser.add_argument(
        "--chat-history",
        type=str,
        help="Path to chat history JSON file for query mode"
    )
    
    args = parser.parse_args()
    
    if args.mode == "ingest":
        if not args.document:
            print(json.dumps({"error": "Document is required for ingest mode"}))
            return
            
        # Process document
        data = ingest_file(args.document)
        if data is None:
            print(json.dumps({"error": "Failed to ingest document"}))
            return
            
        chunks = split_documents(data)
        llm = ChatOllama(model=MODEL_NAME, temperature=0.3)
        key_value_info = extract_key_value_info(chunks, None, llm)
        logging.info(f"Extracted key-value pairs: {key_value_info}")
        
        # Flatten any nested structures before saving
        flat_key_value_info = flatten_json(key_value_info)
        update_user_info_json(flat_key_value_info)
        
        # Create and store vector DB
        filename = os.path.basename(args.document)
        collection_name = sanitize_collection_name(os.path.splitext(filename)[0])
        vector_db = create_vector_db(chunks, collection_name)
        
        if vector_db:
            vector_db_path = os.path.join(VECTOR_DB_DIR, collection_name)
            update_user_info_json({collection_name: vector_db_path})
            
            print(json.dumps({
                "status": "success",
                "message": "Document processed successfully",
                "extracted_info": flat_key_value_info
            }))
        else:
            print(json.dumps({
                "status": "partial_success",
                "message": "Document processed but vector database creation failed",
                "extracted_info": flat_key_value_info
            }))
    
    elif args.mode == "query":
        if not args.question:
            print(json.dumps({"error": "Question is required for query mode"}))
            return
        
        # Load stored user info
        user_info = load_user_info()
        if not user_info:
            print(json.dumps({"error": "No user information found"}))
            return

        # Get chat history if provided
        chat_history = ""
        if args.chat_history:
            chat_history = format_chat_history(args.chat_history)

        # Initialize LLM and get response
        llm = ChatOllama(model=MODEL_NAME, temperature=0.3)

        data = ingest_file(args.document)
        response = answer_query(llm, args.question, user_info, chat_history, data)
        
        print(json.dumps({"response": response}))
    
    elif args.mode == "update":
        # Load current user info
        current_info = load_user_info()
        if not current_info:
            print(json.dumps({"error": "No user information found. Run in 'ingest' mode first."}))
            return
            
        llm = ChatOllama(model=MODEL_NAME, temperature=0.3)
        
        if args.document:
            # Update via document
            file_path = args.document
            updated_info = update_user_info_from_doc(file_path, llm, current_info)
            print(json.dumps({
                "status": "success",
                "message": "Your info has been updated from your document.",
                "updated_info": updated_info
            }))
        elif args.question:  # Repurpose question arg for conversation text in update mode
            # Update via conversation text
            text = args.question
            updated_info = update_user_info_from_conversation(text, llm, current_info)
            print(json.dumps({
                "status": "success",
                "message": "Your info has been updated from our conversation.",
                "updated_info": updated_info
            }))
        else:
            print(json.dumps({"error": "Document or question required for update mode"}))

if __name__ == "__main__":
    main()
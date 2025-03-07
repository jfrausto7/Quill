import os
import json
import re
import logging
import argparse
from langchain_community.document_loaders import (
    UnstructuredPDFLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredImageLoader
)
from langchain.document_loaders.csv_loader import CSVLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain.prompts import PromptTemplate
import ollama
from PIL import Image

Image.MAX_IMAGE_PIXELS = None  # Disable image size limit

logging.basicConfig(level=logging.INFO)

# Constants
VECTOR_DB_DIR = "vector_db"       # Base directory for persisting vector DBs
MODEL_NAME = "llama3.2-vision:11b"
EMBEDDING_MODEL = "nomic-embed-text"
USER_INFO_JSON = "../../uploads/user_info.json"

### Helper functions for file ingestion ###
def ingest_file(file_path):
    """Load a file (PDF, Word, image, or CSV) using the appropriate loader."""
    if not os.path.exists(file_path):
        logging.error(f"File not found at path: {file_path}")
        return None
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        loader = UnstructuredPDFLoader(file_path=file_path)
    elif ext in [".doc", ".docx"]:
        loader = UnstructuredWordDocumentLoader(file_path=file_path)
    elif ext in [".png", ".jpg", ".jpeg"]:
        loader = UnstructuredImageLoader(file_path=file_path)
    elif ext == ".csv":
        loader = CSVLoader(file_path=file_path)
    else:
        logging.error(f"Unsupported file format: {ext}")
        return None
    data = loader.load()
    logging.info(f"File {file_path} loaded successfully.")
    return data

def split_documents(documents):
    """Split documents into smaller chunks."""
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=300)
    chunks = text_splitter.split_documents(documents)
    logging.info("Documents split into chunks.")
    return chunks

def extract_key_value_info(chunks, text, llm):
    """
    Extract key-value pairs from document chunks using the LLM.
    Expected output: a valid JSON object.
    If text is provided, use it instead of the concatenated chunk texts.
    """
    if text is not None:
        full_text = text
        prompt = (
            "Extract key information from the following text and represent it as a JSON object with camelCase keys. "
            "For instance, if the text says 'my favorite fruit is orange', output {\"favorite_fruit\": \"orange\"}. "
            "Only output valid JSON without any additional commentary.\n\n"
            f"Text: {full_text}"
        )
    else:
        full_text = " ".join([chunk.page_content for chunk in chunks])
        prompt = (
            "Extract key information from the following document and represent it as JSON key-value pairs. "
            "For example, if the document contains a name, include it as \"name\": \"Daniel Zhou\". "
            "Only output valid JSON without any additional commentary.\n\n"
            f"Document: {full_text}"
        )
    result = llm.invoke(input=prompt)
    logging.info("Key-value information extracted from document.")
    try:
        content = result.content.strip()
        if content.startswith('```') and content.endswith('```'):
            content = content[3:-3].strip()
        info = json.loads(content)
    except Exception as e:
        logging.error("Failed to parse JSON output from LLM: " + str(e))
        info = {}
    return info

def sanitize_collection_name(name: str) -> str:
    """
    Sanitize the provided name:
      - Lowercase, 3-63 characters long.
      - Only alphanumeric characters, underscores, or hyphens.
    """
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
    """
    Create a vector database from document chunks using the given collection name.
    The vector DB is persisted under VECTOR_DB_DIR/<collection_name>.
    """
    # Ensure the vector DB directory exists
    os.makedirs(VECTOR_DB_DIR, exist_ok=True)
    persist_dir = os.path.join(VECTOR_DB_DIR, collection_name)
    os.makedirs(persist_dir, exist_ok=True)
    
    ollama.pull(EMBEDDING_MODEL)
    vector_db = Chroma.from_documents(
        documents=chunks,
        embedding=OllamaEmbeddings(model=EMBEDDING_MODEL),
        collection_name=collection_name,
        persist_directory=persist_dir,
    )
    # Persistence is automatic in newer versions; calling persist() is optional.
    vector_db.persist()
    logging.info(f"Vector database created with collection name: {collection_name} and persisted to {persist_dir}")
    return vector_db

def update_user_info_json(new_info, json_file=USER_INFO_JSON):
    """
    Update the user_info JSON file by merging in new key-value pairs.
    """
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
    with open(json_file, "w") as f:
        json.dump(user_info, f, indent=4)
    logging.info("User info JSON updated with new key-value pairs.")

def load_user_info(json_file=USER_INFO_JSON):
    """
    Load and return user information from the JSON file as a formatted string.
    """
    if os.path.exists(json_file):
        try:
            with open(json_file, "r") as f:
                user_info = json.load(f)
            if user_info:
                return json.dumps(user_info, indent=4)
        except Exception as e:
            logging.error(f"Error reading {json_file}: {e}")
    return ""

def create_retriever(vector_db, llm):
    """
    Create a multi-query retriever using the given vector database and LLM.
    """
    QUERY_PROMPT = PromptTemplate(
        input_variables=["question"],
        template=(
            "You are an AI assistant. Generate five alternative queries for the original question:\n"
            "Original question: {question}"
        ),
    )
    retriever = MultiQueryRetriever.from_llm(
        vector_db.as_retriever(), llm, prompt=QUERY_PROMPT
    )
    logging.info("Retriever created.")
    return retriever

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

def create_chain(new_form, llm, user_info="", uploaded=None):
    """
    Create a chain that combines context from the new form and from a list of uploaded forms.
    The prompt differentiates between 'New Form Context' and 'Uploaded Forms Context' so the LLM knows
    that it may use information from the uploaded forms to fill out the new form.
    """
    if uploaded is None:
        uploaded = []
    template = (
        "You are an AI assistant tasked with filling out a new form. Use the following contexts:\n\n"
        "New Form Context:\n{new_form_context}\n\n"
        "Uploaded Forms Context:\n{uploaded_forms_context}\n\n"
        "Additional User Information:\n{user_info}\n\n"
        "Based on the above, answer the question:\n{question}\n"
    )
    def chain_invoke(question: str) -> str:
        new_form_docs = new_form.get_relevant_documents(question)
        new_form_context = "\n".join(doc.page_content for doc in new_form_docs)
        uploaded_contexts = []
        for r in uploaded:
            docs = r.get_relevant_documents(question)
            context_str = "\n".join(doc.page_content for doc in docs)
            uploaded_contexts.append(context_str)
        uploaded_forms_context = "\n".join(uploaded_contexts)
        prompt_text = template.format(
            new_form_context=new_form_context,
            uploaded_forms_context=uploaded_forms_context,
            user_info=user_info,
            question=question
        )
        response = llm.invoke(input=prompt_text)
        return response.content.strip()
    return chain_invoke

def merge_user_info(current_info: dict, new_info: dict, llm) -> dict:
    """
    Merge new_info into current_info with improved field matching.
    """
    merged = current_info.copy()
    
    for new_key, new_value in new_info.items():
        # Normalize the key - split into words for better matching
        new_key_words = re.findall(r'\b\w+\b', new_key.lower())
        
        # First look for exact key matches
        exact_match = False
        for cur_key in list(merged.keys()):
            if cur_key.lower() == new_key.lower():
                merged[cur_key] = new_value
                exact_match = True
                logging.info(f"Updated exact match field '{cur_key}' with '{new_value}'")
                break
        
        if exact_match:
            continue
        
        # Define specific field types with primary and secondary identifiers
        field_categories = {
            'email': {
                'primary': ['email', 'e-mail', 'mail'],
                'secondary': ['address']
            },
            'address': {
                'primary': ['address', 'residence', 'location'],
                'secondary': ['street', 'ave', 'road', 'apartment', 'apt', 'home']
            },
            'phone': {
                'primary': ['phone', 'telephone', 'mobile', 'cell'],
                'secondary': ['number']
            },
            'name': {
                'primary': ['name'],
                'secondary': ['first', 'last', 'full', 'user']
            }
        }
        
        # Find the category of the new key
        new_key_category = None
        for category, identifiers in field_categories.items():
            # Check for primary identifiers (strong match)
            for word in identifiers['primary']:
                if word in new_key_words:
                    new_key_category = category
                    break
            
            # If no primary match and category still None, try secondary with additional checks
            if new_key_category is None:
                for word in identifiers['secondary']:
                    if word in new_key_words:
                        # For secondary matches, require additional context
                        # e.g., "address" is secondary for email, but should only match if "email" is also present
                        if category == 'email' and any(w in new_key_words for w in ['email', 'mail', 'e-mail']):
                            new_key_category = category
                            break
                        elif category == 'phone' and 'number' in new_key_words:
                            new_key_category = category
                            break
                        elif category == 'address' and not any(w in new_key_words for w in ['email', 'mail']):
                            new_key_category = category
                            break
                        elif category == 'name' and any(w in new_key_words for w in ['user', 'first', 'last']):
                            new_key_category = category
                            break
            
            if new_key_category:
                break
        
        # If we found a category, look for matching keys
        found_match = False
        if new_key_category:
            logging.info(f"Identified '{new_key}' as belonging to category: {new_key_category}")
            
            # Look for keys in the same category
            for cur_key in list(merged.keys()):
                cur_key_words = re.findall(r'\b\w+\b', cur_key.lower())
                
                # Check if current key matches the same category
                for word in field_categories[new_key_category]['primary']:
                    if word in cur_key_words:
                        merged[cur_key] = new_value
                        found_match = True
                        logging.info(f"Category match: Updated '{cur_key}' with value from '{new_key}'")
                        break
                
                if found_match:
                    break
        
        # If still no match, use LLM verification as final attempt
        if not found_match:
            for cur_key in list(merged.keys()):
                # Skip vector_db and other system keys
                if cur_key.endswith('_db') or 'vector' in cur_key.lower():
                    continue
                
                prompt = (
                    "You are an expert in data field comparison. Determine if the following two field names "
                    "refer to the same piece of information:\n"
                    f"Field 1: '{cur_key}'\n"
                    f"Field 2: '{new_key}'\n"
                    "Only answer with 'yes' or 'no'."
                )
                response = llm.invoke(input=prompt).content.strip().lower()
                if response.startswith("yes"):
                    merged[cur_key] = new_value
                    found_match = True
                    logging.info(f"LLM verified: Updated '{cur_key}' with value from '{new_key}'")
                    break
        
        # If no match found after all checks, add as new field
        if not found_match:
            merged[new_key] = new_value
            logging.info(f"Added new field '{new_key}' with value '{new_value}'")
    
    return merged

def update_user_info_from_doc(file_path, llm, current_info: dict):
    """
    Update user_info by processing a new document.
    Also creates and persists a vector database for the update document,
    and adds the vector DB address as a new field in the JSON.
    """
    data = ingest_file(file_path)
    if data is None:
        return current_info
    chunks = split_documents(data)
    new_info = extract_key_value_info(chunks, None, llm)
    logging.info(f"New info from document: {new_info}")
    merged = merge_user_info(current_info, new_info, llm)
    update_user_info_json(merged)
    # Create and persist a vector DB for the update document.
    filename = os.path.basename(file_path)
    collection_name = sanitize_collection_name(os.path.splitext(filename)[0])
    vector_db = create_vector_db(chunks, collection_name)
    vector_db_path = os.path.join(VECTOR_DB_DIR, collection_name)
    update_user_info_json({collection_name: vector_db_path})
    return merged

def update_user_info_from_conversation(text, llm, current_info: dict):
    """
    Update user_info by processing conversation text.
    """
    new_info = extract_key_value_info(None, text, llm)
    logging.info(f"New info from conversation: {new_info}")
    merged = merge_user_info(current_info, new_info, llm)
    update_user_info_json(merged)
    return merged

def answer_query(llm, question, user_info="", chat_history=""):
    """
    Answer a query using stored data and vector DBs of uploaded forms.
    """
    try:
        user_info_dict = json.loads(user_info)
    except Exception as e:
        logging.error(f"Error parsing user_info: {e}")
        return "Sorry, I couldn't process your request due to an error with user information."
    
    # Check if we have any persisted vector DBs
    uploaded_forms = []
    for key, value in user_info_dict.items():
        if isinstance(value, str) and value.startswith(VECTOR_DB_DIR) and os.path.exists(value) and os.path.isdir(value):
            try:
                retriever = create_retriever(
                    Chroma(
                        persist_directory=value,
                        collection_name=key,
                        embedding_function=OllamaEmbeddings(model=EMBEDDING_MODEL),
                    ),
                    llm
                )
                uploaded_forms.append(retriever)
            except Exception as e:
                logging.error(f"Error loading vector DB for {key}: {e}")
    
    # If we don't have any vector DBs, fall back to simple query answering
    if not uploaded_forms:
        prompt = f"""Based on the following user information and chat history, answer the question.
        
        User Information:
        {user_info}

        {chat_history}
        
        Question: {question}
        
        Please provide a direct and helpful response."""

        response = llm.invoke(input=prompt)
        return response.content.strip()
    
    # If we have vector DBs, use the more sophisticated approach
    template = (
        "You are an AI assistant tasked with helping the user. Use the following contexts:\n\n"
        "Uploaded Forms Context:\n{uploaded_forms_context}\n\n"
        "Additional User Information:\n{user_info}\n\n"
        "Chat History:\n{chat_history}\n\n"
        "Based on the above, answer the question:\n{question}\n"
    )
    
    # Gather contexts from all retrievers
    uploaded_contexts = []
    for retriever in uploaded_forms:
        docs = retriever.get_relevant_documents(question)
        context_str = "\n".join(doc.page_content for doc in docs)
        uploaded_contexts.append(context_str)
    
    uploaded_forms_context = "\n".join(uploaded_contexts)
    
    prompt_text = template.format(
        uploaded_forms_context=uploaded_forms_context,
        user_info=user_info,
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
        help="Question for query mode"
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
        llm = ChatOllama(model=MODEL_NAME)
        key_value_info = extract_key_value_info(chunks, None, llm)
        logging.info(f"Extracted key-value pairs: {key_value_info}")
        update_user_info_json(key_value_info)
        
        # Create and store vector DB
        filename = os.path.basename(args.document)
        collection_name = sanitize_collection_name(os.path.splitext(filename)[0])
        vector_db = create_vector_db(chunks, collection_name)
        vector_db_path = os.path.join(VECTOR_DB_DIR, collection_name)
        update_user_info_json({collection_name: vector_db_path})
        
        print(json.dumps({
            "status": "success",
            "message": "Document processed successfully"
        }))
    
    elif args.mode == "query":
        if not args.question:
            print(json.dumps({"error": "Question is required for query mode"}))
            return
        
        # Load stored user info
        user_info_str = load_user_info()
        if not user_info_str:
            print(json.dumps({"error": "No user information found"}))
            return

        # Get chat history if provided
        chat_history = ""
        if args.chat_history:
            chat_history = format_chat_history(args.chat_history)

        # Initialize LLM and get response
        llm = ChatOllama(model=MODEL_NAME)
        response = answer_query(llm, args.question, user_info_str, chat_history)
        
        print(json.dumps({"response": response}))
    
    elif args.mode == "update":
        # Load current user info
        user_info_str = load_user_info()
        if not user_info_str:
            logging.error("User info JSON is empty or missing. Run in 'ingest' mode first.")
            print(json.dumps({"error": "No user information found"}))
            return
            
        try:
            current_info = json.loads(user_info_str)
        except Exception as e:
            logging.error(f"Error parsing user_info.json: {e}")
            print(json.dumps({"error": f"Error parsing user info: {e}"}))
            return
            
        llm = ChatOllama(model=MODEL_NAME)
        
        if args.document:
            # Update via document
            file_path = args.document
            current_info = update_user_info_from_doc(file_path, llm, current_info)
            print(json.dumps({
                "status": "success",
                "message": "Your info has been updated from your document.",
                "updated_info": current_info
            }))
        elif args.question:  # Repurpose question arg for conversation text in update mode
            # Update via conversation text
            text = args.question
            current_info = update_user_info_from_conversation(text, llm, current_info)
            print(json.dumps({
                "status": "success",
                "message": "Your info has been updated from our conversation.",
                "updated_info": current_info
            }))
        else:
            print(json.dumps({"error": "Document or question required for update mode"}))

if __name__ == "__main__":
    main()
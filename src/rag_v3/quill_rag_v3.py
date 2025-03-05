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
from langchain_core.output_parsers import StrOutputParser
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain.prompts import ChatPromptTemplate, PromptTemplate
import ollama

logging.basicConfig(level=logging.INFO)

# Constants
DOC_PATH1 = "sample_filled.pdf"   # For ingest mode (can be any supported file)
DOC_PATH2 = "sample_form.pdf"     # For query mode (new form to be processed)
DOC_PATH3 = "update_info.png"          # For update mode (update user_info.json via a document)
VECTOR_DB_DIR = "vector_db"       # Base directory for persisting vector DBs
MODEL_NAME = "llama3.2-vision:11b"
EMBEDDING_MODEL = "nomic-embed-text"
USER_INFO_JSON = "user_info.json"

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
        info = json.loads(result.content.strip())
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

### New merging functions with LLM assistance ###
def merge_user_info(current_info: dict, new_info: dict, llm) -> dict:
    """
    Merge new_info into current_info using an LLM to decide if two fields are equivalent.
    For each new field, for each existing field, the LLM is asked whether they refer to the same information.
    The prompt now includes examples (e.g., 'phone' and 'mobile') to increase the chance of correct matching.
    If yes, update the existing field; otherwise, add the new field.
    """
    merged = current_info.copy()
    for new_key, new_value in new_info.items():
        found = False
        for cur_key, cur_value in merged.items():
            prompt = (
                "You are an expert in data field comparison. Determine if the following two field names "
                "refer to the same piece of information based on their field names and values. "
                "Note that synonyms like 'cell phone' and 'mobile number' usually refer to the same information.\n"
                f"Field 1: '{cur_key}' with value '{cur_value}'\n"
                f"Field 2: '{new_key}' with value '{new_value}'\n"
                "Answer with 'yes' or 'no' only."
            )
            response = llm.invoke(input=prompt).content.strip().lower()
            if response.startswith("yes"):
                merged[cur_key] = new_value  # Update the existing field.
                found = True
                break
        if not found:
            merged[new_key] = new_value  # Add as a new field.
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
    collection_name = os.path.splitext(filename)[0]
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

### Main function with three modes: ingest, query, update ###
def main():
    parser = argparse.ArgumentParser(
        description="Run in three modes: ingest, query, or update. "
                    "Ingest: process an uploaded file; Query: answer questions using stored info; "
                    "Update: update the stored user info via a new file or conversation."
    )
    parser.add_argument(
        "--mode",
        choices=["ingest", "query", "update"],
        required=True,
        help="Mode: 'ingest' to process a file; 'query' to answer questions; 'update' to update user info."
    )
    args = parser.parse_args()
    
    if args.mode == "ingest":
        # Ingest mode: process DOC_PATH1.
        data = ingest_file(DOC_PATH1)
        if data is None:
            return
        chunks = split_documents(data)
        llm = ChatOllama(model=MODEL_NAME)
        key_value_info = extract_key_value_info(chunks, None, llm)
        logging.info(f"Extracted key-value pairs: {key_value_info}")
        update_user_info_json(key_value_info)
        filename = os.path.basename(DOC_PATH1)
        collection_name = os.path.splitext(filename)[0]
        vector_db = create_vector_db(chunks, collection_name)
        vector_db_path = os.path.join(VECTOR_DB_DIR, collection_name)
        update_user_info_json({collection_name: vector_db_path})
        print("User info JSON has been updated and vector database persisted.")
    
    elif args.mode == "query":
        # Query mode: load stored user info and persisted vector DBs.
        user_info_str = load_user_info()
        if not user_info_str:
            logging.error("User info JSON is empty or missing. Run in 'ingest' mode first.")
            return
        try:
            user_info_dict = json.loads(user_info_str)
        except Exception as e:
            logging.error(f"Error parsing user_info.json: {e}")
            return
        uploaded_forms = []
        for key, value in user_info_dict.items():
            if isinstance(value, str) and os.path.exists(value) and os.path.isdir(value):
                retriever = create_retriever(
                    Chroma(
                        persist_directory=value,
                        collection_name=key,
                        embedding_function=OllamaEmbeddings(model=EMBEDDING_MODEL),
                    ),
                    ChatOllama(model=MODEL_NAME)
                )
                uploaded_forms.append(retriever)
        if not uploaded_forms:
            logging.error("No valid uploaded forms vector DB found in user_info.json. Run in ingest mode first.")
            return
        data = ingest_file(DOC_PATH2)
        if data is None:
            return
        chunks = split_documents(data)
        new_form_collection = "new_form"
        new_form_vector_db = create_vector_db(chunks, new_form_collection)
        llm = ChatOllama(model=MODEL_NAME)
        new_form_retriever = create_retriever(new_form_vector_db, llm)
        chain = create_chain(new_form=new_form_retriever, llm=llm, user_info=user_info_str, uploaded=uploaded_forms)
        question = input("Enter your question: ")
        res = chain(question)
        print("Response:")
        print(res)
    
    elif args.mode == "update":
        # Update mode: update the existing user_info.json via a new document or conversation.
        current_info_str = load_user_info()
        if not current_info_str:
            logging.error("User info JSON is empty or missing. Run in 'ingest' mode first.")
            return
        try:
            current_info = json.loads(current_info_str)
        except Exception as e:
            logging.error(f"Error parsing user_info.json: {e}")
            return
        llm = ChatOllama(model=MODEL_NAME)
        update_method = input("Enter update type ('doc' for document, 'conv' for conversation): ").strip().lower()
        if update_method == "doc":
            # file_path = input("Enter the file path for the update document: ").strip()
            # For simplicity, using DOC_PATH3 for the update document.
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

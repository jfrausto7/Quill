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
from langchain_ollama import OllamaEmbeddings
from langchain_ollama import ChatOllama
from langchain_core.output_parsers import StrOutputParser
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain.prompts import ChatPromptTemplate, PromptTemplate
import ollama

logging.basicConfig(level=logging.INFO)

# Constants
DOC_PATH1 = "screen_shot.png"  # For ingest mode – can be PDF, Word, image, or CSV.
DOC_PATH2 = "sample_form.pdf"    # For query mode – the new form to be processed.
VECTOR_DB_DIR = "vector_db"      # Base directory for persisting vector DBs.
MODEL_NAME = "llama3.2-vision:11b"
EMBEDDING_MODEL = "nomic-embed-text"
USER_INFO_JSON = "user_info.json"

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

def extract_key_value_info(chunks, llm):
    """
    Extract key-value pairs from the document using the LLM.
    For example: {"name": "Daniel Zhou", "email": "example@example.com", ...}
    """
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
    # Note: In newer versions persistence is automatic.
    vector_db.persist()
    logging.info(f"Vector database created with collection name: {collection_name} and persisted to {persist_dir}")
    return vector_db

def update_user_info_json(new_info, json_file=USER_INFO_JSON):
    """
    Update the JSON file of user information with new key-value pairs.
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
    Load user information from the JSON file and return it as a formatted string.
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
    Create a chain that combines contexts from the new form and from a list of uploaded forms.
    The LLM will be informed that it can use info from the uploaded forms to fill out the new form.
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

def main():
    parser = argparse.ArgumentParser(
        description="Run in two modes: ingest (update user_info.json and store vector DB) or query (use stored info and vector DBs to answer questions)."
    )
    parser.add_argument(
        "--mode",
        choices=["ingest", "query"],
        required=True,
        help="Mode: 'ingest' to update user_info.json and persist vector DB; 'query' to answer a question using stored info and vector DBs.",
    )
    args = parser.parse_args()
    
    if args.mode == "ingest":
        # Ingest file from DOC_PATH1 (any supported file type).
        data = ingest_file(DOC_PATH1)
        if data is None:
            return
        chunks = split_documents(data)
        llm = ChatOllama(model=MODEL_NAME)
        key_value_info = extract_key_value_info(chunks, llm)
        logging.info(f"Extracted key-value pairs: {key_value_info}")
        update_user_info_json(key_value_info)
        
        # Use the file name (without extension) as the collection name/key.
        filename = os.path.basename(DOC_PATH1)
        collection_name = os.path.splitext(filename)[0]
        
        vector_db = create_vector_db(chunks, collection_name)
        vector_db_path = os.path.join(VECTOR_DB_DIR, collection_name)
        update_user_info_json({collection_name: vector_db_path})
        print("User info JSON has been updated and vector database persisted.")
    
    elif args.mode == "query":
        # Load stored user info.
        user_info_str = load_user_info()
        if not user_info_str:
            logging.error("User info JSON is empty or missing. Run in 'ingest' mode first.")
            return
        
        try:
            user_info_dict = json.loads(user_info_str)
        except Exception as e:
            logging.error(f"Error parsing user_info.json: {e}")
            return
        
        # Load retrievers for each uploaded form (persisted vector DB).
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
        
        # Process the new form from DOC_PATH2.
        data = ingest_file(DOC_PATH2)
        if data is None:
            return
        chunks = split_documents(data)
        new_form_collection = "new_form"
        new_form_vector_db = create_vector_db(chunks, new_form_collection)
        llm = ChatOllama(model=MODEL_NAME)
        new_form_retriever = create_retriever(new_form_vector_db, llm)
        
        # Create a chain that incorporates both the new form and the uploaded forms contexts.
        chain = create_chain(new_form=new_form_retriever, llm=llm, user_info=user_info_str, uploaded=uploaded_forms)
        
        question = input("Enter your question: ")
        res = chain(question)
        print("Response:")
        print(res)

if __name__ == "__main__":
    main()

import os
import json
import re
import logging
import argparse
from langchain_community.document_loaders import UnstructuredPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain.prompts import ChatPromptTemplate, PromptTemplate
from langchain_ollama import ChatOllama
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.retrievers.multi_query import MultiQueryRetriever
import ollama

logging.basicConfig(level=logging.INFO)

# Constants
DOC_PATH1 = "sample_filled.pdf"
DOC_PATH2 = "sample_form.pdf" # sample_filled.pdf for mode ingest and sample_form.pdf for mode query
MODEL_NAME = "llama3.2-vision:11b"
EMBEDDING_MODEL = "nomic-embed-text"
USER_INFO_JSON = "user_info.json"

def ingest_pdf(doc_path):
    """Load PDF documents."""
    if os.path.exists(doc_path):
        loader = UnstructuredPDFLoader(file_path=doc_path)
        data = loader.load()
        logging.info("PDF loaded successfully.")
        return data
    else:
        logging.error(f"PDF file not found at path: {doc_path}")
        return None

def split_documents(documents):
    """Split documents into smaller chunks."""
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=300)
    chunks = text_splitter.split_documents(documents)
    logging.info("Documents split into chunks.")
    return chunks

def extract_key_value_info(chunks, llm):
    """
    Extract key-value pairs from the document using the LLM.
    The output should be valid JSON containing key-value pairs.
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
    Sanitize the provided name to conform to Chroma's naming rules:
      - Lowercase, 3-63 characters long.
      - Only alphanumeric characters, underscores or hyphens.
      - Starts and ends with an alphanumeric character.
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
    Create a vector database from document chunks using the provided collection name.
    """
    ollama.pull(EMBEDDING_MODEL)
    vector_db = Chroma.from_documents(
        documents=chunks,
        embedding=OllamaEmbeddings(model=EMBEDDING_MODEL),
        collection_name=collection_name,
    )
    logging.info(f"Vector database created with collection name: {collection_name}")
    return vector_db

def update_user_info_json(new_info, json_file=USER_INFO_JSON):
    """
    Update the JSON file of user information with new key-value pairs.
    If the file exists, merge new_info into it; otherwise, create a new file.
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
    logging.info("User info JSON updated with extracted key-value pairs.")

def load_user_info(json_file=USER_INFO_JSON):
    """
    Load user information from the JSON file and return it as a formatted string.
    If the file doesn't exist or is empty, return an empty string.
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
    Create a multi-query retriever using the provided vector database and language model.
    """
    QUERY_PROMPT = PromptTemplate(
        input_variables=["question"],
        template=(
            "You are an AI language model assistant. Your task is to generate five "
            "different versions of the given user question to retrieve relevant documents from "
            "a vector database. By generating multiple perspectives on the user question, your "
            "goal is to help the user overcome some of the limitations of the distance-based "
            "similarity search. Provide these alternative questions separated by newlines.\n"
            "Original question: {question}"
        ),
    )
    retriever = MultiQueryRetriever.from_llm(
        vector_db.as_retriever(), llm, prompt=QUERY_PROMPT
    )
    logging.info("Retriever created.")
    return retriever

def create_chain(retriever, llm, user_info=""):
    """
    Create the retrieval-augmented generation chain.
    The prompt now includes the stored user data via partial formatting.
    """
    template = (
        "Answer the question based ONLY on the following context:\n"
        "{context}\n\n"
        "Additional user information:\n"
        "{user_info}\n\n"
        "Question: {question}\n"
    )
    # Pre-fill the prompt with the user_info (static data) using partial formatting.
    prompt = ChatPromptTemplate.from_template(template).partial(user_info=user_info)
    
    chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    logging.info("Chain created successfully.")
    return chain

def main():
    parser = argparse.ArgumentParser(
        description="Run in one of two modes: ingest (update user_info.json) or query (answer query using stored user info)."
    )
    parser.add_argument(
        "--mode",
        choices=["ingest", "query"],
        required=True,
        help="Mode: 'ingest' to update user_info.json from the document, 'query' to answer a question using stored user info.",
    )
    args = parser.parse_args()
    
    if args.mode == "ingest":
        # Mode 1: Ingest data from DOC_PATH and update (or create) user_info.json.
        data = ingest_pdf(DOC_PATH1)
        if data is None:
            return
        chunks = split_documents(data)
        llm = ChatOllama(model=MODEL_NAME)
        key_value_info = extract_key_value_info(chunks, llm)
        logging.info(f"Extracted key-value pairs: {key_value_info}")
        update_user_info_json(key_value_info)
        print("User info JSON has been updated.")
    
    elif args.mode == "query":
        # Mode 2: Use user_info.json as context to answer a query, without updating it.
        user_info_str = load_user_info()
        if not user_info_str:
            logging.error("User info JSON is empty or missing. Run in 'ingest' mode first.")
            return

        # Optionally, still load the document and create a vector database for retrieval.
        data = ingest_pdf(DOC_PATH2)
        if data is None:
            return
        chunks = split_documents(data)
        
        # Determine a collection name using stored info (if available) or a default.
        try:
            user_info_dict = json.loads(user_info_str)
        except Exception as e:
            logging.error(f"Error parsing user_info.json: {e}")
            return
        if "name" in user_info_dict and user_info_dict["name"]:
            collection_name = sanitize_collection_name(user_info_dict["name"])
        else:
            collection_name = "vector_store_default"
        
        vector_db = create_vector_db(chunks, collection_name)
        llm = ChatOllama(model=MODEL_NAME)
        retriever = create_retriever(vector_db, llm)
        chain = create_chain(retriever, llm, user_info=user_info_str)
        
        # Accept a user query from standard input.
        question = input("Enter your question: ")
        res = chain.invoke(input=question)
        print("Response:")
        print(res)

if __name__ == "__main__":
    main()

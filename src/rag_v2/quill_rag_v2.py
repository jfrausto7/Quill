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
VECTOR_DB_DIR = "vector_db"      # Base directory for persisting vector DBs.
MODEL_NAME = "llama3.2-vision:11b"
EMBEDDING_MODEL = "nomic-embed-text"
USER_INFO_JSON = "../../uploads/user_info.json"  # Updated to match original path

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
        # Remove code block markers if they exist
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
    # Note: In newer versions persistence is automatic.
    vector_db.persist()
    logging.info(f"Vector database created with collection name: {collection_name} and persisted to {persist_dir}")
    return vector_db

def update_user_info_json(new_info, json_file=USER_INFO_JSON):
    """
    Update the JSON file of user information with new key-value pairs.
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

def answer_query(llm, question, user_info="", chat_history=""):
    """
    Answer a query using stored data and vector DBs of uploaded forms.
    This preserves the more advanced logic of v2 while maintaining the
    original interface.
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
    
    # If we have vector DBs, use the more sophisticated approach from v2
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
        description="Run in one of two modes: ingest (update user_info.json) or query (answer query using stored user info)."
    )
    parser.add_argument(
        "--mode",
        choices=["ingest", "query"],
        required=True,
        help="Mode: 'ingest' to update user_info.json from the document, 'query' to answer a question using stored user info.",
    )
    parser.add_argument(
        "--document",
        type=str,
        required=True,
        help="Path to the document file"
    )
    parser.add_argument(
        "--question",
        type=str,
        help="Question for query mode"
    )
    parser.add_argument(
        "--chat-history",
        type=str,
        help="Path to chat history JSON file"
    )

    args = parser.parse_args()
    
    if args.mode == "ingest":
        # Process document
        data = ingest_file(args.document)
        if data is None:
            return
        chunks = split_documents(data)
        llm = ChatOllama(model=MODEL_NAME)
        key_value_info = extract_key_value_info(chunks, llm)
        logging.info(f"Extracted key-value pairs: {key_value_info}")
        update_user_info_json(key_value_info)
        
        # Additional for v2: Store vector DB
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

if __name__ == "__main__":
    main()
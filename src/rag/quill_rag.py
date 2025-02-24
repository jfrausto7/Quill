import os
import json
import logging
import argparse
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from langchain_community.document_loaders import UnstructuredPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings, ChatOllama
import socket
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_NAME = "llama3.2-vision:11b"
EMBEDDING_MODEL = "nomic-embed-text"
USER_INFO_JSON = "../../uploads/user_info.json"
NUM_CORES = multiprocessing.cpu_count()

# global instances
llm = None
embeddings = None
response_cache = {}
process_pool = None
thread_pool = None

class QueryRequest(BaseModel):
    question: str
    chat_history: str = ""

class IngestRequest(BaseModel):
    document_path: str

def find_free_port(start_port=8000, max_port=8100):
    """Find a free port to use"""
    for port in range(start_port, max_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('', port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free ports found between {start_port} and {max_port}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI app"""
    global llm, embeddings, process_pool, thread_pool
    logger.info("Initializing services...")
    
    # initialize process and thread pools
    process_pool = ProcessPoolExecutor(max_workers=NUM_CORES)
    thread_pool = ThreadPoolExecutor(max_workers=NUM_CORES * 2)
    
    # initialize LLM and embeddings
    llm = ChatOllama(model=MODEL_NAME)
    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
    
    logger.info(f"Initialization complete with {NUM_CORES} CPU cores")
    yield
    
    # some cleanup
    process_pool.shutdown()
    thread_pool.shutdown()
    logger.info("Shutting down...")

app = FastAPI(lifespan=lifespan)

def process_chunk(chunk):
    """Process a single document chunk"""
    try:
        return chunk.page_content
    except Exception as e:
        logger.error(f"Error processing chunk: {e}")
        return ""

def parallel_process_chunks(chunks):
    """Process document chunks in parallel"""
    with ProcessPoolExecutor(max_workers=NUM_CORES) as executor:
        processed_chunks = list(executor.map(process_chunk, chunks))
    return processed_chunks

def split_documents(documents, chunk_size=1000, chunk_overlap=200):
    """Optimized document splitting with smaller chunks"""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    chunks = text_splitter.split_documents(documents)
    return parallel_process_chunks(chunks)

def ingest_pdf(doc_path):
    """Load PDF documents."""
    if os.path.exists(doc_path):
        try:
            loader = UnstructuredPDFLoader(file_path=doc_path)
            data = loader.load()
            logger.info("PDF loaded successfully")
            return data
        except Exception as e:
            logger.error(f"Error loading PDF: {e}")
            return None
    logger.error(f"PDF file not found at path: {doc_path}")
    return None

def extract_key_value_info(chunks, llm):
    """Extract key-value pairs from document chunks."""
    try:
        full_text = " ".join([chunk for chunk in chunks if chunk])
        prompt = (
            "Extract key information from the following document and represent it as JSON key-value pairs. "
            "For example, if the document contains a name, include it as \"name\": \"Daniel Zhou\". "
            "Only output valid JSON without any additional commentary.\n\n"
            f"Document: {full_text}"
        )
        result = llm.invoke(input=prompt)
        content = result.content.strip()
        
        if content.startswith('```') and content.endswith('```'):
            content = content[3:-3].strip()
            
        info = json.loads(content)
        logger.info("Successfully extracted key-value information")
        return info
    except Exception as e:
        logger.error(f"Failed to extract key-value information: {e}")
        return {}

def update_user_info_json(new_info, json_file=USER_INFO_JSON):
    """Update the JSON file with new user information."""
    try:
        os.makedirs(os.path.dirname(json_file), exist_ok=True)
        
        if os.path.exists(json_file):
            try:
                with open(json_file, "r") as f:
                    user_info = json.load(f)
            except json.JSONDecodeError:
                logger.error(f"Error decoding {json_file}. Starting fresh.")
                user_info = {}
        else:
            user_info = {}
        
        user_info.update(new_info)
        
        with open(json_file, "w") as f:
            json.dump(user_info, f, indent=4)
        logger.info("User info updated successfully")
        
    except Exception as e:
        logger.error(f"Error updating user info: {e}")
        raise

def load_user_info(json_file=USER_INFO_JSON):
    """Load user information from JSON file."""
    try:
        if os.path.exists(json_file):
            with open(json_file, "r") as f:
                user_info = json.load(f)
            return json.dumps(user_info, indent=4)
    except Exception as e:
        logger.error(f"Error loading user info: {e}")
    return "{}"

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
        logger.error(f"Error reading chat history: {e}")
        return ""

async def process_llm_request(prompt):
    """Process LLM request asynchronously"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(thread_pool, lambda: llm.invoke(input=prompt))

async def get_response(question: str, chat_history: str = ""):
    """Async version of get_response with parallel processing"""
    cache_key = f"{question}:{chat_history}"
    
    if cache_key in response_cache:
        logger.info("Cache hit for query")
        return response_cache[cache_key]

    # load user info async
    loop = asyncio.get_event_loop()
    user_info = await loop.run_in_executor(thread_pool, load_user_info)

    prompt = f"""Based on this user information and chat history, answer the question.
    
    User Information: {user_info}
    Chat History: {chat_history}
    Question: {question}
    Answer:"""

    try:
        response = await process_llm_request(prompt)
        response_content = response.content.strip()
        response_cache[cache_key] = response_content
        return response_content
    except Exception as e:
        logger.error(f"Error getting LLM response: {e}")
        raise

def get_response_sync(question: str, chat_history: str = ""):
    """Synchronous version optimized with thread pool"""
    cache_key = f"{question}:{chat_history}"
    
    if cache_key in response_cache:
        logger.info("Cache hit for query")
        return response_cache[cache_key]

    with ThreadPoolExecutor(max_workers=NUM_CORES) as executor:
        user_info = executor.submit(load_user_info).result()

    prompt = f"""Based on this user information and chat history, answer the question.
    
    User Information: {user_info}
    Chat History: {chat_history}
    Question: {question}
    Answer:"""

    try:
        response = llm.invoke(input=prompt)
        response_content = response.content.strip()
        response_cache[cache_key] = response_content
        return response_content
    except Exception as e:
        logger.error(f"Error getting LLM response: {e}")
        raise

async def process_pdf(doc_path):
    """Process PDF asynchronously"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(process_pool, ingest_pdf, doc_path)

@app.post("/query")
async def handle_query(query: QueryRequest, background_tasks: BackgroundTasks):
    try:
        response = await get_response(query.question, query.chat_history)
        return {"response": response}
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        return {"error": str(e)}

@app.post("/ingest")
async def handle_ingest(ingest: IngestRequest):
    try:
        data = await process_pdf(ingest.document_path)
        if data is None:
            return {"error": "Document not found or couldn't be loaded"}
            
        chunks = await asyncio.get_event_loop().run_in_executor(
            process_pool, 
            split_documents, 
            data
        )
        
        key_value_info = await asyncio.get_event_loop().run_in_executor(
            thread_pool,
            extract_key_value_info,
            chunks,
            llm
        )
        
        await asyncio.get_event_loop().run_in_executor(
            thread_pool,
            update_user_info_json,
            key_value_info
        )
        
        return {"status": "success", "message": "Document processed successfully"}
    except Exception as e:
        logger.error(f"Error ingesting document: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RAG service with parallel processing")
    parser.add_argument("--mode", choices=["ingest", "query"], required=True)
    parser.add_argument("--document", type=str, required=True)
    parser.add_argument("--question", type=str, help="Question for query mode")
    parser.add_argument("--chat-history", type=str, help="Path to chat history JSON file")
    args = parser.parse_args()

    if args.mode == "ingest":
        data = ingest_pdf(args.document)
        if data:
            chunks = split_documents(data)
            llm = ChatOllama(model=MODEL_NAME)
            key_value_info = extract_key_value_info(chunks, llm)
            update_user_info_json(key_value_info)
            print(json.dumps({"status": "success", "message": "Document processed successfully"}))
    elif args.mode == "query":
        if not args.question:
            print(json.dumps({"error": "Question is required for query mode"}))
            exit(1)

        llm = ChatOllama(model=MODEL_NAME)
        
        # parallel processing of user info and chat history
        with ThreadPoolExecutor(max_workers=2) as executor:
            user_info_future = executor.submit(load_user_info)
            chat_history_future = executor.submit(
                format_chat_history, 
                args.chat_history if args.chat_history else None
            )
            
            user_info_str = user_info_future.result()
            chat_history = chat_history_future.result()

        if not user_info_str:
            print(json.dumps({"error": "No user information found"}))
            exit(1)

        try:
            response = get_response_sync(args.question, chat_history)
            print(json.dumps({"response": response}))
        except Exception as e:
            print(json.dumps({"error": str(e)}))
            exit(1)
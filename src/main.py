import subprocess
import os
import asyncio
import uvicorn
from fastapi import FastAPI, BackgroundTasks
from concurrent.futures import ThreadPoolExecutor
import logging
from rag.quill_rag import app as rag_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def start_frontend():
    """Start the Next.js frontend development server"""
    npm_cmd = 'npm.cmd' if os.name == 'nt' else 'npm'
    frontend_path = os.path.join(os.getcwd(), 'src', 'frontend', 'quill')
    
    try:
        os.chdir(frontend_path)
        logger.info(f"Starting Next.js development server in {frontend_path}...")
        
        # Run npm run dev
        process = subprocess.run(
            f"{npm_cmd} run dev",
            shell=True,
            check=True,
            text=True
        )
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running npm run dev: {e}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        raise

def start_rag_service():
    """Start the RAG service"""
    try:
        logger.info("Starting RAG service on port 8000...")
        uvicorn.run(rag_app, host="0.0.0.0", port=8000)
    except Exception as e:
        logger.error(f"Error starting RAG service: {e}")
        raise

async def main():
    """Main function to start all services"""
    try:
        # create a ThreadPoolExecutor to run our services
        with ThreadPoolExecutor(max_workers=2) as executor:
            # start both services
            futures = [
                executor.submit(start_rag_service),
                executor.submit(start_frontend)
            ]
            
            # wait for both services to complete (or raise an exception)
            for future in futures:
                await asyncio.get_event_loop().run_in_executor(
                    None, 
                    future.result
                )
                
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise

if __name__ == "__main__":
    try:
        # run the async main function
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down services...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
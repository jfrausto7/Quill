import subprocess
import os
import time
from pathlib import Path

def start_mongodb():
    # Create data directory if it doesn't exist
    data_dir = Path.home() / '.quill' / 'mongodb'
    data_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Starting MongoDB with data directory: {data_dir}")
    
    # Start MongoDB as a background process
    if os.name == 'nt':  # Windows
        mongo_cmd = "mongod"
    else:  # Mac/Linux
        mongo_cmd = "mongod"
    
    try:
        mongo_process = subprocess.Popen(
            f"{mongo_cmd} --dbpath={data_dir}",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait a bit to ensure MongoDB has started
        time.sleep(3)
        
        # Check if process is still running
        if mongo_process.poll() is None:
            print("MongoDB server started successfully")
            return mongo_process
        else:
            stdout, stderr = mongo_process.communicate()
            print(f"MongoDB failed to start: {stderr.decode()}")
            return None
    except Exception as e:
        print(f"Error starting MongoDB: {e}")
        return None

def start_frontend():
    # Get the absolute path to npm
    npm_cmd = 'npm.cmd' if os.name == 'nt' else 'npm'
    
    # Get frontend directory path
    current_dir = os.getcwd()
    frontend_path = os.path.join(current_dir, 'src', 'frontend', 'quill')
    
    try:
        # Change to the frontend directory
        os.chdir(frontend_path)
        print(f"Starting Next.js development server in {frontend_path}...")
        
        # Run npm run dev with shell=True for Windows
        process = subprocess.run(
            f"{npm_cmd} run dev",
            shell=True,
            check=True,
            text=True
        )
        
    except subprocess.CalledProcessError as e:
        print(f"Error running npm run dev: {e}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    # Start MongoDB first
    mongo_process = start_mongodb()
    
    if mongo_process:
        try:
            # Start the frontend
            start_frontend()
        finally:
            # Cleanup: Stop MongoDB when the script exits
            print("Shutting down MongoDB...")
            if os.name == 'nt':  # Windows
                subprocess.run(['taskkill', '/F', '/PID', str(mongo_process.pid)])
            else:  # Mac/Linux
                mongo_process.terminate()
                mongo_process.wait()
    else:
        print("Failed to start MongoDB. Please make sure MongoDB is installed correctly.")
1. Install dependencies with: `pip install -r requirements.txt`
2. Install poppler by: `conda install poppler`
3. Run: `python install.py`
4. Run ingest mode to extract information from a pdf form and generate a json file by: `python quill_rag.py --mode ingest`
5. Run query mode to use user's info from the json file to fill a pdf form by: `python quill_rag.py --mode query`
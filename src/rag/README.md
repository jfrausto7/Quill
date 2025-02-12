1. Install dependencies with: `pip install -r requirements.txt`
2. Install poppler by: `conda install poppler`
3. Install tesseract by: `brew install tesseract` (MacOS with brew installed); for other systems, refer to https://tesseract-ocr.github.io/tessdoc/Installation.html
4. Run: `python install.py`
5. Run: `brew install tesseract` or install tesseract via this [link](https://github.com/UB-Mannheim/tesseract/wiki)
6. Run ingest mode to extract information from a pdf form and generate a json file by: `python quill_rag.py --mode ingest`
7. Run query mode to use user's info from the json file to fill a pdf form by: `python quill_rag.py --mode query`

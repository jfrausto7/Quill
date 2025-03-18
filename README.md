# Quill

🪶 AI-powered document assistant that intelligently extracts information from your documents to automate form filling.

CS224G Project

## Features

TODO

## Setup

1. Clone the repository
2. Install dependencies with: `pip install -r requirements.txt` in a virtual environment named 'quill'
3. Download ollama (https://ollama.com)
4. Install poppler by: `conda install poppler`
5. Install tesseract by: `brew install tesseract` (MacOS with brew installed); for other systems, refer to https://tesseract-ocr.github.io/tessdoc/Installation.html
6. Run: `python src/rag/install.py`
7. Install [Node/Next.js](https://nodejs.org/en/download)

## Usage

Run the frontend with `python src/main.py` and navigate to http://localhost:3000/

To test document creation, run: `python3 src/document_creation/write_pdf.py PNG_PATH JSON`
where `PNG_PATH` is the path to an empty form png (e.g. "./W-2.png") and `JSON` is the path
to a .json file containing the labels and their respective answers (e.g. "./user_info.json"):

user_info.json:
{ "Employee social security number": "000-11-2222", 
  "Employer identification number": "999-888-777", 
  "Wages, tips, other compensation": "64000" }

## OpenAI Assistant API

A side experiment named 'openai_assistant' leverages the OpenAI Assistant API to automate document processing to build a proof of concept. To implement the notebook, an API key needs to be inserted at the first cell. The experiment can:

- Visually identify blanks in forms
- Auto-fill forms and generate PDF outputs
- Store and manage user information in JSON format

## WEB-UI

We utilized the open-source project WEB-UI (MIT License) to build a proof of concept (https://github.com/browser-use/web-ui). Our experiments included various deep learning models:

- DeepLearning R1: 1.5B to 70B
- LLaVA
- Gemini 2.0 Flash-Exp
- GPT-4o
  Among these, GPT-4o demonstrated the best performance in accuracy and efficiency.

## Contributions by team member

Sprint #1:
- Daniel: Implemented OpenAI Assistant API, experimented with WEB-UI, explored locally running DeepSeek R1 & LLaVA, and prepared slides
- Dante: Implemented backend chat function using Ollama API (deepseek model), experimented with locally running Deepseek r1 & LLaVa, worked on slides.
- Jacob: Implemented UI and frontend/backend integration.
- Ismael: Research on multimodal agents, explored Janus capabilities locally on the web using Gradio, fine tuning attempt on Janus for form text extraction.
- Neil: Prepared user interview form and conducted preliminary interviews; project management; provided input on solution; mentored on slides and presentation

Sprint #2:
- Daniel: Developed a multi-query RAG system with key-value extraction for JSON generation and JSON-based form filling.
- Dante: Wrote doc_upload.py and modified llama3.2-vision_interface.py, added PDF2PNG functionality, create detailed diagrams of workflow, worked on slides.
- Jacob: Experimented w/ MongoDB for document management/encryption. Integrated RAG system into chat interface.
- Ismael: Wrote the fine-tune script for llama3.2 vision, began the construction of the form-field-detection dataset, (WIP) Integrating llama 3.2 system into chat interface
- Neil: Prepared user interview form and conducted preliminary interviews; project management; provided input on solution; mentored on slides and presentation

Sprint #3:
- Daniel: Upgraded RAG to process various document types (PDF, Word, Images, and CSV) with persistent storage and vector database referencing for uploads; worked on slides and demo
- Dante: Wrote two scripts: write_pdf.py and find_source_coords.py, which leverage LLM calls (GPT4o-mini) and OCR (Google Tesseract) to handle the final workflow task of finalized form creation. Worked on slides and demo.
- Jacob: Experimented w/ local LLM memory optimization. Improved UI features based on feedback.
- Ismael: Pushed two methods that extract form fields from web-based forms: 1. Puppeteer (onlineForms_Puppeteer) 2. Prompt engineering w/ o3-mini (onlineForms_llm).
- Neil: Finalized user survey form, and collected and analyzed results.  Developed "coming soon" website with waiting list feature; project management; provided input on workflow and demo; mentored on slides and presentation.

Final Sprint:
- Daniel: Enhanced RAG with an update mode, allowing users to update their information via chat or doc uploads; debugged RAG and its integration with the frontend; prepared demo day slides.
- Dante:
- Jacob: Integrated all frontend components with RAG and OCR processes. Debugged like crazy and recorded the final demo.
- Ismael: Pushed OnlineTestFormFill1 (workflow of manually filling/submitting web-based forms through a convo w/ Quill) & OnlineTestFormFill2 (workflow of taking the info from a filled form pdf and then filling/submitting a web-based form using that info) under onlineForms_v2.
- Neil:

# Quill

🪶 AI-powered document assistant that intelligently extracts information from your documents to automate form filling.

CS224G Project

## Features

TODO

## Setup

1. Clone the repository
2. Install dependencies with: `pip install -r requirements.txt`
3. Download ollama (https://ollama.com)
4. Install Deepseek R1 with: `ollama pull deepseek-r1:1.5b`
5. Install [Node/Next.js](https://nodejs.org/en/download)
6. Install [MongoDB Community](https://www.mongodb.com/try/download/community)
7. Install MongoDB on Node with: `npm install mongodb`

## Usage

Run the application with `python src/main.py` and navigate to http://localhost:3000/

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

- Daniel: Implemented OpenAI Assistant API, experimented with WEB-UI, explored locally running DeepSeek R1 & LLaVA, and prepared slides
- Dante: Implemented backend chat function using Ollama API (deepseek model), experimented with locally running Deepseek r1 & LLaVa, worked on slides.
- Jacob: Implemented UI and frontend/backend integration.
- Ismael: Research on multimodal agents, explored Janus capabilities locally on the web using Gradio, fine tuning attempt on Janus for form text extraction.
- Neil: Interview attorney/owners re tax appeal process; research appeal process; project management; mentor on slides and presentation

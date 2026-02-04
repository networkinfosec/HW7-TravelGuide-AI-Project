# HW7-TravelGuide-AI-Project

# Travel Guide (Streamlit + OpenAI)

## Overview
This app collects:
- Destination
- Number of days
- Special interests
- Guardrails / constraints

It generates:
- A day-by-day travel plan (Morning/Afternoon/Evening)
- A downloadable PDF

---

## Prerequisites
- Python 3.10+
- Visual Studio Code
- OpenAI API key

---

## Setup (macOS / Linux)
1) Open this folder in VS Code
2) Open Terminal (View > Terminal)
3) Create venv:
   python3 -m venv .venv
4) Activate venv:
   source .venv/bin/activate
5) Upgrade pip:
   python -m pip install --upgrade pip
6) Install dependencies:
   python -m pip install -r requirements.txt
7) Create a .env file in the project folder:
   OPENAI_API_KEY=sk-...

---

## Setup (Windows PowerShell)
1) Open this folder in VS Code
2) Open Terminal (View > Terminal)
3) Create venv:
   py -m venv .venv
4) Activate venv:
   .\.venv\Scripts\Activate.ps1
5) Upgrade pip:
   python -m pip install --upgrade pip
6) Install dependencies:
   python -m pip install -r requirements.txt
7) Create a .env file in the project folder:
   OPENAI_API_KEY=sk-...

---

## Run the app
python -m streamlit run travel_guide.py

---

## Troubleshooting
- Make sure you selected the Python interpreter from .venv in VS Code
- Make sure .env exists and has OPENAI_API_KEY
- Use "Diagnostics > Run quick API self-test" in the app if it fails

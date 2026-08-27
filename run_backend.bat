@echo off
cd backend
if not exist .venv py -3.12 -m venv .venv
call .venv\Scripts\activate
python -m pip install -r requirements.txt
if not exist .env copy .env.example .env
python -m uvicorn app.main:app --reload --port 8000

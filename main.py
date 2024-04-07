from typing import List
from fastapi import FastAPI, Request, HTTPException, Depends,Body,Form
from fastapi.responses import HTMLResponse,RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google.oauth2 import id_token
import requests
from google.cloud import firestore
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
app = FastAPI()
firestore_db = firestore.Client()
fire_base_request_adapter = requests.Request()
app.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def get_form(request: Request):
    docs_ref = firestore_db.collection('processed_weather_data').stream()

    weather_data = []
    for doc in docs_ref:
        doc_data = doc.to_dict()
        weather_data.append(doc_data)

    return templates.TemplateResponse("main.html", {"request": request,"weather_data": weather_data})

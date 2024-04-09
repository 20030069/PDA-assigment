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

@app.post("/submit")
async def submit_form(city: str = Form(...), date: str = Form(...)):
    data = fetch_weather_history(city, date)
    if data:
        upload_to_firestore(data,city,date)
        return RedirectResponse(url="/", status_code=303)
    else:
        return {"error": "Failed to fetch or save data"}

def fetch_weather_history(city, date):
    url = "https://weatherapi-com.p.rapidapi.com/history.json"
    querystring = {"q": city, "dt": date, "lang": "en"}
    headers = {
        "X-RapidAPI-Key": "73f81855famsh68b12ce03f72ce5p1f9443jsnc3ecbd92b22c",
        "X-RapidAPI-Host": "weatherapi-com.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers, params=querystring)
    print("URL requested:", response.url)  
    print("Response status code:", response.status_code) 
    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to fetch data: ", response.text)  
        return None


def upload_to_firestore(data, city, date):
    try:
        document_name = f"{city}-{date}"
        summary = data['forecast']['forecastday'][0]['day']

        doc_ref = firestore_db.collection('weather_history').document(document_name)
        doc_ref.set(summary)
        print(f"Uploaded data for {document_name} successfully.")
    except Exception as e:
        print(f"Failed to save data to Firestore: {e}")
        return None

@app.get("/process-all-weather-data")
async def process_all_weather_data():
    weather_docs_ref = firestore_db.collection('weather_history').stream()

    processed_count = 0
    for doc in weather_docs_ref:
        doc_id = doc.id 
        doc_data = doc.to_dict()
        parts = doc_id.split('-')
        city = '-'.join(parts[:-3])  
        date = '-'.join(parts[-3:])
        processed_doc_ref = firestore_db.collection('processed_weather_data').document(doc_id)
        processed_doc = processed_doc_ref.get()

        if not processed_doc.exists:
            try:
                weather_text = doc_data.get("condition", {}).get("text", "Unknown")

                processed_data = {
                    "city": city,
                    "date": date,
                    "text": weather_text,
                    "daily_chance_of_rain": doc_data["daily_chance_of_rain"],
                    "daily_chance_of_snow": doc_data["daily_chance_of_snow"],
                    "daily_will_it_rain": doc_data["daily_will_it_rain"],
                    "daily_will_it_snow": doc_data["daily_will_it_snow"],
                    "maxtemp_c": doc_data["maxtemp_c"],
                    "mintemp_c": doc_data["mintemp_c"],
                    "maxwind_kph": doc_data["maxwind_kph"],
                    "totalprecip_mm": doc_data["totalprecip_mm"],
                    "totalsnow_cm": doc_data["totalsnow_cm"],
                    "uv": doc_data["uv"],
                }

                processed_doc_ref.set(processed_data)
                processed_count += 1
            except KeyError as e:
                print(f"Data missing for document {doc_id}: {e}")

    return {"detail": f"Processed {processed_count} documents into 'processed_weather_data' collection."}
